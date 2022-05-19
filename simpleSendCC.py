import sys
import socket
import selectors
import traceback
import os
import colorama
import dotsi

import libclient

sel = selectors.DefaultSelector()


def create_request(
    request, action=None, args=None, shell=None, files=None, data=None, filename=None
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
            action=action,
        )
    elif request == "command":
        return dotsi.Dict(
            type="command",
            encoding="utf-8",
            content=dict(request=request, shell=shell, args=args, files=files),
            action=action,
        )
    elif request == "file":
        return dotsi.Dict(
            type="binary",
            encoding="binary",
            content=data,
            action=action,
            filename=filename,
        )


def start_connection(host, port, request):
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)

    return sock.fileno()


def get_file_data(filename):
    with open(filename, "rb") as f:
        data = f.read()

    return data


def send_file(filename, address, sel, socket=None):
    host, port = address
    data = get_file_data(filename)
    request = create_request("file", data=data, filename=filename)

    if socket is None:
        start_connection(host, port, request)
    else:
        message = libclient.Message(sel, socket, address, request)
        sel.modify(socket, events=selectors.EVENT_WRITE, data=message)


def reuse_socket(request, address, sel, socket=None):
    host, port = address

    if socket is None:
        start_connection(host, port, request)
    else:
        message = libclient.Message(sel, socket, address, request)
        sel.modify(socket, events=selectors.EVENT_WRITE, data=message)


def main():
    host = "127.0.0.1"
    port = 65432

    files_to_send = ["test.c", "test2.c"]

    request_cc = create_request(
        "command", shell="cc", args=["-o", "output_file"], files=files_to_send
    )

    # start the action by sending requires
    send_file(filename="test.c", address=(host, port), sel=sel, socket=None)

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)

                    if (
                        message.response
                        and message.jsonheader["content_type"] == "binary"
                    ):
                        # if receive a binary response from server, means file succesfully received
                        if files_to_send:
                            # if there are still files to be sent
                            file = files_to_send.pop(0)
                            send_file(
                                filename=file,
                                socket=key.fileobj,
                                address=message.addr,
                                sel=sel,
                            )
                        else:
                            # all files sent, can send the command now
                            reuse_socket(
                                request=request_cc,
                                socket=key.fileobj,
                                address=message.addr,
                                sel=sel,
                            )
                except Exception:
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
            # Check for a socket being monitored to continue.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")


if __name__ == "__main__":
    main()
