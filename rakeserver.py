import sys
import socket
import selectors
import types
import pickle
import tempfile

HOST = "localhost"
PORT = 8002

file = open("test", "w")

temp = tempfile.TemporaryFile()


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
    # print(data)
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(4096)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        # This is where the data received by the server can be handled
        if data.outb:
            my_data = pickle.loads(data.outb)
            print(data.outb)
            temp.write(data.outb)
            file.write(my_data)
            file.close()
            print(f"Echoing {my_data!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write

            data.outb = data.outb[sent:]


sel = selectors.DefaultSelector()

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((HOST, PORT))
lsock.listen()
print(f"Listening on {(HOST, PORT)}")
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


temp.seek(0)
print(temp.read().decode("utf-8"))
temp.close()
