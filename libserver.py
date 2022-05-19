import os, subprocess, sys, struct, time, random, tempfile, shutil, logging

import dotsi, colorama

from utils import get_latest_file
from liball import MessageAll

random.seed(time.time())
colorama.init(autoreset=True)


class Message(MessageAll):
    def __init__(self, selector, sock, addr):
        super().__init__(selector, sock, addr)
        self.directory = None
        self.response_created = False

    def reset(self):
        self._set_selector_events_mask("r")
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False

    def _write(self):
        if self._send_buffer:
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if (
                    "keep_connection_alive" in self.jsonheader.keys()
                    and self.jsonheader.keep_connection_alive > 0
                ):
                    self.reset()
                    print(f"<<< Keep connection alive for ${self.addr} >>>")

                elif sent and not self._send_buffer:
                    self.close()

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
        print(f"LENGTH OF JSONHEADER: {len(jsonheader_bytes)}")
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _create_response_json_content(self):
        self.request = dotsi.fy(self.request)
        request = self.request.request

        if request == "query":
            content = {"cost": random.randint(0, 100)}
            print(f"{colorama.Fore.YELLOW}Sending: {content}")
        else:
            content = {"result": f"Error: invalid action."}
        return content

    def _create_response_command(self):
        self.request = dotsi.fy(self.request)
        command = self.request.command

        if self.directory is not None:
            directory = self.directory
        else:
            directory = os.getcwd()

        print(f"{colorama.Fore.RED}Running CMD: {command}")

        process = subprocess.run(
            command, check=True, capture_output=True, cwd=directory
        )

        output = dotsi.Dict(
            {
                "output": process.stdout.decode("utf-8"),
                "exit_status": process.returncode,
            }
        )

        if process.returncode == 0:
            # get compiled file which is presumably the newest file
            latest_file = get_latest_file(directory)
            filename = os.path.basename(latest_file)
            output.update({"filename": filename})
            # send back the compiled file
            with open(latest_file, "rb") as f:
                data = f.read()

        else:
            logging.exception("Subprocess exited non-zero")

        logging.debug(f"Output: {output.output}, exit_status: {output.exit_status}")

        if "tmp" in self.directory:
            # cleanup tmp dir
            print(f"=== Removing ${self.directory} ===")
            shutil.rmtree(self.directory)

        return (data, output)

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

    def process_request(self):
        self.jsonheader = dotsi.fy(self.jsonheader)

        content_len = self.jsonheader.content_length
        if not len(self._recv_buffer) >= content_len:
            return

        # data populated from buffer
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        if self.jsonheader.content_type == "text/json":
            # if json content
            encoding = self.jsonheader.content_encoding
            self.request = self._json_decode(data, encoding)
            print(f">>> Received request {self.request!r} from {self.addr}")

        elif self.jsonheader.content_type == "binary":
            # File recieved
            self.request = data
            filename = self.jsonheader.filename

            print(
                f"{colorama.Fore.RED}>>> Received {self.jsonheader.content_type} "
                f"request from {self.addr}"
            )

            # Write data to file!
            if self.directory is None:
                self.directory = tempfile.mkdtemp()

            fullpath = os.path.join(self.directory, filename)

            with open(fullpath, "wb") as f:
                f.write(data)

            print(f"=== File:{filename} written to ${fullpath} ===")

        elif self.jsonheader.content_type == "command":
            # if a command is given
            encoding = self.jsonheader.content_encoding
            self.request = self._json_decode(data, encoding)
            print(f"{colorama.Fore.GREEN}>>> Received command request from {self.addr}")

        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")

    def create_response(self):
        if self.jsonheader.content_type == "text/json":
            response = self._create_response_json_content()
            content_bytes = self._json_encode(response, "utf-8")
            header = dotsi.Dict(
                {
                    "content_type": "text/json",
                    "content_encoding": "utf-8",
                }
            )
            print(f"{colorama.Fore.CYAN}Created 'query/json' response ")
        elif self.jsonheader.content_type == "binary":
            # Binary or unknown content_type
            content_bytes = b">>>First 10 bytes of request: " + self.request[:10]
            header = dotsi.Dict(
                {
                    "content_type": "binary",
                    "content_encoding": "binary",
                }
            )
            print(f"{colorama.Fore.CYAN}Created 'binary' response ")
        elif self.jsonheader.content_type == "command":
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
        else:
            # TODO: generic command passed in
            pass

        message = self._create_message(header, content_bytes)
        self.response_created = True
        self._send_buffer += message

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
