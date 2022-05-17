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
def event_loop(addresses):
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
    queues = []
    requires = [[] for x in actions]
    queries = [[] for x in actions]

    # mock actionset 1 only first
    for index, action in enumerate(actions[1:]):

        fd_action = []
        if action[-1][0] == "requires":
            for file in action[-1][1:]:
                requires[index].append(file)
            # remove the require for later processing
            action[-1].pop()

        for address in addresses:
            # for each host!
            host, port = address
            fd = start_connection(host, port, query)
            fd_action.append(fd)

        queues.append(fd_action)

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data

                """experimental"""
                try:
                    message.process_events(mask)

                    socket_no = key.fd
                    if message.response and (
                        message.jsonheader["content-type"] == "text/json"
                        or message.jsonheader["content-type"] == "file/received"
                    ):
                        # TODO: make a file/received type for libclient/libserver
                        # Process the server response to query request, if there is a response and type is query
                        action_n = in_list(socket_no, queues)

                        if action_n != -1:
                            # If there is a socket being awaited on, remove it from queue and store result
                            queues[action_n].remove(socket_no)
                            queries[action_n].append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["result"],
                                }
                            )

                        if not queues[action_n]:
                            """
                            if for an action, not waiting for any more sockets to return
                            determine the lowest bid and send the relevant action
                            by starting a new connection with different request
                            """

                            minCost = min(queries[action_n], key=lambda x: x["cost"])
                            print(f"{colorama.Fore.RED}Start connection to {minCost}")
                            host, port = minCost["address"]

                            # create buffer to store socket no to be returned
                            fd = []

                            for file in requires[action_n]:
                                # if there are files required to be sent for the action, send them
                                print(
                                    f"{colorama.Fore.BLUE}Sending file: {file} to {host} {port}"
                                )

                                fd.append(send_file(host, port, file))

                            queues[action_n].append(fd)

                            # TODO: Send multiple files!

                            # if no files or all the files have been sent
                            # TODO: keep track of when files have been sucessfully received
                            if not queues[action_n]:
                                # temporary loop to see again if queue is empty,
                                # TODO: refactor this
                                actions[1:][action_n]

                                print(f"{colorama.Fore.GREEN}FINALLY RUN ACTUAL ACTION")

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
    """
    Send a file on a host

        Parameters:
            host (str): host ip address
            port (int): port number
            filename (str): file to send

        Returns:
            int : socket fd
    """
    with open(filename, "rb") as f:
        data = f.read()

    request = create_request("file", data)
    return start_connection(host, port, request)


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

    event_loop(addresses)
    sel.close()


if __name__ == "__main__":
    main()
