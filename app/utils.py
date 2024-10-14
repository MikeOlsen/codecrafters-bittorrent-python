import requests
import hashlib

from app import bencode


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


""


def calculate_piece_length(torrent, piece_index):
    piece_hashes = get_piece_hashes(torrent)
    if piece_index == len(piece_hashes) - 1:
        # Calculate remainig length of last piece
        return torrent["info"]["length"] - (
            torrent["info"]["piece length"] * piece_index
        )
    else:
        return torrent["info"]["piece length"]
