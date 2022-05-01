import re

configs = []
actions = []
buffer = []

with open("rakefile") as file:
    for line in file:
        chars = line.split()

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

print(actions)
