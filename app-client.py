#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import os

import libclient


sel = selectors.DefaultSelector()


def create_request(action, value=None, shell="echo", req_file=None):
    if action == "search":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, value=value),
        )
    elif action == "query":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action),
        )
    elif action == "remote":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, shell=shell, value=value, req_file=req_file),
        )
    elif action == "command":
        return dict(
            type="command",
            encoding="utf-8",
            content=dict(action=action, shell=shell, value=value, req_file=req_file),
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


# if len(sys.argv) != 5:
#     print(f"Usage: {sys.argv[0]} <host> <port> <action> <value>")
#     sys.exit(1)

# host, port = sys.argv[1], int(sys.argv[2])
# action, value = sys.argv[3], sys.argv[4]
# request = create_request(action, value)

ports = [65432, 65431]

results = []

# in an action set, for each action, run a query to all hosts
# collect the returned costs, send a request to remote host,
# which may involve sending a file for each action and receiving back a file from each host


# first query
def query(addresses):
    """
    Run for each action in an actionset to query all the connected servers.
    will return the minimum bid server and it's ip address

    """

    query = create_request("query")

    for address in addresses:
        # for each host!
        host, port = address
        start_connection(host, port, query)

    results = []

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)
                    # print(key.data)
                    if mask & selectors.EVENT_READ:
                        results.append(
                            {
                                "address": message.addr,
                                "cost": message.response["result"],
                            }
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
    # finally:
    #     sel.close()

    minCost = min(results, key=lambda x: x["cost"])

    return minCost


def remote(minCost, request):
    host, port = minCost["address"]

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
    # finally:
    #     sel.close()


def send_file(host, port, filename):
    with open(filename, "rb") as f:
        data = f.read()

    request = create_request("file", data)
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
    # finally:
    #     sel.close()


def cc(host, port, filename):
    request = create_request(
        "command", shell="cc", value=["-o", "output"], req_file=filename
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


def main():
    host = "127.0.0.1"
    port = 65431

    # port2 = 65431

    addresses = [(host, port)]

    query(addresses)
    send_file(host, port, "test.c")
    cc(host, port, "test.c")

    sel.close()


if __name__ == "__main__":
    main()
