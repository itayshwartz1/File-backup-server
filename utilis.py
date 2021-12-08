import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SEPARATOR = "<SEPARATOR>"


# path the path from disk
# command - action to do + path from the local folder
def send_file(command, path, socket):
    socket.send(len(command).to_bytes(4, "big"))
    socket.send(command.encode())

    size_of_file = os.path.getsize(path)
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


def push_dir(command, socket):
    socket.send(len(command).to_bytes(4, "big"))
    socket.send(command.encode("utf-8"))


# path- is the path from the disk
def push(socket, path):
    done = 0
    for root, dirs, files in os.walk(path, topdown=True):
        for name in files:
            command = "cf" + (os.path.join(root, name).replace(path, ''))[1:]
            send_file(command, path, socket)
        for name in dirs:
            command = "cd" + os.path.join(root.replace(path, '')[1:], name)
            push_dir(command, socket)

    socket.send(done.to_bytes(4, "big"))


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

# src_path - the absolute path (example sys.argv[3] or id)
def pull(socket, src_path):
    while True:
        size = (socket.recv(4)).to_bytes(4, "big")
        if size == 0:
            break
        command = (socket.recv(size)).decode()
        action = command[:1]
        is_dir = command[1:2]
        local_path = command[2:]

        full_path = os.path.join(src_path, local_path)
        if action == "c":
            if is_dir == "d":
                receive_dir(full_path)
            else:
                receive_file(full_path, socket)

        elif action == "d":
            if is_dir == "d":
                delete_dirs(full_path)
            else:
                delete_file(full_path)

        elif action == "z":
            receive_modify(full_path, socket)

        elif action == "m":
            move_dir_file(src_path, local_path)


def receive_modify(full_path, socket):

    size_bytes = socket.recv(4)
    size_server = int.from_bytes(size_bytes, "big")
    size_client = os.path.getsize(full_path)
    # for empty file
    first_read = True

    # is there is change
    real_modify = False

    # all the bytes we got
    all_bytes = b''

    try:
        if size_client != size_server:
            real_modify = True

        with open(full_path, "rb") as f:
            while True:
                server_bytes = socket.recv(min(4096, size_server))
                length = len(server_bytes)
                # if first_read and not bytes_read:
                #     f.truncate(0)
                #     f.close()
                #     break
                my_bytes = f.read(length)
                if my_bytes != server_bytes:
                    real_modify = True
                all_bytes = all_bytes.join([all_bytes, server_bytes])
                size_server = size_server - length
                if size_server == 0:
                    f.close()
                    break

        if real_modify:
            with open(full_path, "wb") as f:
                f.write(all_bytes)
                print("modify file from server")
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


def modify_file(command, path, socket):
    send_file(command, path, socket)


def send_update(list, socket, src_path):
    for command in list:
        if command[:2] == "cf":
            absolute_path = src_path + command[2:]
            send_file(command, absolute_path, socket)
        elif command[:2] == "zf":
            absolute_path = src_path + command[2:]
            modify_file(command, absolute_path, socket)
        else:
            socket.send(len(command).to_bytes(4, "big"))
            socket.send(command.encode())


# not sure we need it
def delete_file(path):
    if os.path.exists(path):
        os.remove(path)
        print("delete file")


def receive_file(path, socket):
    # if os.path.exists(path):
    #     return
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


def update_list(command, list):
    list.append(command)
