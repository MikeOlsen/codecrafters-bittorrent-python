import asyncio
import json
import sys

from app import bencode
from app.bittorrent import download_all_pieces, download_piece_from_peer, handshake
from app.utils import get_piece_hashes, get_tracker_info, parse_peers, parse_torrent
import logging


def bytes_to_str(data):
    if isinstance(data, bytes):
        return data.decode()

    raise TypeError(f"Type not serializable: {type(data)}")


def main():
    command = sys.argv[1]

    if command == "decode":
        bencoded_value = sys.argv[2].encode()

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

        peer_id = asyncio.run(handshake(ip, int(port), torrent))
        print("Peer ID:", peer_id)

    elif command == "download_piece":
        target_file = sys.argv[3]
        torrent_file = sys.argv[4]
        piece_index = int(sys.argv[5])

        # Gather info
        torrent = parse_torrent(torrent_file)
        tracker = get_tracker_info(torrent)
        peers = parse_peers(tracker)

        data = asyncio.run(download_piece_from_peer(peers[1], piece_index, torrent))

        print(f"Piece {piece_index} successfully downloaded")
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

        pieces = asyncio.run(download_all_pieces(peers, torrent))

        with open(target_file, "wb") as f:
            for piece in pieces:
                f.write(piece)

    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
