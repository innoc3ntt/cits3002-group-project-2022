import sys
import re


def parse_file(filename):
    configs = []
    actions = []
    buffer = []
    with open(filename) as file:
        for line in file:
            line = line.rstrip()
            chars = line.split()

            if line.startswith("#") or line == "\n":
                # SKIP COMMENTS AND EMPTY LINES
                continue

            if "=" in chars:
                # If line is a global variable

                temp = []
                for word in chars[2:]:
                    # Check if each option has an additional port given with :
                    temp.append(word)
                configs.append({chars[0]: temp})

            elif re.match(r"^.*\:$", line):
                # if line defines an actionset
                if len(actions):
                    # if actions is not empty
                    actions[-1].extend(buffer)

                # create a new actionset and clear the buffer
                actions.append([line.split()[0]])
                buffer = []

            elif re.match(r"^\s{4}[a-z]|\t{1}[a-z]", line):
                # if line begins with 4 spaces/1 tab, defines a command
                # FIXME: Convert to tabs instead of spaces
                actions[-1].append(line.split())

            elif re.match(r"^\s{8}[a-z]|\t{2}[a-z]", line):
                # if line beings with 8 spaces/2 tabs, defines additional arguments
                # FIXME: Convert to tabs instead of spaces
                actions[-1][-1].append(line.split())

                # FIXME : making a 2d array instead of 1D for requires

            # on last line of file, add the buffer to last action set
        if buffer:
            actions[-1].append(buffer)

    addresses = []

    for config in configs:
        if "PORT" in config.keys():
            port = config["PORT"][0]
            configs.remove(config)

    for index, config in enumerate(configs):
        if "HOSTS" in config.keys():
            for option in config["HOSTS"]:
                if ":" not in option:
                    config[index] = option + ":" + port
                    addresses.append((option, int(port)))
                else:
                    split = option.split(":")
                    addresses.append((split[0], int(split[1])))
    return addresses, actions


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename> ")
        sys.exit(1)

    addresses, actions = parse_file(sys.argv[1])

    print(addresses)
    print(actions)


if __name__ == "__main__":
    main()
