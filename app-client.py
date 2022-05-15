#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import os
import subprocess

import libclient

# remove later

import tqdm


sel = selectors.DefaultSelector()


def create_request(action, value=None, shell="echo"):
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
            content=dict(action=action, shell=shell, value=value),
        )
    # elif action == "file":
    #     return dict(type="binary/custom-server-binary-type", encoding="binary", content=)
    else:
        return dict(
            type="binary/custom-client-binary-type",
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
def query():

    host = "127.0.0.1"
    query = create_request("query")

    # pretend there are 3 actions

    for port in ports:
        # for each host!
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

    print("mincost")
    print(minCost)

    return minCost


def remote(minCost):
    print()
    print()
    host, port = minCost["address"]
    # request = create_request("remote", "-l", subp="ls")
    request = create_request("remote", "-jy", subp="cal")

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


def sendFile():
    host = "127.0.0.1"

    file = open("test.c", "rb")
    bytes_read = file.read()
    print("LENGHT IS :   " + str(len(bytes_read)))
    file_send = create_request("file", bytes_read)

    # pretend there are 3 actions
    start_connection(host, 65432, file_send)

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


def main():
    # both_commands()
    # subprocess.run(both_commands)
    # minimums = []

    # for action in range(3):
    #     minimums.append(query())

    # for action in minimums:
    #     remote(action)
    sendFile()
    c_req = create_request("remote", shell="cc", value=["-o", "output", "test.c"])

    start_connection("127.0.0.1", 65432, c_req)
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

    sel.close()


if __name__ == "__main__":
    main()
