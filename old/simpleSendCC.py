import selectors
import traceback


from utils import create_request, send_file, send_file_request


sel = selectors.DefaultSelector()


def main():
    host = "127.0.0.1"
    port = 65432

    files_to_send = ["test.c", "test2.c"]

    request_cc = create_request(
        "command", shell="cc", args=["-o", "output_file"], files=files_to_send
    )

    # start the action by sending requires
    if files_to_send:
        send_file(filename="test.c", address=(host, port), sel=sel, socket=None)
        files_to_send.pop(0)

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)

                    if message.response and message.jsonheader.content_type == "binary":
                        # if receive a binary response from server, means file succesfully received
                        if files_to_send:
                            # if there are still files to be sent
                            file = files_to_send.pop(0)
                            # create a new request
                            new_request = send_file_request(file)
                            message.update_request(new_request)
                        else:
                            # all files sent, can send the command now
                            message.update_request(request_cc)
                except Exception:
                    print(
                        f"Main: Error: Exception for {message.addr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
            # Check for a socket being monitored to continue.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")


if __name__ == "__main__":
    main()
