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

    return sock.fileno()


# if len(sys.argv) != 5:
#     print(f"Usage: {sys.argv[0]} <host> <port> <action> <value>")
#     sys.exit(1)

# host, port = sys.argv[1], int(sys.argv[2])
# action, value = sys.argv[3], sys.argv[4]
# request = create_request(action, value)

ports = [65432, 65431]

results = []

"""
in an action set, for each action, run a query to all hosts
collect the returned costs, send a request to remote host,
which may involve sending a file for each action and receiving back a file from each host
"""


def in_list(c, classes):
    for i, sublist in enumerate(classes):
        if c in sublist:
            return i
    return -1


# first query
def query(addresses):
    """
    Run for each action in an actionset to query all the connected servers.
    will return the minimum bid server and it's ip address

    """

    query = create_request("query")

    # mock the actionset input here
    actionset = ["action1", "action2"]

    # buffer to hold all the socket descriptors
    fd_all = []

    for index, action in enumerate(actionset):

        fd_action = []
        for address in addresses:
            # for each host!
            host, port = address
            fd = start_connection(host, port, query)
            fd_action.append(fd)

        fd_all.append(fd_action)

    queries = [[] for x in actionset]

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data

                """experimental"""
                try:
                    message.process_events(mask)

                    socket_no = key.fd
                    if (
                        message.response
                        and message.jsonheader["content-type"] == "text/json"
                    ):
                        # print("HELP!")

                        which_list = in_list(socket_no, fd_all)
                        # print(f"In list:  + {which_list}")

                        if which_list != -1:
                            fd_all[which_list].remove(socket_no)
                            queries[which_list].append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["result"],
                                }
                            )

                        if not fd_all[which_list]:
                            """
                            if for an action, not waiting for any more sockets to return
                            determine the lowest bid and send the next request
                            by starting a new connection with different request

                            """

                            minCost = min(queries[which_list], key=lambda x: x["cost"])
                            print(f"Start connection to {minCost}")

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

    # parser(filename)

    # mock return of parser
    host = "127.0.0.1"
    port = 65432

    port2 = 65431

    addresses = [(host, port), (host, port2), (host, port)]

    query(addresses)
    # send_file(host, port, "test.c")
    # cc(host, port, "test.c")

    sel.close()


if __name__ == "__main__":
    main()
