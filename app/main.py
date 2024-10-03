import json
import sys
from typing import Any

# import bencodepy - available if you need it!
# import requests - available if you need it!


# Examples:
#
# - decode_bencode(b"5:hello") -> b"hello"
# - decode_bencode(b"10:hello12345") -> b"hello12345"
def decode_bencode(bencoded_value):
    return _decode_bencoded_segment(bencoded_value)[0]


def _decode_bencoded_segment(bencoded_value) -> tuple[Any, bytes]:
    prefix = chr(bencoded_value[0])
    if prefix.isdigit():
        length_b, content = bencoded_value.split(b":", 1)
        length = int(length_b)
        return str(content[:length], "utf-8"), content[length:]
    elif prefix == "i":
        integer_b, rest = bencoded_value[1:].split(b"e", 1)
        return int(integer_b), rest
    elif prefix == "l":
        result = []
        data = bencoded_value[1:]
        while chr(data[0]) != "e":
            value, data = _decode_bencoded_segment(data)
            result.append(value)
        return result, data[1:]
    elif prefix == "d":
        result = {}
        data = bencoded_value[1:]
        while chr(data[0]) != "e":
            key, data = _decode_bencoded_segment(data)
            value, data = _decode_bencoded_segment(data)
            result[key] = value
        return result, data

    else:
        raise NotImplementedError("Only strings and digits are supported at the moment")


def main():
    command = sys.argv[1]

    if command == "decode":
        bencoded_value = sys.argv[2].encode()

        # json.dumps() can't handle bytes, but bencoded "strings" need to be
        # bytestrings since they might contain non utf-8 characters.
        #
        # Let's convert them to strings for printing to the console.
        def bytes_to_str(data):
            if isinstance(data, bytes):
                return data.decode()

            raise TypeError(f"Type not serializable: {type(data)}")

        print(json.dumps(decode_bencode(bencoded_value), default=bytes_to_str))
    else:
        raise NotImplementedError(f"Unknown command {command}")


if __name__ == "__main__":
    main()
