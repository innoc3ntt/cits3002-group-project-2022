import sys, selectors, struct, socket, os, logging


import dotsi

import libclient
from liball import MessageAll

logger = logging.getLogger("client")


def in_list(c, classes):
    """
    Convenience function to find which list in a 2D list an integer is in

        Parameters:
            c (int): The integer to look for
            classes list[int]: 2D list to search in

        Returns:
            i (int): index of list containing element, -1 if not found
    """
    for i, sublist in enumerate(classes):
        if c in sublist:
            return i
    return -1


def start_connection(sel, host, port, request):
    """
    Returns:
        (int) socket number

    Parameters:
        sel (selector):
        host (str): ip address
        port (int): port number
        request (dict): dictionary
    """
    addr = (host, port)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    logger.info(f"<<< Starting connection to {addr} on {sock.fileno()}")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)

    return sock.fileno()


def reuse_connection(message, filename=None, command=None, keep_connection_alive=True):
    if filename:
        data = get_file_data(filename)
        request = create_request(
            "file",
            data=data,
            filename=filename,
            keep_connection_alive=keep_connection_alive,
        )
    else:
        request = create_request("command", command=command)

    message.update_request(request)


def send_query(sel, host, port):
    """Wrapper around start_connection to be called for each action to each host"""
    query = create_request("query")
    return start_connection(sel, host, port, query)


def create_request(
    request,
    command=None,
    data=None,
    filename=None,
    keep_connection_alive=False,
):
    """
    Create a request to pass to start_connection
    One of three types
    - query
    - command
    - file

    Parameters:
        request (str): type of request, query, command or file
        action (int): action number associated with
        args: extra args to pass to a "command" request
        shell: command to pass to shell, default echo
        files: name of files to send

    Returns:
        (dict) A dictionary representing the request object
    """
    if request == "query":
        return dotsi.Dict(
            type="text/json",
            encoding="utf-8",
            content=dict(request=request),
        )
    elif request == "command":
        return dotsi.Dict(
            type="command",
            encoding="utf-8",
            content=dict(request=request, command=command),
        )
    elif request == "file":
        return dotsi.Dict(
            type="binary",
            encoding="binary",
            content=data,
            filename=filename,
            keep_connection_alive=keep_connection_alive,
        )
    else:
        raise RuntimeError("Invalid request created!")


def send_file(filename, address, sel, socket=None):
    host, port = address
    data = get_file_data(filename)
    request = create_request(
        "file", data=data, filename=filename, keep_connection_alive=True
    )

    if socket is None:
        return start_connection(sel, host, port, request)
    else:
        message = libclient.Message(sel, socket, address, request)
        sel.modify(socket, events=selectors.EVENT_WRITE, data=message)
        return socket.fileno()


def get_file_data(filename):
    with open(filename, "rb") as f:
        data = f.read()
    return data


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
                logger.info(f"<<< Sending {self.request.filename} to {self.addr}")
            elif request == "command":
                logger.info(
                    f"<<< Sending {self.request.content.command} command to {self.addr}"
                )
            else:
                logger.info(f"<<< Sending {self.request.content} to {self.addr}")
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

    def _process_response_command(self):
        # compile file sent by server!
        exit_status = self.jsonheader.exit_status

        if exit_status == 0:
            logger.info(f">>> Subprocess exited succesfully")
            filename = self.jsonheader.filename
            logger.info(f">>> Received file: {filename} from {self.addr}")
            with open(filename, "wb") as f:
                f.write(self.response)
        else:
            logger.error(f">>> Subprocess exited non-zero")
            raise SubprocessFailedError(f"{self.jsonheader.output}")

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
            logger.info(f">>> Received response {self.response!r} from {self.addr}")
            self.close()

        elif self.jsonheader.content_type == "command":
            self.response = data
            logger.info(
                f">>> Received {self.jsonheader.content_type} "
                f"response from {self.addr}"
            )
            self._process_response_command()
            self.close()
        else:
            # Binary or unknown content_type
            self.response = data
            logger.info(
                f">>> Received {self.jsonheader.content_type} | {self.response} response from {self.addr}"
            )

    def close(self):
        logger.info(f"=== Closing connection to {self.addr} ===")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            logger.error(
                f"Error: selector.unregister() exception for " f"{self.addr}: {e!r}"
            )

        try:
            self.sock.close()
        except OSError as e:
            logger.error(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

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


class SubprocessFailedError(Exception):
    pass
