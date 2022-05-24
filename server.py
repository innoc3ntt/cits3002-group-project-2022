import io
import json
import sys
import socket
import selectors
import types
import struct

HOST = "localhost"
PORT = 8000

sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def _json_decode(json_bytes, encoding):
    tiow = io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="")
    obj = json.load(tiow)
    tiow.close()
    return obj

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read

        if recv_data:
            proto = recv_data[:2]
            proto = struct.unpack(">H", proto)[0]
            print(f'len: {len(recv_data)}, recv_data: {recv_data}')
            recv_data = recv_data[2:]
            try:

                print(f"proto: {proto}")

                print(f"proto-unpacked: {proto}")
                json_msg = _json_decode(recv_data,"utf-8")
                print(f"received: {json_msg}")
                print(f"unpack {struct.unpack('<H',recv_data)[0]}")

            except Exception as e:
                print(e)
            data.outb += recv_data
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb!r} to {data.addr}")
            sent = sock.send(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
