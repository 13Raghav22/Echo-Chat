import socket
import threading
import json
import time
import base64
import os

HOST = "127.0.0.1"
PORT = 12345

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = {}  # socket -> username
usernames = {}  # username -> socket

def broadcast(data, exclude=None):
    disconnected = []
    for client_socket in list(clients.keys()):
        if client_socket != exclude:
            try:
                send_packet(client_socket, data)
            except:
                disconnected.append(client_socket)
    for c in disconnected:
        remove_client(c)

def send_packet(client_socket, data):
    """Send length-prefixed packet"""
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        data = data.encode("utf-8")
    length = len(data)
    client_socket.sendall(length.to_bytes(4, "big") + data)

def recv_packet(client_socket):
    """Receive length-prefixed packet"""
    raw_len = recv_exact(client_socket, 4)
    if not raw_len:
        return None
    length = int.from_bytes(raw_len, "big")
    return recv_exact(client_socket, length)

def recv_exact(client_socket, n):
    """Receive exactly n bytes"""
    data = b""
    while len(data) < n:
        chunk = client_socket.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

def remove_client(client_socket):
    username = clients.pop(client_socket, None)
    if username:
        usernames.pop(username, None)
        broadcast_user_list()
        broadcast({
            "type": "system",
            "text": f"🔴 {username} left the chat",
            "timestamp": time.strftime("%H:%M")
        })
    try:
        client_socket.close()
    except:
        pass

def broadcast_user_list():
    users = list(clients.values())
    broadcast({
        "type": "user_list",
        "users": users
    })

def handle(client_socket):
    try:
        # First packet = join with username
        data = recv_packet(client_socket)
        if not data:
            return
        msg = json.loads(data.decode("utf-8"))
        if msg.get("type") != "join":
            return

        username = msg["username"].strip()
        if not username:
            username = "Anonymous"

        # Handle duplicate names
        original = username
        count = 1
        while username in usernames:
            username = f"{original}_{count}"
            count += 1

        clients[client_socket] = username
        usernames[username] = client_socket

        # Send welcome
        send_packet(client_socket, json.dumps({
            "type": "welcome",
            "username": username,
            "timestamp": time.strftime("%H:%M")
        }).encode())

        # Broadcast join
        broadcast({
            "type": "system",
            "text": f"🟢 {username} joined the chat",
            "timestamp": time.strftime("%H:%M")
        }, exclude=client_socket)

        broadcast_user_list()

        # Main loop
        while True:
            data = recv_packet(client_socket)
            if not data:
                break

            try:
                msg = json.loads(data.decode("utf-8"))
            except:
                break

            msg_type = msg.get("type")

            if msg_type == "message":
                msg["username"] = username
                msg["timestamp"] = time.strftime("%H:%M")
                broadcast(msg, exclude=client_socket)

            elif msg_type == "typing":
                broadcast({
                    "type": "typing",
                    "username": username,
                    "is_typing": msg.get("is_typing", False)
                }, exclude=client_socket)

            elif msg_type in ("image", "file"):
                msg["username"] = username
                msg["timestamp"] = time.strftime("%H:%M")
                broadcast(msg, exclude=client_socket)

    except Exception as e:
        pass
    finally:
        remove_client(client_socket)

def receive():
    print(f"✅ Server running on {HOST}:{PORT}")
    print("Waiting for connections...\n")
    while True:
        try:
            client_socket, address = server.accept()
            print(f"[+] Connected: {address}")
            thread = threading.Thread(target=handle, args=(client_socket,), daemon=True)
            thread.start()
        except Exception as e:
            print(f"Error accepting: {e}")

receive()
