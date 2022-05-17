import sys
import socket
import selectors
import traceback
import os
import colorama

import libclient


sel = selectors.DefaultSelector()
colorama.init(autoreset=True)


def create_request(action, value=None, shell="echo", req_file=None):
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


# first query
def query(addresses):
    """
    Run for each action in an actionset to query all the connected servers.
    will return the minimum bid server and it's ip address

    """

    query = create_request("query")

    # mock the actionset input here
    actions = [
        "actionset1:",
        ["remote-cc", "test.c", ["requires", "test.c"]],
        ["echo", "hello"],
    ]

    actionset1 = actions[0]

    # buffers to hold connection data per action
    fd_all = []
    requires = [[] for x in actions]
    queries = [[] for x in actions]

    # mock actionset 1 only first
    for index, action in enumerate(actions[1:]):

        fd_action = []
        if action[-1][0] == "requires":
            for file in action[-1][1:]:
                requires[index].append()

        for address in addresses:
            # for each host!
            host, port = address
            fd = start_connection(host, port, query)
            fd_action.append(fd)

        fd_all.append(fd_action)

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

                        action_n = in_list(socket_no, fd_all)
                        # print(f"In list:  + {which_list}")

                        if action_n != -1:
                            fd_all[action_n].remove(socket_no)
                            queries[action_n].append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["result"],
                                }
                            )

                        if not fd_all[action_n]:
                            """
                            if for an action, not waiting for any more sockets to return
                            determine the lowest bid and send the next request
                            by starting a new connection with different request

                            """

                            minCost = min(queries[action_n], key=lambda x: x["cost"])
                            print(f"{colorama.Fore.RED} Start connection to {minCost}")

                            address = minCost["address"]
                            host, port = address

                            print(f"address is {host} {port}")
                            # host, port = address

                            send_file(host, port, "test.c")

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


def send_file(host, port, filename):
    with open(filename, "rb") as f:
        data = f.read()

    request = create_request("file", data)
    start_connection(host, port, request)


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
