import sys, selectors, struct

import dotsi

from liball import MessageAll


class Message(MessageAll):
    def __init__(self, selector, sock, addr, request):
        super().__init__(selector, sock, addr)
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None
        self._request_queued = False

    def _write(self):
        request = self.request.type
        if self._send_buffer:
            if request == "binary":
                print(f"<<< Sending {self.request.filename} to {self.addr}")
            elif request == "command":
                print(
                    f"<<< Sending {self.request.content.command} command to {self.addr}"
                )
            else:
                print(f"<<< Sending {self.request.content} to {self.addr}")
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]

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

    def _process_response_json_content(self):
        content = self.response
        cost = content.get("cost")
        print(f"Got cost: {cost}")

    def _process_response_binary_content(self):
        content = self.response
        print(f">>> {content!r}")

    def _process_response_command(self):
        # compile file sent by server!

        content = self.response
        exit_status = self.jsonheader.exit_status
        filename = self.jsonheader.filename
        print(f">>> Received file: {filename} from server")
        print(f">>> Subprocess exited {exit_status}")
        with open(filename, "wb") as f:
            f.write(content)

    def read(self):
        self._read()

        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.response is None:
                self.process_response()

    def write(self):
        if not self._request_queued:
            self.queue_request()

        self._write()

        if self._request_queued:
            if not self._send_buffer:
                # Set selector to listen for read events, we're done writing.
                self._set_selector_events_mask("r")

    def update_request(self, request):
        self.request = request
        self._recv_buffer = b""
        self._send_buffer = b""
        self._request_queued = False
        self._jsonheader_len = None
        self.jsonheader = None
        self.response = None

        events = selectors.EVENT_WRITE

        self.selector.modify(self.sock, events=events, data=self)

    def queue_request(self):
        content = self.request.content
        content_type = self.request.type
        content_encoding = self.request.encoding

        header = dotsi.Dict()

        if content_type == "text/json":
            content_bytes = self._json_encode(content, content_encoding)
            header.update(
                {
                    "content_type": content_type,
                    "content_encoding": content_encoding,
                }
            )
        elif content_type == "command":
            content_bytes = self._json_encode(content, content_encoding)
            header.update(
                {
                    "content_type": content_type,
                    "content_encoding": content_encoding,
                }
            )
        else:
            content_bytes = content
            filename = self.request.filename
            header.update(
                {
                    "content_type": content_type,
                    "content_encoding": content_encoding,
                    "filename": filename,
                }
            )

        if "keep_connection_alive" in self.request.keys():
            header.update({"keep_connection_alive": self.request.keep_connection_alive})

        message = self._create_message(header, content_bytes)
        self._send_buffer += message
        self._request_queued = True

    def process_response(self):
        self.jsonheader = dotsi.fy(self.jsonheader)

        content_len = self.jsonheader.content_length
        if not len(self._recv_buffer) >= content_len:
            return

        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]

        if self.jsonheader.content_type == "text/json":
            # if json content
            encoding = self.jsonheader.content_encoding
            self.response = self._json_decode(data, encoding)
            print(f">>> Received response {self.response!r} from {self.addr}")
            self._process_response_json_content()

            self.close()

        elif self.jsonheader.content_type == "command":
            self.response = data
            print(
                f">>> Received {self.jsonheader['content_type']} "
                f"response from {self.addr}"
            )
            self._process_response_command()
            self.close()
        else:
            # Binary or unknown content_type
            self.response = data
            print(
                f">>> Received {self.jsonheader.content_type} "
                f"response from {self.addr}"
            )
            self._process_response_binary_content()

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
