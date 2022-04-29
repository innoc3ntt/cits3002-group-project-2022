import os, re

global_vars = []
action_set = []

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
        elif line[0].isalpha():
            # if the line starts with a letter, or no spaces, start of an action set
            while line != "\n":
                line = next(file)
            action_set.append(chars)
        # else:
        #     if re.match(r"\s{4}", line):
        # if this is first line of command
        # if re.match(r"\s{8}", line):


print(global_vars)
# print(action_set)
