import json
import sys
import hashlib

from app import bencode

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
        with open(file, "rb") as f:
            bencoded_content = f.read()

            torrent: dict = bencode.decode(bencoded_content)
            info_part = torrent["info"]

            if isinstance(info_part, dict):
                hash = hashlib.sha1(bencode.encode(info_part)).hexdigest()

                # Stage: Calculate the hashes
                print("Tracker URL:", torrent["announce"].decode())
                print("Length:", torrent["info"]["length"])
                print("Info Hash:", hash)

                # Stage: Piece hashes
                print("Piece Length:", info_part["piece length"])
                print("Piece Hashes:")
                for i in range(0, len(info_part["pieces"]), 20):
                    print(info_part["pieces"][i : i + 20].hex())

    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
