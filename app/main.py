import json
import os
import socket
import sys
import hashlib
import requests

from app import bencode, bittorrent

# import requests - available if you need it!


# Examples:
#
# - decode_bencode(b"5:hello") -> b"hello"
# - decode_bencode(b"10:hello12345") -> b"hello12345"


def bytes_to_str(data):
    if isinstance(data, bytes):
        return data.decode()

    raise TypeError(f"Type not serializable: {type(data)}")


def parse_torrent(bencoded_content: bytes) -> dict:
    torrent: dict = bencode.decode(bencoded_content)
    torrent["info_hash"] = hashlib.sha1(bencode.encode(torrent["info"])).digest()
    return torrent


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
        with open(file, "rb") as f:

            torrent = parse_torrent(f.read())

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
        with open(file, "rb") as f:
            torrent = parse_torrent(f.read())

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
            response_b = requests.get(tracker_url, params)
            response = bencode.decode(response_b.content)

            peers = response["peers"]
            for i in range(0, len(peers), 6):
                ip = ".".join(str(byte) for byte in peers[i : i + 4])
                port = int.from_bytes(peers[i + 4 : i + 6])
                print(f"{ip}:{port}")

    elif command == "handshake":
        file = sys.argv[2]
        ip, port = sys.argv[3].split(":", 1)

        with open(file, "rb") as f:
            torrent = parse_torrent(f.read())
            peer_id = bittorrent.handshake(ip, int(port), torrent)
            print("Peer ID:", peer_id)

    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
