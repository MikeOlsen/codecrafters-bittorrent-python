import json
import math
import struct
import sys
import hashlib
import requests

from app import bencode
from app.bittorrent import (
    BITFIELD,
    INTERESTED,
    REQUEST,
    UNCHOKE,
    Bittorrent,
)

BLOCK_LENGTH = 16 * 1024

# import requests - available if you need it!


# Examples:
#
# - decode_bencode(b"5:hello") -> b"hello"
# - decode_bencode(b"10:hello12345") -> b"hello12345"


def bytes_to_str(data):
    if isinstance(data, bytes):
        return data.decode()

    raise TypeError(f"Type not serializable: {type(data)}")


def parse_torrent(file: str) -> dict:
    with open(file, "rb") as f:
        bencoded_content = f.read()
        torrent: dict = bencode.decode(bencoded_content)
        torrent["info_hash"] = hashlib.sha1(bencode.encode(torrent["info"])).digest()
        return torrent


def parse_peers(tracker):
    peers = tracker["peers"]
    result = []
    for i in range(0, len(peers), 6):
        ip = ".".join(str(byte) for byte in peers[i : i + 4])
        port = int.from_bytes(peers[i + 4 : i + 6])
        result.append((ip, port))
    return result


def get_piece_hashes(torrent):
    hashes = []
    for i in range(0, len(torrent["info"]["pieces"]), 20):
        hashes.append(torrent["info"]["pieces"][i : i + 20].hex())
    return hashes


def get_tracker_info(torrent):
    tracker_url = torrent["announce"].decode()

    params = {
        "info_hash": torrent["info_hash"],
        "peer_id": "codecrafter-12345678",
        "port": 6881,
        "uploaded": 0,
        "downloaded": 0,
        "left": torrent["info"]["length"],
        "compact": 1,
    }
    response = requests.get(tracker_url, params)
    return bencode.decode(response.content)


def calculate_piece_length(torrent, piece_index):
    piece_hashes = get_piece_hashes(torrent)
    if piece_index == len(piece_hashes) - 1:
        # Calculate remainig length of last piece
        return torrent["info"]["length"] - (
            torrent["info"]["piece length"] * piece_index
        )
    else:
        return torrent["info"]["piece length"]


def main():
    command = sys.argv[1]

    if command == "decode":
        bencoded_value = sys.argv[2].encode()

        # json.dumps() can't handle bytes, but bencoded "strings" need to be
        # bytestrings since they might contain non utf-8 characters.
        #
        # Let's convert them to strings for printing to the console.

        print(json.dumps(bencode.decode(bencoded_value), default=bytes_to_str))

    elif command == "info":
        file = sys.argv[2]
        torrent = parse_torrent(file)

        # Stage: Calculate the hashes
        print("Tracker URL:", torrent["announce"].decode())
        print("Length:", torrent["info"]["length"])
        print("Info Hash:", torrent["info_hash"].hex())

        # Stage: Piece hashes
        print("Piece Length:", torrent["info"]["piece length"])
        print("Piece Hashes:")
        for i in range(0, len(torrent["info"]["pieces"]), 20):
            print(torrent["info"]["pieces"][i : i + 20].hex())

    elif command == "peers":
        file = sys.argv[2]

        torrent = parse_torrent(file)
        tracker = get_tracker_info(torrent)

        peers = parse_peers(tracker)
        for ip, port in peers:
            print(f"{ip}:{port}")

    elif command == "handshake":
        file = sys.argv[2]
        ip, port = sys.argv[3].split(":", 1)

        torrent = parse_torrent(file)

        bittorrent = Bittorrent()
        bittorrent.connect(ip, int(port))
        peer_id = bittorrent.handshake(torrent)
        print("Peer ID:", peer_id)

    elif command == "download_piece":
        target_file = sys.argv[3]
        torrent_file = sys.argv[4]
        piece_index = int(sys.argv[5])

        # Gather info
        torrent = parse_torrent(torrent_file)
        tracker = get_tracker_info(torrent)
        peers = parse_peers(tracker)

        # Establish connection
        bittorrent = Bittorrent()
        bittorrent.connect(*peers[0])
        bittorrent.handshake(torrent)

        # Request piece from peer
        bittorrent.wait_for_reply(BITFIELD)
        bittorrent.send(INTERESTED)
        bittorrent.wait_for_reply(UNCHOKE)

        piece_length = calculate_piece_length(torrent, piece_index)
        block_count = piece_length // BLOCK_LENGTH
        last_block_length = piece_length % BLOCK_LENGTH

        data = b""
        for index in range(block_count):
            data += bittorrent.download_block(
                index=piece_index,
                begin=index * BLOCK_LENGTH,
                length=BLOCK_LENGTH,
            )
        if last_block_length > 0:
            data += bittorrent.download_block(
                index=piece_index,
                begin=block_count * BLOCK_LENGTH,
                length=last_block_length,
            )

        with open(target_file, "wb") as f:
            f.write(data)

    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
