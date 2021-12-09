# Noam Tzuberi 313374837 and Itay Shwartz 318528171

import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SEPARATOR = "<SEPARATOR>"
counter = 1


# ===============================================================================
# shrink_list - this function shrink the list - if command from some update appear in the black list - so
# is mean that the watch dog jump about action that the sender told him to to - so we prevent sending back the data,
# return 1 and pop the command from the black list
#
# command- command that we need to check if appear in the black list.
# black_list - list of commands that the sender told us to do
# ===============================================================================
def shrink_list(command, black_list):
    # shrink_modifies(updates_list)
    for i in range(len(black_list)):
        if command == black_list[i]:
            black_list.pop(i)
            return 1


# ===============================================================================
# push - this function send all the files and directories from a given path to receiver on given socket
#
# socket - socket to send
# path - path from the disk
# ===============================================================================
def push(socket, path):
    done = 0
    # we go throws all the file
    for root, dirs, files in os.walk(path, topdown=True):
        # for files
        for name in files:
            # the command that we sent it 'cf' (create file) + the path
            command = "cf" + (os.path.join(root, name).replace(path, ''))[1:]
            current_path = os.path.join(path, command[2:])
            # send the length of the command, and next the command
            socket.send((len(command.encode()).to_bytes(4, "big")))
            socket.send(command.encode())
            # ofter we send the file itself
            send_file(command, current_path, socket)
        # for directories
        for name in dirs:
            # the command that we sent it 'cd' (create dir)
            command = "cd" + os.path.join(root.replace(path, '')[1:], name)
            send_dir(command, socket)
    # when we finish go throws the file - we send done (0)
    socket.send(done.to_bytes(4, "big"))


# src_path - the absolute path (example sys.argv[3] or id)
# ===============================================================================
# pull - this function get from sender new updates
#
# socket - socket to send
# src_path - path from the disk
# black_list - list of commands thad the sender told us to do
# ===============================================================================
def pull(socket, src_path, black_list):
    # we receive commands until we receive size == 0
    while True:
        size = socket.recv(4)
        size = int.from_bytes(size, "big")
        if size == 0:
            break

        # we get new command, and take the action, is dir and local_path from it.
        command = (socket.recv(size)).decode(errors='ignore')
        action = command[:1]
        is_dir = command[1:2]
        local_path = command[2:]

        # create the full path from src_path and local_path
        full_path = os.path.join(src_path, local_path)

        # we go the the correct function according to the command that we received
        if action == "c":
            # we add to the black list only the command of creation - those are the problematic
            black_list.append(command)
            if is_dir == "d":
                receive_dir(full_path)
            else:
                receive_file(full_path, socket)

        elif action == "d":
            if os.path.isdir(full_path):
                delete_dirs(full_path)
            else:
                delete_file(full_path)
        # z mean modify
        elif action == "z":
            receive_modify(full_path, socket)

        elif action == "m":
            move_dir_file(src_path, local_path)


# ===============================================================================
# send_file - this function send file from sender to receiver
#
# path - the path of the file
# socket - to send data
# ===============================================================================
def send_file(command, path, socket):
    # first, if the receiver tell us that the file already exist on his computer - we return. else - we send
    is_exist = socket.recv(4)
    is_exist = int.from_bytes(is_exist, "big")
    if is_exist:
        return

    # we try to get the size if the file
    try:
        size_of_file = os.path.getsize(path)
    except:
        # if we cant get hime - we send that the size is 0 and return
        socket.send((0).to_bytes(4, "big"))
        return

    # else - we send the size of file
    socket.send(size_of_file.to_bytes(4, "big"))

    try:
        # send the file
        with open(path, "rb") as f:
            while True:
                # read the bytes from the file
                bytes_read = f.read(4096)

                # if we finish to read we close the file and get out
                if not bytes_read:
                    f.close()
                    break

                socket.send(bytes_read)
    except:
        pass


