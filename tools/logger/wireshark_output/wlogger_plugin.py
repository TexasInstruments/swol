import socket
import json

HOST = "127.0.0.1"
PORT = 51108
WS_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
BUF_TO_RESEND = None


def send_data(buf):
    global WS_SOCKET
    global BUF_TO_RESEND

    if not buf:
        return

    try:
        if BUF_TO_RESEND is not None:
            WS_SOCKET.sendto(json.dumps(BUF_TO_RESEND).encode(), (HOST, PORT))
            BUF_TO_RESEND = None

        WS_SOCKET.sendto(json.dumps(buf).encode(), (HOST, PORT))
    except Exception:
        BUF_TO_RESEND = buf
