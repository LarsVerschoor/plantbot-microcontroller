import usocket as socket
import ubinascii
import urandom
import uhashlib
import utime
import ujson
import ssl

print(dir(ssl))

HOST = '192.168.1.152'
PORT = 80

GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

# Create 128 random bits. The server will hash this key with the GUID which is also locally stored at the server
def generate_sec_websocket_key():
    random_bytes = bytearray([urandom.getrandbits(8) for _ in range(16)])
    key = ubinascii.b2a_base64(random_bytes).decode().strip()
    return key

# Hash the GUID with the 128 bit key. To compare with the hash ("Sec-WebSocket-Accept" handshake response header) returned from the server
def compute_sec_websocket_accept(sec_websocket_key):
    accept_value = uhashlib.sha1(sec_websocket_key.encode() + GUID.encode()).digest()
    return ubinascii.b2a_base64(accept_value).decode().strip()

def send_handshake(sock):
    sec_websocket_key = generate_sec_websocket_key()
    sec_websocket_accept = compute_sec_websocket_accept(sec_websocket_key)
    headers = (
        "GET /iot HTTP/1.1\r\n"
        "Host: {}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: {}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).format(HOST, sec_websocket_key)
    sock.send(headers.encode())

    response = sock.recv(1024).decode()
    print("Handshake response:", response)

    if "Sec-WebSocket-Accept: " in response:
        accept_key = response.split("Sec-WebSocket-Accept: ")[1].split("\r\n")[0]
        if accept_key == sec_websocket_accept:
            print("Handshake verified successfully.")
        else:
            print("Handshake verification failed.")
    else:
        print("No Sec-WebSocket-Accept in response. Handshake failed.")

def mask_data(data):
    mask = bytearray([urandom.getrandbits(8) for _ in range(4)])
    masked_data = bytearray()
    for i in range(len(data)):
        masked_data.append(data[i] ^ mask[i % 4])
    return mask + masked_data

def send_message(sock, message):
    frame = bytearray()
    frame.append(0x81)
    payload_length = len(message)

    if payload_length <= 125:
        frame.append(0x80 | payload_length)
    else:
        raise ValueError("Payload too large for this example")

    frame.extend(mask_data(message.encode()))
    sock.send(frame)

def receive_message(sock):
    sock.setblocking(False)
    try:
        header = sock.recv(2)
        if not header:
            return None
        payload_len = header[1] & 0x7F
        payload = sock.recv(payload_len)
        return payload.decode()
    except Exception:
        return None

def connect_websocket():
    addr_info = socket.getaddrinfo(HOST, PORT)[0]
    addr = addr_info[-1]

    s = socket.socket()
    s.connect(addr)
    
    # for secure https ssl
    # s = ssl.wrap_socket(s, server_hostname=HOST)
    
    send_handshake(s)

    try:
        send_message(s, ujson.dumps({
            "event": "register",
            "payload": "larsverschoor2@gmail.com"
        }))
        while True:
            send_message(s, ujson.dumps({"event": "heartbeat", "payload": ""}))

            response = receive_message(s)
            if response:
                print("Received from server:", response)

            utime.sleep(1)

    finally:
        s.close()
