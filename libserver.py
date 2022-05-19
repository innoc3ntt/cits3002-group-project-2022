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
import dotsi
import tempfile

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
        self.directory = None

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

                if self.jsonheader["content_type"] == "binary":
                    print("Keep connection alive")
                    self._set_selector_events_mask("r")
                    self._recv_buffer = b""
                    self._send_buffer = b""
                    self._jsonheader_len = None
                    self.jsonheader = None
                    self.request = None
                    self.response_created = False

                    return

                if sent and not self._send_buffer:
                    self.close()

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
        obj = json.load(tiow)
        tiow.close()
        return obj

    def _create_message(self, header, content_bytes):
        jsonheader = dotsi.Dict(
            {
                "byteorder": sys.byteorder,
                "content_length": len(content_bytes),
            }
        )
        jsonheader.update(header)
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_json_content(self):
        request = self.request.request

        if request == "query":
            content = {"cost": random.randint(0, 100)}
            print(f"{colorama.Fore.YELLOW}Sending: {content}")
        else:
            content = {"result": f"Error: invalid action."}
        return content

    def _create_response_command(self):
        self.request = dotsi.fy(self.request)
        shell = self.request.shell
        args = self.request.args
        files = self.request.files

        cmd = [shell]
        cmd.extend(args)
        cmd.extend(files)

        # FIXME:uncomment when testing full
        # if self.directory is not None:
        #     directory = self.directory
        # else:
        #     directory = os.getcwd()

        directory = os.path.join(os.getcwd(), "test")

        print(f"{colorama.Fore.RED}CMD: {cmd}")

        try:
            process = subprocess.run(
                cmd, check=True, capture_output=True, cwd=directory
            )
            output = dotsi.Dict(
                {
                    "output": process.stdout.decode("utf-8"),
                    "exit_status": process.returncode,
                }
            )

            print(f"Output: {output.output}, exit_status:{output.exit_status}")
        except Exception as exc:
            print(exc)

        # get compiled file which is presumably the newest file
        latest_file = self.get_latest_file(directory)
        filename = os.path.basename(latest_file)
        # send back the compiled file
        with open(latest_file, "rb") as f:
            data = f.read()

        output.update({"filename": filename})

        return (data, output)

    def get_latest_file(self, directory):

        file_list = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        ]

        file = max(file_list, key=os.path.getctime)

        base_file = os.path.basename(file)
        print(f"Latest file is: {base_file}")

        return file

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
                "content_length",
                "content_type",
                "content_encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f"Missing required header '{reqhdr}'.")

    def process_request(self):
        self.jsonheader = dotsi.fy(self.jsonheader)

        content_len = self.jsonheader.content_length
        if not len(self._recv_buffer) >= content_len:
            return

        # data populated from buffer
        data = self._recv_buffer[:content_len]

        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content_type"] == "text/json":
            # if json content
            encoding = self.jsonheader["content_encoding"]
            self.request = self._json_decode(data, encoding)
            print(f"Received request {self.request!r} from {self.addr}")

        elif self.jsonheader.content_type == "binary":
            # File recieved
            self.request = data
            filename = self.jsonheader.filename

            print(
                f"{colorama.Fore.RED}Received {self.jsonheader.content_type} "
                f"request from {self.addr}"
            )

            # Write data to file!
            if self.directory is None:
                self.directory = tempfile.mkdtemp()

            fullpath = os.path.join(self.directory, filename)

            with open(fullpath, "wb") as f:
                f.write(data)

            print(f"File written to ${fullpath}")

        elif self.jsonheader.content_type == "command":
            # if a command is given
            # encoding = self.jsonheader["content_encoding"]
            encoding = self.jsonheader.content_encoding
            self.request = self._json_decode(data, encoding)
            print(f"{colorama.Fore.GREEN}Received command request!")

        # print(f"Received request {self.request!r} from {self.addr}")

        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def create_response(self):
        if self.jsonheader["content_type"] == "text/json":
            response = self._create_response_json_content()
            content_bytes = self._json_encode(response, "utf-8")
            header = dotsi.Dict(
                {
                    "content_type": "text/json",
                    "content_encoding": "utf-8",
                }
            )
            print(f"{colorama.Fore.CYAN}Created 'query/json' response ")
        elif self.jsonheader["content_type"] == "binary":
            # Binary or unknown content_type
            content_bytes = b"First 10 bytes of request: " + self.request[:10]
            header = dotsi.Dict(
                {
                    "content_type": "binary",
                    "content_encoding": "binary",
                }
            )
            print(f"{colorama.Fore.CYAN}Created 'binary' response ")
        elif self.jsonheader["content_type"] == "command":
            # if a cc command is given
            # TODO: Do something with output, the subprocess return code
            content_bytes, output = self._create_response_command()
            header = dotsi.Dict(
                {
                    "content_type": "command",
                    "content_encoding": "binary",
                }
            )
            header.update(output)

            print(f"{colorama.Fore.YELLOW}Created 'command' response")

        message = self._create_message(header, content_bytes)
        self.response_created = True
        self._send_buffer += message
