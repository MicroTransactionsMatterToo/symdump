import io
import struct


def read_pascal_string(input: io.BytesIO) -> bytes:
    str_len = int.from_bytes(input.read(1), 'little')
    value = struct.unpack(f"<{str_len}s", input.read(str_len))[0]
    return value