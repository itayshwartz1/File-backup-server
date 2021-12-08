import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SEPARATOR = "<SEPARATOR>"
check_path = ''


def shrink_list(updates_list):
    for i in range(len(updates_list)-1):
        if updates_list[i][:1] == "c":
            try:
                src, dst = updates_list[i + 1].split(SEPARATOR)
                if src == "m" + updates_list[i][1:]:
                    updates_list[i] = "c" + updates_list[i][1:2] + dst
                    updates_list.pop(i + 1)
            except:
                pass


def check_duplicates(path):
    global check_path
    if path == check_path:
        print('check_duplicates work')
        return 1
    return 0


# path- is the path from the disk
def push(socket, path):
    done = 0
    for root, dirs, files in os.walk(path, topdown=True):
        for name in files:
            command = "cf" + (os.path.join(root, name).replace(path, ''))[1:]
            current_path = os.path.join(path, command[2:])
            send_modify(command, current_path, socket)
        for name in dirs:
            command = "cd" + os.path.join(root.replace(path, '')[1:], name)
            send_dir(command, socket)

    socket.send(done.to_bytes(4, "big"))


# src_path - the absolute path (example sys.argv[3] or id)
def pull(socket, src_path):
    global check_path
    while True:
        size = socket.recv(4)
        size = int.from_bytes(size, "big")
        if size == 0:
            check_path = ''
            break
        command = (socket.recv(size)).decode(errors='ignore')
        action = command[:1]
        is_dir = command[1:2]
        local_path = command[2:]

        full_path = os.path.join(src_path, local_path)
        check_path = full_path

        if action == "c":
            if is_dir == "d":
                receive_dir(full_path)
            else:
                receive_modify(full_path, socket)

        elif action == "d":
            if os.path.isdir(full_path):
                delete_dirs(full_path)
            else:
                delete_file(full_path)

        elif action == "z":
            receive_modify(full_path, socket)

        elif action == "m":
            move_dir_file(src_path, local_path)



# path the path from disk
# command - action to do + path from the local folder
def send_file(command, path, socket):
    try:
        size_of_file = os.path.getsize(path)
    except:
        socket.send((0).to_bytes(4, "big"))
        return

    socket.send(size_of_file.to_bytes(4, "big"))

    try:
        with open(path, "rb") as f:
            while True:
                # read the bytes from the file
                bytes_read = f.read(4096)
                # the size of the bytes
                # bytes_len = len(bytes_read)
                # # send the len
                # socket.sendall(bytes_len.to_bytes(4, "big", signed=True))
                if not bytes_read:
                    f.close()
                    # file transmitting is done
                    break
                # busy networks
                # client_socket.sendall(bytes_read)
                socket.send(bytes_read)
    except:
        pass


def receive_file(path, socket):
    size_bytes = socket.recv(4)
    file_size = int.from_bytes(size_bytes, "big")
    first_read = 1

    try:
        with open(path, "wb") as f:
            while True:
                bytes_read = socket.recv(min(4096, file_size))
                if first_read and not bytes_read:
                    f.truncate(0)
                    f.close()
                    break
                f.write(bytes_read)
                first_read = 0
                file_size = file_size - len(bytes_read)
                if file_size == 0:
                    f.close()
                    break
        print("create_file")
    except:
        pass


def send_dir(command, socket):
    socket.send((len(command.encode())).to_bytes(4, "big"))
    socket.send(command.encode("utf-8"))


def receive_dir(path):
    try:
        os.mkdir(path)
        print("create dir")
    except:
        pass


def delete_dirs(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            if os.path.exists(os.path.join(root, name)):
                os.remove(os.path.join(root, name))
                print("delete file")
        if os.path.exists(root):
            os.rmdir(root)
        print("delete dir")


# not sure we need it
def delete_file(path):
    if os.path.exists(path):
        os.remove(path)
        print("delete file")


def send_modify(command, path, socket):
    socket.send((len(command.encode())).to_bytes(4, "big"))
    socket.send(command.encode())

    send_file(command, path, socket)
    size_bytes = socket.recv(4)
    to_create = int.from_bytes(size_bytes, "big")
    if to_create:
        send_file(command, path, socket)


def receive_modify(full_path, socket):
    # is there is change
    real_modify = 0

    size_bytes = socket.recv(4)
    size_server = int.from_bytes(size_bytes, "big")
    try:
        size_client = os.path.getsize(full_path)
    except:
        real_modify = 1
        size_client = 0
    try:
        if size_client != size_server:
            real_modify = 1
        try:
            f = open(full_path, "rb")
            # with open(full_path, "rb") as f:
        except:
            real_modify = 1
        while True:
            server_bytes = socket.recv(min(4096, size_server))

            length = len(server_bytes)

            if not real_modify:
                my_bytes = f.read(length)
                if my_bytes != server_bytes:
                    real_modify = 1

            size_server = size_server - length

            if size_server == 0:
                break

        socket.send(real_modify.to_bytes(4, "big"))
        if real_modify:
            receive_file(full_path, socket)
        f.close()
    except:
        pass


def move_dir_file(src_path, local_path):
    try:
        src, dst = local_path.split(SEPARATOR)
        src = os.path.join(src_path, src)
        dst = os.path.join(src_path, dst)

        os.rename(src, dst)
        print("move file from server")

    except:
        pass


def update_list(command, list):
    list.append(command)


def send_update(list, socket, src_path):
    empty_list = 0
    for command in list:
        if command[:2] == "cf":
            absolute_path = os.path.join(src_path, command[2:])
            send_modify(command, absolute_path, socket)
        elif command[:2] == "zf":
            absolute_path = os.path.join(src_path, command[2:])
            send_modify(command, absolute_path, socket)
        else:
            socket.send((len(command.encode())).to_bytes(4, "big"))
            socket.send(command.encode())
    list.clear()
    socket.send(empty_list.to_bytes(4, "big"))
