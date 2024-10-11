import os
import socket
import struct

PROTOCOL_HEADER = b"\x13BitTorrent protocol"
RESERVED_BYTES = b"\x00" * 8
PEER_ID = os.urandom(20)

HANDSHAKE_LENGTH = 68

PEER_ID_INDEX = 48
MESSAGE_ID_INDEX = 4

UNCHOKE = 1
INTERESTED = 2
BITFIELD = 5
REQUEST = 6
PIECE = 7


class Bittorrent:

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host: str, port: int):
        self.sock.connect((host, port))

    def handshake(self, torrent):
        handshake = PROTOCOL_HEADER + RESERVED_BYTES + torrent["info_hash"] + PEER_ID

        self.sock.send(handshake)
        response = self.sock.recv(HANDSHAKE_LENGTH)[PEER_ID_INDEX:]

        return response.hex()

    def send(self, message_id: int, payload=b""):
        length = len(payload) + 1
        message = struct.pack(">IB", length, message_id) + payload
        self.sock.send(message)

    def receive(self, length):
        chunks = []
        bytes_recd = 0
        while bytes_recd < length:
            chunk = self.sock.recv(min(length - bytes_recd, 2048))
            if not chunk:
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd += len(chunk)
        return b"".join(chunks)

    def receive_message(self) -> tuple[int, bytes]:
        header = self.receive(5)
        length, message_id = struct.unpack(">IB", header)
        payload_length = length - 1

        payload = self.receive(payload_length) if payload_length > 0 else b""
        return message_id, payload

    def wait_for_reply(self, desired_message_id: int) -> bytes:
        message_id, message = self.receive_message()
        while message_id != desired_message_id:
            message_id, message = self.receive_message()
        return message

    def download_block(self, index, begin, length):
        self.send(REQUEST, struct.pack(">III", index, begin, length))
        return self.wait_for_reply(PIECE)[8:]
