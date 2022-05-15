import sys
import socket
import selectors
import types

sel = selectors.DefaultSelector()
# messages = [b"Message 1 from client.", b"Message 2 from client."]
messages = []

file = open("a.out", "rb")
file_data = file.read()
messages.append(file_data)

print(file_data)


def start_connections(host, port, num_conns):
    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i + 1
        print(f"Starting connection {connid} to {server_addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        data = types.SimpleNamespace(
            addr=server_addr,
            connid=connid,
            msg_total=sum(len(m) for m in messages),
            recv_total=0,
            messages=messages.copy(),
            outb=b"",
        )
        sel.register(sock, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print(
                f"Received {recv_data!r} from from address {data.addr} connection {data.connid}"
            )
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            print(f"Closing connection {data.connid}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print(f"Sending {data.outb!r} to connection {data.connid}")
            sent = sock.sendall(data.outb)  # Should be ready to write
            data.outb = data.outb[sent:]


# def send_file(self, filename):
#     print("Sending:", filename)
#     with open(filename, "rb") as f:
#         raw = f.read()
#     # Send actual length ahead of data, with fixed byteorder and size
#     self.sock.sendall(len(raw).to_bytes(8, "big"))
#     # You have the whole thing in memory anyway; don't bother chunking
#     self.sock.sendall(raw)


if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <host> <port> <num_connections>")
    sys.exit(1)

host, port, num_conns = sys.argv[1:4]
start_connections(host, int(port), int(num_conns))

# start_connections("127.0.0.1", 65432, 1)
# start_connections("127.0.0.1", 65431, 1)

try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                service_connection(key, mask)
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
