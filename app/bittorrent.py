import os
import socket

PROTOCOL_HEADER = b"\x13BitTorrent protocol"
RESERVED_BYTES = b"\x00" * 8
PEER_ID = os.urandom(20)

HANDSHAKE_LENGTH = 68
PEER_ID_INDEX = 48


def handshake(ip, port, torrent):
    handshake = PROTOCOL_HEADER + RESERVED_BYTES + torrent["info_hash"] + PEER_ID

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, int(port)))
        s.send(handshake)
        return s.recv(HANDSHAKE_LENGTH)[PEER_ID_INDEX:].hex()
