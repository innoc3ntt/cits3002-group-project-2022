import logging, traceback, selectors
import time
import sys

import colorama, dotsi
from parser import parse_file

from libclient import (
    create_request,
    reuse_connection,
    start_connection,
    send_query,
    send_file,
)

logging.basicConfig(filename="logs/all.log", filemode="w", level=logging.DEBUG)
logger = logging.getLogger("client")
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
)

fh = logging.FileHandler(filename="logs/client.log", mode="w")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)


ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.info("================= STARTING LOG ========================")
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
    queue = []
    queries = []
    requires = [[] for x in actions]
    ready_to_begin = [False for x in actions]
    alive_connections = [-1 for x in actions]
    action_number_sent = 0

    for index, action in enumerate(actions):
        # for each action, get required files in a buffer and send a query to all hosts
        if action[-1][0] == "requires":
            # find all the files required and put them in a buffer
            for file in action[-1][1:]:
                requires[index].append(file)
            # remove the empty require
            action.pop()

    def _query():
        logger.info(f"Querying cost for action: {action_number_sent}")
        for address in addresses:
            # for each host, query the cost for an action
            host, port = address
            queue.append(send_query(sel, host, port))

    # create an iterator to send query requests
    my_iter = iter(actions)

    """BEGIN QUERY"""
    next(my_iter)
    _query()

    try:
        while True:
            events = sel.select(timeout=1)

            for key, mask in events:
                time.sleep(1)
                message = key.data
                try:
                    message.process_events(mask)
                    socket_no = key.fd
                    if message.response:
                        if message.jsonheader.content_type == "text/json":
                            # Process the server response to query request, if there is a response and type is query
                            # If there is a socket being awaited on, remove it from queue and store result
                            queue.remove(socket_no)
                            queries.append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["cost"],
                                }
                            )
                            if not queue:
                                # if after dequeing, all queries have returned, ready to send action and query for next action
                                ready_to_begin[action_number_sent] = True

                                try:
                                    # while there are actions
                                    next(my_iter)
                                    _query()
                                except StopIteration:
                                    pass

                                action_number_sent += 1

                        """For returned connections"""
                        if socket_no in alive_connections:
                            """If it is for an existing connection, check which action it is for"""
                            action_num = alive_connections.index(socket_no)

                        elif ready_to_begin.count(True) > 0:
                            """Ready to begin a new action set"""
                            action_num = ready_to_begin.index(True)

                        else:
                            """Is not one of the above options"""
                            action_num = -1

                        if action_num >= 0:
                            """
                            if for an action, not waiting for any more sockets to return from query request

                            determine the lowest bid and send the relevant action
                            by starting a new connection with different request
                            """

                            if requires[action_num]:
                                """If file needs to be sent for current action"""
                                if message.jsonheader.content_type == "text/json":
                                    """if its a query response coming back, start file transfer for action"""
                                    minCost = dotsi.fy(
                                        min(queries, key=lambda x: x["cost"])
                                    )
                                    host, port = minCost.address
                                    file = requires[action_num].pop(0)
                                    logger.info(
                                        f"Starting action: {action_num} with lowest cost of {minCost.cost} to address {minCost.address}"
                                    )
                                    monitor_socket = send_file(
                                        filename=file,
                                        address=(host, port),
                                        sel=sel,
                                        socket=None,
                                    )
                                    # began the action, mark back false
                                    ready_to_begin[action_num] = False
                                    # keep track of which action to whick socket
                                    alive_connections[action_num] = monitor_socket
                                elif (
                                    alive_connections[action_num] > 0
                                    and message.jsonheader.content_type == "binary"
                                ):
                                    """
                                    if its a binary response, from an existing connection, previous file was sent succesfully
                                    send next file, update the message
                                    """
                                    file = requires[action_num].pop(0)
                                    reuse_connection(message, filename=file)
                            else:
                                """no files to send or all files have beeen sent"""
                                if message.jsonheader.content_type == "binary":
                                    """returning connection from sending a file"""
                                    print(message.jsonheader)
                                    action_to_do = actions[action_num]
                                    temp = action_to_do[0].split("-")

                                    if "remote" in temp:
                                        action_to_do[0] = temp[1]

                                    reuse_connection(
                                        message,
                                        command=action_to_do,
                                        keep_connection_alive=False,
                                    )

                                    ready_to_begin[action_num] = False
                                elif message.jsonheader.content_type == "text/json":
                                    """else no files to send, first request so just send the command, returning message is from a query"""
                                    action_to_do = actions[action_num]
                                    temp = action_to_do[0].split("-")

                                    if "remote" in temp:
                                        action_to_do[0] = temp[1]

                                    command_request = create_request(
                                        "command",
                                        command=action_to_do,
                                        keep_connection_alive=False,
                                    )
                                    start_connection(sel, host, port, command_request)
                                    ready_to_begin[action_num] = False

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

    for index, action_set in enumerate(action_sets):
        logger.info(f"Starting actionset: {index}")
        actions = action_set[1:]
        try:
            event_loop(addresses, actions)
        except RuntimeError as e:
            logger.exception(e)
            raise RuntimeError(e)


if __name__ == "__main__":
    main()
