import os, re

global_vars = []
action_set = []
buffer = []

with open("rakefile") as file:
    for line in file:
        chars = line.split()
        # If line is a global variable
        if "=" in chars:
            # Check if each option has an additional port given with :
            temp = []
            for word in chars[2:]:
                if ":" in word:
                    temp.append(word.split(":"))
                else:
                    temp.append(word)
            global_vars.append({chars[0]: temp})

        if re.match(r"^.*\:$", line):
            if len(action_set) > 0:
                action_set[-1].append(buffer)
            action_set.append([line.split()[0]])
            # clear the buffer
            buffer = []

        if re.match(r"^\s{4}[a-z]", line):
            buffer.append(line.split())

        if re.match(r"^\s{8}[a-z]", line):
            # if this is first line of command
            buffer[-1].append(line.split())

    action_set[-1].append(buffer)

print(action_set)
