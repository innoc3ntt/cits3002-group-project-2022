import re, subprocess, logging, socket, pickle
from parser import parse_file


logging.basicConfig(filename="output.log", filemode="w", level=logging.DEBUG)


def main():
    logging.info("Parsing rakefile")
    configs, actions = parse_file("rakefile1")
    logging.info("Rakefile parsed")

    HOST = "localhost"
    PORT = 8000

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        # trying to send action set to server, not sure if required but here if needed
        data_string = pickle.dumps(actions)
        s.send(data_string)
        data = s.recv(4096)
        data_arr = pickle.loads(data)

    print(f"Received {data_arr!r}")

    for actionset in actions:
        for action in actionset[1]:
            logging.info("running %s", action)
            try:
                process = subprocess.run(action, check=True, capture_output=True)
                logging.info(process.stdout)
            except subprocess.CalledProcessError as err:
                logging.error(err)
                raise RuntimeError(process.stderr)


if __name__ == "__main__":
    main()


def create_file(bytes, name):
    # convenience function to create a file to send
    pass
