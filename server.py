import socket
import sys
import string
import random
import os
import time
from utilis import *

computer_number = 1
empty_id = '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'


def random_string():
    character_set = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "BAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    return ''.join(random.choice(character_set) for i in range(128))


def registered_new_id(client_socket, dict):
    global computer_number
    id = random_string()
    try:
        os.makedirs(id)
        dict_id = {}
        dict_id[computer_number] = list()
        dict[id] = dict_id
        client_socket.send(id.encode("utf-8") + computer_number.to_bytes(4, "big"))
        computer_number += 1
    except:
        print("cant open folder in register_new_user!")

    absolute_path = os.path.dirname(id)
    pull(client_socket, absolute_path)


def register_new_cp(id, client_socket, dict):
    global computer_number
    dict[id][computer_number] = list()
    client_socket.send(id.encode("utf-8") + computer_number.to_bytes(4, "big"))
    computer_number += 1
    absolute_path = os.path.dirname(id)
    push(client_socket, absolute_path)


def update_dict(id, cp_num, list, dict):
    client_dict = dict[id]
    for cp in client_dict:
        if cp != cp_num:
            client_dict[cp].extend(list)


def receive_update_from_client(id, cp_num, dict, client_socket):
    list_size = int.from_bytes(client_socket.recv(4), "big")
    if list_size == 0:
        return
    byte_list = client_socket.recv(list_size)
    string_list = [x.decode('utf-8') for x in byte_list]
    update_dict(id, cp_num, string_list, dict)
    absolute_path = os.path.dirname(id)
    receive_update(client_socket, absolute_path)


if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', 12345))
    server.listen(5)
    dict = {}
    while True:
        client_socket, client_address = server.accept()

        data = client_socket.recv(132)
        id = data[:128].decode()
        cp_num = int.from_bytes(data[128:], "big")

        if id == empty_id:
            registered_new_id(client_socket, dict)
        if cp_num == 0:
            register_new_cp(id, client_socket, dict)
        else:
            absolute_path = os.path.dirname(id)
            send_update(dict[id][cp_num], client_socket, absolute_path)
            receive_update_from_client(id, cp_num, dict, client_socket)

        client_socket.close()
