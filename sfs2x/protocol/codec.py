import zlib
from typing import overload

from sfs2x.core import Buffer, SFSObject
from sfs2x.core import decode as core_decode
from sfs2x.protocol import AESCipher, Flag, Message, ProtocolError, UnsupportedFlagError

_SHORT_MAX = 0xFFFF


def _assemble_header(payload_len: int) -> bytearray:
    """Assemble first byte and packet length."""
    flags = Flag.BINARY
    hdr = bytearray()

    if payload_len > _SHORT_MAX:
        flags |= Flag.BIG_SIZE
        hdr.append(flags)
        hdr.extend(payload_len.to_bytes(4, byteorder="big"))
    else:
        hdr.append(flags)
        hdr.extend(payload_len.to_bytes(2, byteorder="big"))

    return hdr


def _parse_header(buf: Buffer) -> tuple[int, Flag]:
    """Parse first bytes and return packet length and flags."""
    flags = Flag(buf.read(1)[0])

    if flags & Flag.BLUEBOX:
        msg = "BLUEBOX don't supported yet."
        raise UnsupportedFlagError(msg)

    length = int.from_bytes(buf.read(4 if flags & Flag.BIG_SIZE else 2), byteorder="big")

    if not flags & Flag.BINARY:
        msg = "Currently, only binary packets are supported."
        raise ProtocolError(msg)

    return length, flags


def encode(msg: Message, compress_threshold: int | None = 1024, encryption_key: bytes | None = None) -> bytearray:
    """Encode message to bytearray, TCP-Ready."""
    flags = Flag.BINARY
    payload: bytes = msg.to_sfs_object().to_bytes()

    if compress_threshold is not None and len(payload) > compress_threshold:
        payload = zlib.compress(payload)
        flags |= Flag.COMPRESSED

    if encryption_key is not None:
        if AESCipher is None:
            msg = "Library pycryptodome is not installed. Install it before using encryption (pip install pycryptodome)."
            raise ImportError(msg)
        cipher = AESCipher(encryption_key)
        payload = cipher.encrypt(payload)
        flags |= Flag.ENCRYPTED

    header = _assemble_header(len(payload))
    header[0] |= flags
    return header + payload


@overload
def decode(buf: Buffer, *, encryption_key: bytes | None = None) -> Message: ...


@overload
def decode(raw: bytes | bytearray | memoryview, *, encryption_key: bytes | None = None) -> Message: ...

# noinspection PyTypeChecker
def decode(data, *, encryption_key: bytes | None = None) -> Message:
    """Decode buffer to message."""
    buf = data if isinstance(data, Buffer) else Buffer(data)

    length, flags = _parse_header(buf)
    payload_bytes = buf.read(length)

    if flags & Flag.ENCRYPTED:
        if encryption_key is None:
            msg = "Can't decrypt message without encryption key."
            raise ProtocolError(msg)
        if AESCipher is None:
            msg = "Library pycryptodome is not installed. Install it before using encryption (pip install pycryptodome)."
            raise ImportError(msg)
        cipher = AESCipher(encryption_key)
        try:
            payload_bytes = cipher.decrypt(payload_bytes)
        except ValueError as e:
            msg = "Encryption error occurred."
            raise ProtocolError(msg) from e

    if flags & Flag.COMPRESSED:
        payload_bytes = zlib.decompress(payload_bytes)

    root: SFSObject = core_decode(Buffer(payload_bytes))

    controller = root.get("c", 0)
    action = root.get("a", 0)
    params = root.get("p", SFSObject())

    return Message(controller, action, params)
