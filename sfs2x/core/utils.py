from .buffer import Buffer

__all__ = [
    "write_small_string",
    "read_small_string",
    "write_big_string",
    "read_big_string",
]

def write_small_string(s: str) -> bytearray:
    encoded = s.encode("utf-8")
    return bytearray(len(encoded).to_bytes(2, 'big') + encoded)

def read_small_string(buffer: Buffer) -> str:
    ln = int.from_bytes(buffer.read(2), 'big')
    return bytes(buffer.read(ln)).decode("utf-8")

def write_big_string(s: str) -> bytearray:
    encoded = s.encode("utf-8")
    return bytearray(len(encoded).to_bytes(4, 'big') + encoded)

def read_big_string(buffer: Buffer) -> str:
    ln = int.from_bytes(buffer.read(4), 'big')
    return bytes(buffer.read(ln)).decode("utf-8")

