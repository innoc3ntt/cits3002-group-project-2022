import os


def get_latest_file(self, directory):
    file_list = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    file = max(file_list, key=os.path.getctime)

    base_file = os.path.basename(file)
    print(f"Latest file is: {base_file}")

    return file
