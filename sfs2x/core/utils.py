import re

from .buffer import Buffer

__all__ = [
    "camel_to_snake",
    "read_big_string",
    "read_small_string",
    "write_big_string",
    "write_small_string"
]

_CAMEL_RE = re.compile(
    r"""
    (?<=[a-z0-9])(?=[A-Z])     # aB         ← rule 1
    |                          # ─── or ───
    (?<=[A-Z])(?=[A-Z][a-z])   # XMLhttp   ← rule 2
    """,
    re.VERBOSE,
)

def write_small_string(s: str) -> bytearray:
    encoded = s.encode("utf-8")
    return bytearray(len(encoded).to_bytes(2, "big") + encoded)

def read_small_string(buffer: Buffer) -> str:
    ln = int.from_bytes(buffer.read(2), "big")
    return bytes(buffer.read(ln)).decode("utf-8")

def write_big_string(s: str) -> bytearray:
    encoded = s.encode("utf-8")
    return bytearray(len(encoded).to_bytes(4, "big") + encoded)

def read_big_string(buffer: Buffer) -> str:
    ln = int.from_bytes(buffer.read(4), "big")
    return bytes(buffer.read(ln)).decode("utf-8")

def camel_to_snake(name: str) -> str:
    """Bool → bool, IntArray → int_array, SFSObject → sfs_object."""
    return _CAMEL_RE.sub("_", name).lower()
