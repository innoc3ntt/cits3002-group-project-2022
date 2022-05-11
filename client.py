import re, subprocess, logging, socket, pickle

logging.basicConfig(filename="output.log", filemode="w", level=logging.DEBUG)


def parse_file(filename):
    configs = []
    actions = []
    buffer = []
    with open(filename) as file:
        for line in file:
            chars = line.split()

            if line.startswith("#"):
                continue

            if "=" in chars:
                # If line is a global variable

                temp = []
                for word in chars[2:]:
                    # Check if each option has an additional port given with :
                    if ":" in word:
                        temp.append(word.split(":"))
                    else:
                        temp.append(word)
                configs.append({chars[0]: temp})

            elif re.match(r"^.*\:$", line):
                # if line defines an actionset
                if len(actions):
                    # if actions is not empty
                    actions[-1].append(buffer)

                # create a new actionset and clear the buffer
                actions.append([line.split()[0]])
                buffer = []

            elif re.match(r"^\s{4}[a-z]", line):
                # if line begins with 4 spaces/1 tab, defines a command
                buffer.append(line.split())

            elif re.match(r"^\s{8}[a-z]", line):
                # if line beings with 8 spaces/2 tabs, defines additional arguments
                buffer[-1].append(line.split())

        # on last line of file, add the buffer to last action set
        actions[-1].append(buffer)

    return configs, actions


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
