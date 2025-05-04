from .buffer import Buffer

__all__ = [
    "write_prefixed_string",
    "read_prefixed_string"
]

def write_prefixed_string(s: str) -> bytearray:
    encoded = s.encode("utf-8")
    return bytearray(len(encoded).to_bytes(2, 'big') + encoded)

def read_prefixed_string(buffer: Buffer) -> str:
    ln = int.from_bytes(buffer.read(2), 'big')
    return bytes(buffer.read(ln)).decode("utf-8")