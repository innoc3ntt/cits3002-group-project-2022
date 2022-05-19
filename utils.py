import os, socket, selectors, logging
import dotsi

import libclient


def start_connection(sel, host, port, request):
    """
    Returns:
        (int) socket number

    Parameters:
        sel (selector):
        host (str): ip address
        port (int): port number
        request (dict): dictionary
    """
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)

    return sock.fileno()


def get_file_data(filename):
    with open(filename, "rb") as f:
        data = f.read()
    return data


def query(sel, host, port):
    """Wrapper around start_connection to be called for each action to each host"""
    query = create_request("query")
    return start_connection(sel, host, port, query)


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


def get_latest_file(directory):
    file_list = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    file = max(file_list, key=os.path.getctime)

    base_file = os.path.basename(file)
    logging.debug(f"Latest file is: {base_file}")

    return file


def create_request(
    request,
    command=None,
    data=None,
    filename=None,
    keep_connection_alive=False,
):
    """
    Create a request to pass to start_connection
    One of three types
    - query
    - command
    - file

    Parameters:
        request (str): type of request, query, command or file
        action (int): action number associated with
        args: extra args to pass to a "command" request
        shell: command to pass to shell, default echo
        files: name of files to send

    Returns:
        (dict) A dictionary representing the request object
    """
    if request == "query":
        return dotsi.Dict(
            type="text/json",
            encoding="utf-8",
            content=dict(request=request),
        )
    elif request == "command":
        return dotsi.Dict(
            type="command",
            encoding="utf-8",
            content=dict(request=request, command=command),
        )
    elif request == "file":
        return dotsi.Dict(
            type="binary",
            encoding="binary",
            content=data,
            filename=filename,
            keep_connection_alive=keep_connection_alive,
        )


def send_file(filename, address, sel, socket=None):
    host, port = address
    data = get_file_data(filename)
    request = create_request(
        "file", data=data, filename=filename, keep_connection_alive=True
    )

    if socket is None:
        return start_connection(sel, host, port, request)
    else:
        message = libclient.Message(sel, socket, address, request)
        sel.modify(socket, events=selectors.EVENT_WRITE, data=message)
        return socket.fileno()


def send_file_request(filename):
    data = get_file_data(filename)
    request = create_request(
        "file", data=data, filename=filename, keep_connection_alive=True
    )

    return request
