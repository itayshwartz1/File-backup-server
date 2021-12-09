import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

SEPARATOR = "<SEPARATOR>"
check_path = ''
counter = 1


def shrink_create_modifies(updates_list):
    try:
        for i in range(len(updates_list)):
            if updates_list[i][:2] == "cf":
                if updates_list[i][:2] == updates_list[i + 1][:2] and updates_list[i + 1][:1] == 'z':
                    updates_list.pop(i)
    except:
        pass


def shrink_modifies(updates_list):
    try:
        for i in range(len(updates_list)):
            if updates_list[i][:1] == "z":
                if updates_list[i] == updates_list[i + 1]:
                    updates_list.pop(i)
    except:
        pass
    shrink_create_modifies(updates_list)


def shrink_list(updates_list, black_list):
    # shrink_modifies(updates_list)
    try:
        for i in range(len(updates_list)):
            for j in range(len(black_list)):
                if updates_list[i] == black_list[j]:
                    updates_list.pop(i)
                    black_list.pop(j)
                    print('delete from black list')
                    break
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
            socket.send((len(command.encode()).to_bytes(4,"big")))
            socket.send(command.encode())

            send_file(command, current_path, socket)
        for name in dirs:
            command = "cd" + os.path.join(root.replace(path, '')[1:], name)
            send_dir(command, socket)

    socket.send(done.to_bytes(4, "big"))


# src_path - the absolute path (example sys.argv[3] or id)
def pull(socket, src_path, black_list):
    global counter

    while True:
        size = socket.recv(4)
        size = int.from_bytes(size, "big")
        if size == 0:
            # check_path = ''
            break
        command = (socket.recv(size)).decode(errors='ignore')
        action = command[:1]
        is_dir = command[1:2]
        local_path = command[2:]

        full_path = os.path.join(src_path, local_path)
        # check_path = full_path
        # black_list.append(command)

        if action == "c":
            if is_dir == "d":
                receive_dir(full_path)
            else:
                receive_file(full_path, socket)

        elif action == "d":
            if os.path.isdir(full_path):
                delete_dirs(full_path)
            else:
                delete_file(full_path)

        elif action == "z":
            receive_modify(full_path, socket)

        elif action == "m":
            move_dir_file(src_path, local_path)
        print(counter)
        counter = counter + 1


# path the path from disk
# command - action to do + path from the local folder
# def send_file(command, path, socket):
#     try:
#         size_of_file = os.path.getsize(path)
#     except:
#         socket.send((0).to_bytes(4, "big"))
#         return
#
#     socket.send(size_of_file.to_bytes(4, "big"))
#
#     try:
#         with open(path, "rb") as f:
#             while True:
#                 # read the bytes from the file
#                 bytes_read = f.read(4096)
#                 # the size of the bytes
#                 # bytes_len = len(bytes_read)
#                 # # send the len
#                 # socket.sendall(bytes_len.to_bytes(4, "big", signed=True))
#                 if not bytes_read:
#                     f.close()
#                     # file transmitting is done
#                     break
#                 # busy networks
#                 # client_socket.sendall(bytes_read)
#                 socket.send(bytes_read)
#     except:
#         pass


# def receive_file(path, socket):
#     size_bytes = socket.recv(4)
#     file_size = int.from_bytes(size_bytes, "big")
#     first_read = 1
#
#     try:
#         with open(path, "wb") as f:
#             while True:
#                 bytes_read = socket.recv(min(4096, file_size))
#                 if first_read and not bytes_read:
#                     f.truncate(0)
#                     f.close()
#                     break
#                 f.write(bytes_read)
#                 first_read = 0
#                 file_size = file_size - len(bytes_read)
#                 if file_size == 0:
#                     f.close()
#                     break
#         print("create_file")
#     except:
#         while True:
#             bytes_read = socket.recv(min(4096, file_size))
#             file_size = file_size - len(bytes_read)
#             if file_size == 0:
#                 f.close()
#                 break
def send_file(command, path, socket):

    is_exist = socket.recv(4)
    is_exist = int.from_bytes(is_exist, "big")

    if is_exist:
        return
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
    if os.path.exists(path):
        socket.send((1).to_bytes(4, "big"))
        return

    socket.send((0).to_bytes(4, "big"))

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
        while True:
            bytes_read = socket.recv(min(4096, file_size))
            file_size = file_size - len(bytes_read)
            if file_size == 0:
                f.close()
                break


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
    # socket.send((len(command.encode())).to_bytes(4, "big"))
    # socket.send(command.encode())
    send_file(command, path, socket)
    # size_bytes = socket.recv(4)
    # to_create = int.from_bytes(size_bytes, "big")
    # if to_create:
    #     send_file(command, path, socket)


def receive_modify(full_path, socket):
    socket.send((0).to_bytes(4, "big"))

    size_bytes = socket.recv(4)
    size_server = int.from_bytes(size_bytes, "big")
    server_file = b''

    try:
        while True:
            current_server_bytes = socket.recv(min(4096, size_server))
            #server_file.join(current_server_bytes)
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
