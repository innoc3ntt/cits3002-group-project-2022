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
                # FIXME: Convert to tabs instead of spaces
                actions[-1].append(line.split())

            elif re.match(r"^\s{8}[a-z]", line):
                # if line beings with 8 spaces/2 tabs, defines additional arguments
                # FIXME: Convert to tabs instead of spaces
                actions[-1][-1].append(line.split())

                # FIXME : making a 2d array instead of 1D for requires

            # on last line of file, add the buffer to last action set
        if buffer:
            actions[-1].append(buffer)

    return configs, actions


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename> ")
        sys.exit(1)

    configs, actions = parse_file(sys.argv[1])

    print(configs)
    print(actions)

    actionset1 = actions[0]
    action1_1 = actionset1[1][0]

    if action1_1[-1][0] == "requires":
        files = action1_1[-1]
        files = files[1:]

    # print(files)


if __name__ == "__main__":
    main()
