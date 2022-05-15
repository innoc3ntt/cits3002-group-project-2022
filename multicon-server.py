import sys
import socket
import selectors
import types
import time
import random
import os


sel = selectors.DefaultSelector()
random.seed(time.time())

# TESTING SENDING BINARY FILE
cwd = os.getcwd()
test = os.path.join(cwd, "test", "test_output")
file = open(test, "wb")



def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
            # file.write(data.outb)
            # file.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            time.sleep(random.randint(0, 5))
            print(f"Echoing {data.outb!r} to {data.addr}")
            file.write(data.outb)
            file.close()
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


# if len(sys.argv) != 3:
#     print(f"Usage: {sys.argv[0]} <host> <port>")
#     sys.exit(1)

# host, port = sys.argv[1], int(sys.argv[2])
host, port = ("127.0.0.1", 8000)

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
