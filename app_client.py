import logging, traceback, selectors, yaml, logging.config, sys, os


from parser import parse_file
from libclient import (
    SubprocessFailedError,
    create_request,
    reuse_connection,
    start_connection,
    send_query,
    send_file,
)

logging.basicConfig(filename="logs/clients.log", filemode="w", level=logging.DEBUG)
with open("logger.yaml", "rt") as f:
    logging_config = yaml.safe_load(f.read())

logging.config.dictConfig(logging_config)
logger = logging.getLogger("client")


logger.info("================= STARTING LOG ========================")

"""
in an action set, for each action, run a query to all hosts
collect the returned costs, send a request to remote host,
which may involve sending a file for each action and receiving back a file from each host
"""


def event_loop(addresses, actions, port):
    """
    Run for each action in an actionset to query all the connected servers.
    will return the minimum bid server and it's ip address
    """
    sel = selectors.DefaultSelector()
    local_port = port

    # buffers to hold connection data per action
    queue = []
    queries = []
    requires = [[] for x in actions]
    ready_to_begin = [False for x in actions]
    alive_connections = [-1 for x in actions]
    query_n = 0

    for index, action in enumerate(actions):
        # for each action, get required files in a buffer and send a query to all hosts
        if action[-1][0] == "requires":
            # find all the files required and put them in a buffer
            for file in action[-1][1:]:
                requires[index].append(file)
            # remove the empty require
            action.pop()

    def _query():
        logger.info(f"Querying cost for action: {query_n}")
        for address in addresses:
            # for each host, query the cost for an action
            host, port = address
            queue.append(send_query(sel, host, port))

    def _remote_start(action_step, action_n):

        if "remote" in action_step[0]:
            _query()
        else:
            host, port = "localhost", local_port
            logger.info(f"=== Sending a request to localhost for {action_n} ===")

            if requires[action_n]:
                # if files required, start sending
                file = requires[action_n].pop(0)
                monitor_socket = send_file(
                    filename=file,
                    address=(host, port),
                    sel=sel,
                    socket=None,
                )
                # keep track of which action to whick socket
                alive_connections[action_n] = monitor_socket
            else:
                command_request = create_request(
                    "command",
                    command=action_step,
                    keep_connection_alive=False,
                )
                start_connection(sel, host, port, command_request)

    """BEGIN FIRST ACTION WITH QUERY AND CHECK IF REMOTE"""

    try:
        # create an iterator to send query requests
        my_iter = iter(actions)
        _remote_start(next(my_iter), 0)
    except Exception as e:
        logger.error(e)
        raise RuntimeError("Failed at start, problem with the iterator")

    try:
        while True:
            events = sel.select(timeout=1)

            for key, mask in events:
                # time.sleep(1)
                message = key.data
                try:
                    socket_no = key.fd
                    message.process_events(mask)

                    if message.response:
                        if (
                            message.jsonheader["content_type"] == "text/json"
                            and message.request["content"]["request"] == "query"
                        ):
                            # Process the server response to query request, if there is a response and type is query
                            # If there is a socket being awaited on, remove it from queue and store result
                            queue.remove(socket_no)
                            queries.append(
                                {
                                    "address": message.addr,
                                    "cost": message.response["cost"],
                                }
                            )

                            logger.debug(f"queries: {queries}")
                            logger.debug(f"queue: {queue}")
                            if not queue:
                                # if after dequeing, all queries have returned, ready to send action and query for next action
                                ready_to_begin[query_n] = True
                                query_n += 1
                                try:
                                    # while there are actions
                                    _remote_start(next(my_iter), query_n)
                                except StopIteration:
                                    # no more actions to perform
                                    pass

                        """For returned connections, second stage"""
                        if socket_no in alive_connections:
                            """If it is for an existing connection, check which action it is for"""
                            action_n = alive_connections.index(socket_no)

                        elif ready_to_begin.count(True) > 0:
                            """Ready to begin a new action set. find which action it is"""
                            action_n = ready_to_begin.index(True)

                        else:
                            """
                            Is not one of the above options,
                            - not an existing connection
                            - not a new action
                            unrecognized so mark as -1 to ignore
                            """
                            action_n = -1

                        if action_n >= 0:
                            """
                            if an existing connection or ready to start a new connection

                            determine the lowest bid for the action and send the relevant action
                            by starting a new connection with a file transfer or command request
                            """

                            if requires[action_n]:
                                """If file needs to be sent for current action"""
                                if message.jsonheader["content_type"] == "text/json":
                                    """if its a query response coming back, start file transfer for action"""

                                    minCost = min(queries, key=lambda x: x["cost"])
                                    address = minCost["address"]
                                    cost = minCost["cost"]
                                    host, port = address
                                    file = requires[action_n].pop(0)
                                    logger.info(
                                        f"Starting action: {action_n} with lowest cost of {cost} to address {address}"
                                    )
                                    monitor_socket = send_file(
                                        filename=file,
                                        address=(host, port),
                                        sel=sel,
                                        socket=None,
                                    )
                                    # began the action, mark back false
                                    ready_to_begin[action_n] = False
                                    # keep track of which action to whick socket
                                    alive_connections[action_n] = monitor_socket
                                    queries = []
                                elif (
                                    alive_connections[action_n] > 0
                                    and message.jsonheader["content_type"] == "binary"
                                ):
                                    """
                                    if its a binary response, from an existing connection, previous file was sent succesfully
                                    send next file, update the message
                                    """
                                    file = requires[action_n].pop(0)
                                    reuse_connection(message, filename=file)
                            else:
                                """no files to send or all files have beeen sent so send the command now"""
                                if message.jsonheader["content_type"] == "binary":
                                    """returning connection from sending a file"""
                                    new_action = check_remote(actions[action_n])

                                    reuse_connection(
                                        message,
                                        command=new_action,
                                        keep_connection_alive=False,
                                    )

                                    # reset the buffers
                                    ready_to_begin[action_n] = False
                                    alive_connections[action_n] = -1
                                elif message.jsonheader["content_type"] == "text/json":
                                    """else no files to send, first request so just send the command, returning message is from a query"""
                                    minCost = min(queries, key=lambda x: x["cost"])
                                    address = minCost["address"]
                                    cost = minCost["cost"]
                                    host, port = address
                                    logger.info(
                                        f"Starting action: {action_n} with lowest cost of {cost} to address {address}"
                                    )
                                    new_action = check_remote(actions[action_n])

                                    command_request = create_request(
                                        "command",
                                        command=new_action,
                                        keep_connection_alive=False,
                                    )

                                    start_connection(sel, host, port, command_request)
                                    # reset buffers
                                    ready_to_begin[action_n] = False
                                    queries = []
                except ConnectionRefusedError as e:
                    logger.debug(f"{socket_no}")
                    logger.debug(f"{queue}")
                    logger.error(f"{e} to {message.addr} on {socket_no}")

                    queue.remove(socket_no)
                    message.close()
                except SubprocessFailedError as e:
                    logger.critical(
                        f"Subprocess failed: {e} on request:{message.request['content']['command']} for action: {action_n}"
                    )
                    logger.critical(f"Stopping client")
                    exit(1)
                except Exception:
                    logger.error(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
            # Check for a socket being monitored to continue.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        raise KeyboardInterrupt()
    finally:
        sel.close()


def check_remote(action):
    """Check if an action is remote by parsing the first argument

    Args:
        action list(str): a list of the words of the actions

    Returns:
        list(str): the action with remote split if it is present
    """
    if "remote" in action[0]:
        action[0] = action[0].split("-")[1]
    return action


def main():
    """
    Parse a rakefile and then run an event loop for each action set

    Raises:
        RuntimeError: _description_
    """
    addresses, action_sets, port = parse_file(sys.argv[1])
    try:
        for index, action_set in enumerate(action_sets):
            logger.info(f"Starting actionset: {index}")
            actions = action_set[1:]
            try:
                event_loop(addresses, actions, port)
                logger.info(f"Actionset {index} completed successfully")
            except RuntimeError as e:
                logger.exception(e)
                raise RuntimeError(e)
            except KeyboardInterrupt as e:
                raise KeyboardInterrupt()
        logger.info("All actionsets completed successfully!")
    except KeyboardInterrupt as e:
        logger.error("Caught keyboard interrupt, exiting")


if __name__ == "__main__":
    main()
