import sys, socket, selectors, traceback, logging, logging.config, yaml

import libserver


sel = selectors.DefaultSelector()

logging.basicConfig(filename="logs/servers.log", filemode="w", level=logging.DEBUG)
with open("logger.yaml", "rt") as f:
    logging_config = yaml.safe_load(f.read())

logging.config.dictConfig(logging_config)
logger = logging.getLogger("server")

logger.info("================= STARTING LOG ========================")


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    logger.info(f">>> Accepted connection from {addr}")
    conn.setblocking(False)
    message = libserver.Message(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)


if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
logger.info(f"Listening on {(host, port)}")
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
except KeyboardInterrupt:
    logger.error("Caught keyboard interrupt, exiting")
finally:
    sel.close()