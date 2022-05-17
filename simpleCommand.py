import sys
import socket
import selectors
import traceback
import os
import colorama

import libclient

sel = selectors.DefaultSelector()


def create_request(action, value=None, shell="echo", files=None):
    if action == "query":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action),
        )
    elif action == "remote":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, shell=shell, value=value, req_file=files),
        )
    elif action == "command":
        return dict(
            type="command",
            encoding="utf-8",
            content=dict(action=action, shell=shell, value=value, req_file=files),
        )
    else:
        return dict(
            type="binary",
            encoding="binary",
            content=value,
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


def main():
    host = "127.0.0.1"
    port = 65432

    filename = "test.c"

    request = create_request(
        "command", shell="cc", value=["-o", "output"], files=filename
    )

    start_connection(host, port, request)

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)
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
