from typing import Any


def encode(input: Any) -> bytes:
    if isinstance(input, int):
        return f"i{input}e".encode()

    if isinstance(input, str):
        return f"{len(input.encode())}:{input}".encode()

    if isinstance(input, bytes):
        return f"{len(input)}:".encode() + input

    if isinstance(input, list):
        return b"l" + b"".join(map(encode, input)) + b"e"

    if isinstance(input, dict):
        encoded_items = b"".join(encode(k) + encode(v) for k, v in input.items())
        return b"d" + encoded_items + b"e"

    else:
        raise NotImplementedError(f"{type(input)} is not implemented")


def decode(bencoded_value):
    return _decode(bencoded_value)[0]


def _decode(bencoded_value) -> tuple[Any, bytes]:
    prefix = chr(bencoded_value[0])
    if prefix.isdigit():
        length_b, content = bencoded_value.split(b":", 1)
        length = int(length_b)
        return content[:length], content[length:]
    elif prefix == "i":
        integer_b, rest = bencoded_value[1:].split(b"e", 1)
        return int(integer_b), rest
    elif prefix == "l":
        result = []
        data = bencoded_value[1:]
        while chr(data[0]) != "e":
            value, data = _decode(data)
            result.append(value)
        return result, data[1:]
    elif prefix == "d":
        result = {}
        data = bencoded_value[1:]
        while chr(data[0]) != "e":
            key, data = _decode(data)
            value, data = _decode(data)
            result[key.decode()] = value
        return result, data

    else:
        raise NotImplementedError("Only strings and digits are supported at the moment")
