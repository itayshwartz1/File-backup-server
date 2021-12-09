import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from utils import *

ID = '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
CP_NUM = 0
my_observer = None
empty_id = '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
SEPARATOR = "<SEPARATOR>"
updates_list = []


def open_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((sys.argv[1], int(sys.argv[2])))
    return s


def register():
    global ID
    global CP_NUM
    global empty_id

    to_push = 0
    if ID == empty_id:
        to_push = 1
    s = open_socket()
    s.send(ID.encode() + CP_NUM.to_bytes(4, "big"))
    identity = s.recv(132)
    ID = identity[:128].decode("utf-8")
    CP_NUM = int.from_bytes(identity[128:132], "big")

    if to_push:
        push(s, sys.argv[3])
    else:
        pull(s, sys.argv[3])
    s.close()


def on_created(event):
    global updates_list
    global check_path
    if check_duplicates(event.src_path):
        return
    local_path = event.src_path.replace(sys.argv[3], '')[1:]
    is_dir = "cf"
    if event.is_directory:
        is_dir = "cd"
    updates_list.append(is_dir + local_path)
    print("create_file")


def on_deleted(event):
    global updates_list
    global check_path
    if check_duplicates(event.src_path):
        return
    local_path = event.src_path.replace(sys.argv[3], '')[1:]
    updates_list.append("dd" + local_path)
    print("delete_file")


def on_moved(event):
    global updates_list
    src_path = event.src_path.replace(sys.argv[3], '')[1:]
    dst_path = event.dest_path.replace(sys.argv[3], '')[1:]
    global check_path
    if check_duplicates(os.path.join(src_path + SEPARATOR + dst_path)):
        return
    is_dir = "mf"
    if event.is_directory:
        is_dir = "md"
    updates_list.append(is_dir + src_path + SEPARATOR + dst_path)
    print("move_file")


def on_modified(event):
    global updates_list
    global check_path
    if check_duplicates(event.src_path):
        return
    modify = 'zf'
    if event.is_directory is False:
        local_path = event.src_path.replace(sys.argv[3], '')[1:]
        updates_list.append(modify + local_path)
        print("modify_file")


def create_observer(path):
    global my_observer
    my_event_handler = PatternMatchingEventHandler(["*"], None, False, True)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_event_handler.on_modified = on_modified
    my_event_handler.on_moved = on_moved

    my_observer = Observer()
    my_observer.schedule(my_event_handler, path, recursive=True)

    return my_observer


def send_identity(s):
    global ID
    global CP_NUM
    s.send(ID.encode() + CP_NUM.to_bytes(4, "big"))


def send_list(updates_list, s):

    shrink_list(updates_list)
    empty_list = 0
    # move all the command in list
    for command in updates_list:
        # the length of the command
        s.send((len(command.encode())).to_bytes(4, "big"))
        # the command itself
        s.send(command.encode())

    # the list is empty
    s.send(empty_list.to_bytes(4, "big"))


if __name__ == '__main__':

    try:
        ID = sys.argv[5]
        os.mkdir(sys.argv[3])
    except:
        pass
    my_observer = create_observer(sys.argv[3])
    my_observer.start()
    register()
    print(ID)

    try:
        while True:
            time.sleep(int(sys.argv[4]))
            print('start connection')
            s = open_socket()

            send_identity(s)
            pull(s, sys.argv[3])
            send_list(updates_list, s)
            send_update(updates_list, s, sys.argv[3])

            s.close()
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()
