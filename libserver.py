import glob
import os
import subprocess
import sys
import selectors
import json
import io
import struct
import time
import random
import colorama

random.seed(time.time())
colorama.init(autoreset=True)


class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def _write(self):
        if self._send_buffer:
            # print(f"Sending {self._send_buffer!r} to {self.addr}")
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.close()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(self, *, content_bytes, content_type, content_encoding, action):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
            "action": action,
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_json_content(self):
        request = self.request.get("request")
        action = self.request.get("action")

        if request == "query":
            content = {"cost": random.randint(0, 100)}
            print(f"{colorama.Fore.YELLOW}Sending: {content} {action}")
        else:
            pass
            # content = {"result": f"Error: invalid action '{action}'."}
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
            "action": action,
        }
        return response

    def _create_response_binary_content(self):
        response = {
            "content_bytes": b"First 10 bytes of request: " + self.request[:10],
            "content_type": "binary",
            "content_encoding": "binary",
            "action": "5",
        }
        # FIXME: action 5???

        return response

    def _create_response_command(self):
        action = self.request.get("action")
        shell = self.request.get("shell")
        value = self.request.get("value")
        files = self.request.get("files")
        cmd = [shell]
        cmd.extend(value)
        cmd.extend(files)

        print(f"{colorama.Fore.RED}CMD: {cmd}")

        process = subprocess.run(cmd, check=True, capture_output=True)
        content = {
            "output": process.stdout.decode("utf-8"),
            "exit_status": process.returncode,
        }

        # get newest file, send it back
        list_of_files = glob.glob(
            "./*"
        )  # * means all if need specific format then *.csv
        latest_file = max(list_of_files, key=os.path.getctime)

        print("Latest file is:")
        print(latest_file)

        with open(latest_file, "rb") as f:
            data = f.read()

        response = {
            "content_bytes": data,
            "content_type": "command",
            "content_encoding": "binary",
            "action": action,
        }
        return response

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.request is None:
                self.process_request()

    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()

        self._write()

    def close(self):
        print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f"Error: selector.unregister() exception for " f"{self.addr}: {e!r}")

        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(">H", self._recv_buffer[:hdrlen])[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(self._recv_buffer[:hdrlen], "utf-8")
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def process_request(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return

        # data populated from buffer
        data = self._recv_buffer[:content_len]

        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json":
            # if json content
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            print(f"Received request {self.request!r} from {self.addr}")

        elif self.jsonheader["content-type"] == "binary":
            # File recieved
            self.request = data
            print(
                f"Received {self.jsonheader['content-type']} "
                f"request from {self.addr}"
                f"{self.jsonheader!r}"
            )

            # FIXME: ENTRY POINTACTION IS STORED IN JSONHEADER!

            # Write data to file!

            with open("testfile", "wb") as f:
                f.write(data)

        elif self.jsonheader["content-type"] == "command":
            # if a command is given
            # encoding = self.jsonheader["content-encoding"]
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            print(f"{colorama.Fore.GREEN}Received command request!")

        # print(f"Received request {self.request!r} from {self.addr}")

        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def create_response(self):
        if self.jsonheader["content-type"] == "text/json":
            response = self._create_response_json_content()
            print(f"{colorama.Fore.CYAN} Created 'query/json' response ")
        elif self.jsonheader["content-type"] == "binary":
            # Binary or unknown content-type
            response = self._create_response_binary_content()
            print(f"{colorama.Fore.CYAN} Created 'binary' response ")
        elif self.jsonheader["content-type"] == "command":
            # if a cc command is given
            response = self._create_response_command()
            print(f"{colorama.Fore.YELLOW}Created 'command' response")

        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message
