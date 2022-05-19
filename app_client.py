import logging, traceback, selectors
import sys

import colorama, dotsi
from parser import parse_file

from utils import (
    create_request,
    send_file_request,
    start_connection,
    in_list,
    query,
    send_file,
)


colorama.init(autoreset=True)


"""
in an action set, for each action, run a query to all hosts
collect the returned costs, send a request to remote host,
which may involve sending a file for each action and receiving back a file from each host
"""


def event_loop(addresses, actions):
    """
    Run for each action in an actionset to query all the connected servers.
    will return the minimum bid server and it's ip address

    """
    sel = selectors.DefaultSelector()

    # buffers to hold connection data per action
    queues = []
    requires = [[] for x in actions]
    queries = [[] for x in actions]
    running_socket = [-1 for x in actions]
    again = [-1 for x in actions]

    for index, action in enumerate(actions):

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
                    action_n = in_list(socket_no, queues)

                    if message.response and (
                        message.jsonheader.content_type == "text/json"
                    ):

                        # Process the server response to query request, if there is a response and type is query
                        if action_n != -1:
                            # If there is a socket being awaited on, remove it from queue and store result
                            queues[action_n].remove(socket_no)
                            queries[action_n].append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["cost"],
                                }
                            )
                            if not queues[action_n]:
                                # if after dequeing, that was the last socket being awaited on for queries, ready to send next
                                running_socket[action_n] = 1
                        else:
                            continue

                    if again.count(socket_no) > 0:
                        action_num = again.index(socket_no)

                    elif running_socket.count(1) > 0:
                        action_num = running_socket.index(1)

                    if message.response and (
                        again.count(socket_no) > 0 or running_socket.count(1) > 0
                    ):
                        """
                        if for an action, not waiting for any more sockets to return from query request

                        determine the lowest bid and send the relevant action
                        by starting a new connection with different request
                        """

                        if (
                            requires[action_num]
                            and message.jsonheader.content_type == "text/json"
                        ):
                            # if its a query response coming back, initiate file transfers
                            minCost = dotsi.fy(
                                min(queries[action_num], key=lambda x: x["cost"])
                            )
                            host, port = minCost.address

                            file = requires[action_num].pop(0)
                            monitor_socket = send_file(
                                filename=file,
                                address=(host, port),
                                sel=sel,
                                socket=None,
                            )
                            running_socket[action_num] = -1
                            again[action_num] = monitor_socket
                        elif (
                            again[action_num] > 0
                            and requires[action_num]
                            and message.jsonheader.content_type == "binary"
                        ):
                            """
                            if its a binary response, files was sent succesfully
                            if there are any additional files to be sent, update the message
                            """
                            file = requires[action_num].pop(0)
                            new_request = send_file_request(file)
                            message.update_request(new_request)
                        elif (
                            message.jsonheader.content_type == "binary"
                            and not requires[action_num]
                        ):
                            """if its a binary response and no more files to send, send the command"""
                            action_to_do = actions[action_num]
                            temp = action_to_do[0].split("-")
                            if "remote" in temp:
                                action_to_do[0] = temp[1]

                            update_request = create_request(
                                "command",
                                command=action_to_do,
                            )
                            message.update_request(update_request)
                            running_socket[action_num] = -1
                        elif (
                            not requires[action_num]
                            and message.jsonheader.content_type == "text/json"
                        ):
                            """
                            else no files to send, just send the command, returning message is from a query
                            """
                            action_to_do = actions[action_num]
                            temp = action_to_do[0].split("-")
                            if "remote" in temp:
                                action_to_do[0] = temp[1]

                            print(
                                f"{colorama.Fore.MAGENTA}ACTION TO DO IS: {action_to_do}"
                            )

                            command_request = create_request(
                                "command", command=action_to_do
                            )
                            start_connection(sel, host, port, command_request)
                            running_socket[action_num] = -1
                            again[action_num] = -1

                except Exception:
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
                    raise RuntimeError("ERROR BRO")
            # Check for a socket being monitored to continue.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()


def main():

    addresses, action_sets = parse_file(sys.argv[1])

    for action_set in action_sets:
        actions = action_set[1:]
        try:
            event_loop(addresses, actions)
        except RuntimeError as e:
            # logging.exception(e)
            raise RuntimeError("FUCK!")


if __name__ == "__main__":
    main()
