import json
import sys

from app import bencode
from app.bittorrent import Bittorrent
from app.utils import get_piece_hashes, get_tracker_info, parse_peers, parse_torrent


# import requests - available if you need it!


# Examples:
#
# - decode_bencode(b"5:hello") -> b"hello"
# - decode_bencode(b"10:hello12345") -> b"hello12345"


def bytes_to_str(data):
    if isinstance(data, bytes):
        return data.decode()

    raise TypeError(f"Type not serializable: {type(data)}")


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
        bittorrent.init_peer_communication()

        # Download piece
        data = bittorrent.download_piece(torrent, piece_index)

        print(f"Piece {piece_index} successfully donloaded")
        # Write piece to file
        with open(target_file, "wb") as f:
            f.write(data)

    elif command == "download":
        target_file = sys.argv[3]
        torrent_file = sys.argv[4]

        # Gather info
        torrent = parse_torrent(torrent_file)
        tracker = get_tracker_info(torrent)
        peers = parse_peers(tracker)

        # Establish connection
        bittorrent = Bittorrent()
        bittorrent.connect(*peers[2])
        bittorrent.handshake(torrent)
        bittorrent.init_peer_communication()

        piece_hashes = get_piece_hashes(torrent)

        print("Pieces to download:", len(piece_hashes))
        pieces = []
        for piece_index in range(0, len(piece_hashes)):
            print("Downloading piece:", piece_index)
            pieces.append(bittorrent.download_piece(torrent, piece_index))

        # Write to file
        with open(target_file, "wb") as f:
            for piece in pieces:
                f.write(piece)

    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