# ===============================================================================
# receive_file - this function received file from sender, and create it
#
# path - the path of the file
# socket - to send data
# ===============================================================================
def receive_file(path, socket):
    # send to the server if the file exist in our computer or not (1 or 0). if not exist - go out.
    if os.path.exists(path):
        socket.send((1).to_bytes(4, "big"))
        return
    socket.send((0).to_bytes(4, "big"))

    # get the size of the file that we get
    size_bytes = socket.recv(4)
    file_size = int.from_bytes(size_bytes, "big")

    first_read = 1
    try:
        # open new file on the path as f
        with open(path, "wb") as f:
            while True:
                # received bytes from the sender - 4096 or file_size
                bytes_read = socket.recv(min(4096, file_size))

                # if it the first read, and we dont get any bytes, we truncate the file, close it and break
                if first_read and not bytes_read:
                    f.truncate(0)
                    f.close()
                    break

                # write the bytes
                f.write(bytes_read)
                first_read = 0

                # update the new file size - the amount of bytes that we need to receive until we finish
                file_size = file_size - len(bytes_read)
                # if there is no bytes to received - close and break
                if file_size == 0:
                    f.close()
                    break
        print("create_file")
    # if problem had accrue when we receiving, we continue to received the amount of bytes that the server sent - that
    # how we keep the synchronize of the sender-receiver
    except:
        while True:
            bytes_read = socket.recv(min(4096, file_size))
            file_size = file_size - len(bytes_read)
            if file_size == 0:
                f.close()
                break


# ===============================================================================
#
#
# ===============================================================================
def send_dir(command, socket):
    socket.send((len(command.encode())).to_bytes(4, "big"))
    socket.send(command.encode("utf-8"))


# ===============================================================================
#
#
# ===============================================================================
def receive_dir(path):
    try:
        os.mkdir(path)
        print("create dir")
    except:
        pass


# ===============================================================================
#
#
# ===============================================================================
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
# ===============================================================================
#
#
# ===============================================================================
def delete_file(path):
    if os.path.exists(path):
        os.remove(path)
        print("delete file")


# ===============================================================================
#
#
# ===============================================================================
def send_modify(command, path, socket):
    send_file(command, path, socket)


# ===============================================================================
#
#
# ===============================================================================
def receive_modify(full_path, socket):
    socket.send((0).to_bytes(4, "big"))

    size_bytes = socket.recv(4)
    size_server = int.from_bytes(size_bytes, "big")
    server_file = b''

    try:
        while True:
            current_server_bytes = socket.recv(min(4096, size_server))
            # server_file.join(current_server_bytes)
            server_file = server_file + current_server_bytes

            length = len(current_server_bytes)
            size_server = size_server - length

            if size_server == 0:
                break
        client_file = open(full_path, 'rb')
        file_temp = client_file.read()
        client_file.close()
        if file_temp != server_file:
            client_file = open(full_path, 'wb')
            client_file.write(server_file)
            client_file.close()


    except:
        pass


# ===============================================================================
#
#
# ===============================================================================
def move_dir_file(src_path, local_path):
    try:
        src, dst = local_path.split(SEPARATOR)
        src = os.path.join(src_path, src)
        dst = os.path.join(src_path, dst)

        os.rename(src, dst)
        print("move file from server")

    except:
        pass


# ===============================================================================
#
#
# ===============================================================================
def update_list(command, list):
    list.append(command)


# ===============================================================================
#
#
# ===============================================================================
def send_update(list, socket, src_path):
    empty_list = 0
    for command in list:

        if command[:2] == "cf":
            absolute_path = os.path.join(src_path, command[2:])
            socket.send((len(command.encode()).to_bytes(4, "big")))
            socket.send(command.encode())
            send_file(command, absolute_path, socket)

        elif command[:2] == "zf":
            absolute_path = os.path.join(src_path, command[2:])
            socket.send((len(command.encode()).to_bytes(4, "big")))
            socket.send(command.encode())
            send_modify(command, absolute_path, socket)

        else:
            socket.send((len(command.encode())).to_bytes(4, "big"))
            socket.send(command.encode())
    list.clear()
    socket.send(empty_list.to_bytes(4, "big"))
