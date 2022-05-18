import sys
import socket
import selectors
import traceback
import os
import colorama
import dotsi
from soupsieve import select

import libclient

sel = selectors.DefaultSelector()


def create_request(request, action=None, args=None, shell="echo", files=None):
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
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(request=request),
            action=action,
        )
    elif request == "command":
        return dict(
            type="command",
            encoding="utf-8",
            content=dict(request=request, shell=shell, args=args, files=files),
            action=action,
        )
    elif request == "file":
        return dict(type="binary", encoding="binary", content=args, action=action)


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


filename = "test2.c"

with open(filename, "rb") as f:
    data2 = f.read()

def main():
    host = "127.0.0.1"
    port = 65432

    filename = "test.c"

    with open(filename, "rb") as f:
        data = f.read()

    # request = create_request(
    #     "command", shell="cc", value=["-o", "output"], files=filename
    # )

    request = create_request("file", args=data, action="5")

    start_connection(host, port, request)

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)

                    if message.jsonheader != None:
                        if (message.jsonheader["content_type"] == "binary"):
                            new_request = create_request("file",args=data2, action="5" )
                            new_message = libclient.Message(sel, key.fileobj,message.addr,new_request)
                            print(key.fileobj)
                            sel.modify(key.fileobj,events=selectors.EVENT_WRITE,data=new_message)
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
