import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from utilis import *

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
    local_path = event.src_path.replace(sys.argv[3], '')[1:]
    is_dir = "cf"
    if event.is_directory:
        is_dir = "cd"
    list.append(is_dir + local_path)


def on_deleted(event):
    local_path = event.src_path.replace(sys.argv[3], '')[1:]
    list.append("dd" + local_path)


def on_moved(event):
    src_path = event.src_path.replace(sys.argv[3], '')[1:]
    dst_path = event.dest_path.replace(sys.argv[3], '')[1:]
    is_dir = "mf"
    if event.is_directory:
        is_dir = "md"
    list.append(is_dir + src_path + SEPARATOR + dst_path)


def on_modified(event):
    modify = 'zf'
    if event.is_directory is False:
        local_path = event.src_path.replace(sys.argv[3], '')[1:]
        list.append(modify + local_path)


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


if __name__ == '__main__':
    #global ID
    #global CP_NUM
    my_observer = create_observer(sys.argv[3])
    my_observer.start()
    try:
        ID = sys.argv[5]
    except:
        pass
    register()
    print(ID)

    try:
        while True:

            time.sleep(int(sys.argv[4]))
            s = open_socket()
            pull(s, sys.argv[3])
            send_update(updates_list, s, sys.argv[3])
            s.close()
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()
