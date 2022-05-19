import socket
import selectors
import traceback

import colorama, dotsi

import libclient
from utils import create_request, start_connection, in_list, query


sel = selectors.DefaultSelector()
colorama.init(autoreset=True)


# if len(sys.argv) != 5:
#     print(f"Usage: {sys.argv[0]} <host> <port> <action> <value>")
#     sys.exit(1)

# host, port = sys.argv[1], int(sys.argv[2])
# action, value = sys.argv[3], sys.argv[4]
# request = create_request(action, value)

"""
in an action set, for each action, run a query to all hosts
collect the returned costs, send a request to remote host,
which may involve sending a file for each action and receiving back a file from each host
"""


# first query
def event_loop(addresses):
    """
    Run for each action in an actionset to query all the connected servers.
    will return the minimum bid server and it's ip address

    """

    # mock the actionset input here
    actions = [
        "actionset1:",
        ["remote-cc", "test.c", ["requires", "test.c"]],
        # ["echo", "hello"],
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
            # remove the requires for later processing
            action.pop()

        for address in addresses:
            # for each host!
            host, port = address
            fd_action.append(query(sel, host, port))

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
                        message.jsonheader.content_type == "text/json"
                    ):
                        # TODO: make a file/received type for libclient/libserver
                        # Process the server response to query request, if there is a response and type is query
                        action_n = in_list(socket_no, queues)

                        if action_n != -1:
                            # If there is a socket being awaited on, remove it from queue and store result
                            queues[action_n].remove(socket_no)

                            # print(f"{colorama.Fore.CYAN} Received {message} ")

                            queries[action_n].append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["cost"],
                                }
                            )

                    #     if not queues[action_n]:
                    #         """
                    #         if for an action, not waiting for any more sockets to return
                    #         determine the lowest bid and send the relevant action
                    #         by starting a new connection with different request
                    #         """

                    #         minCost = min(queries[action_n], key=lambda x: x["cost"])
                    #         # print(f"{colorama.Fore.RED}Start connection to {minCost}")
                    #         host, port = minCost["address"]

                    #         # create buffer to store socket no to be returned
                    #         fd = []

                    #         # for file in requires[action_n]:
                    #         #     # if there are files required to be sent for the action, send them

                    #         # TODO: Send multiple files!
                    #         # send the first file
                    #         msg = send_file(host, port, file, 2)
                    #         fd.append(msg.sock.fileno())
                    #         print(
                    #             f"{colorama.Fore.BLUE}Sending file: {file} to {host} {port} {msg.sock}"
                    #         )
                    #         # with open("test2.c", "rb") as f:
                    #         #     data = f.read()
                    #         # msg.request = create_request("file",args = data)
                    #         # print("sending second file")
                    #         queues[action_n].extend(fd)
                    #         # if no files or all the files have been sent
                    #         # TODO: keep track of when files have been sucessfully received

                    # # the socket has returned
                    # if message.response and (
                    #     message.jsonheader["content-type"] == "binary"
                    # ):

                    #     action_n = in_list(socket_no, queues)

                    #     if queues[action_n]:
                    #         # trying to load the same socket with a new request
                    #         # TODO: add filename and number of files into header?
                    #         with open("test2.c", "rb") as f:
                    #             data = f.read()
                    #         new_request = create_request("file", args=data)

                    #         reused_sock = msg.sock
                    #         message = libclient.Message(
                    #             sel, reused_sock, msg.addr, new_request
                    #         )

                    #         # msg._set_selector_events_mask("w")
                    #         # msg._request_queued = False

                    #         print("sending second file")

                    # the queue will currently hold all the connections which a file has been sent and awaiting a reply
                    # which action is the returning socket for?

                    # if action_n != -1:
                    #     # If there is a socket being awaited on, remove it from queue
                    #     queues[action_n].remove(socket_no)

                    # if not queues[action_n]:
                    #     # temporary loop to see again if queue is empty,if so run the action
                    #     # TODO: refactor this
                    #     actions[1:][action_n]

                    #     print(f"{colorama.Fore.GREEN}FINALLY RUN ACTUAL ACTION")

                    #     # mock assume that file sucessfully sent
                    #     actions[1:][action_n]

                    #     request = create_request(
                    #         "command",
                    #         shell="cc",
                    #         args=["-o", "output"],
                    #         files=requires[action_n],
                    #         action=action_n,
                    #     )

                    # start_connection(host, port, request)
                    # TODO: receive the output file and do something with it here

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


def send_file(host, port, filename, action):
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

    request = create_request(request="file", args=data, action=action)
    # return 1

    return start_connection(host, port, request)


def main():
    # parser(filename)

    # mock return of parser
    host = "127.0.0.1"
    port = 65432
    port2 = 65431

    addresses = [(host, port)]

    event_loop(addresses)
    sel.close()


if __name__ == "__main__":
    main()
