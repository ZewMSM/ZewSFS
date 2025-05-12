from typing import overload

from sfs2x.core import Buffer
from sfs2x.core import decode as core_decode
from sfs2x.core.types.containers import SFSObject
from sfs2x.protocol import Flag, Message, ProtocolError, UnsupportedFlagError

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

    if flags & Flag.ENCRYPTED or flags & Flag.COMPRESSED:
        msg = "Encryption / Compression flags don't supported yet."
        raise UnsupportedFlagError(msg)

    length = int.from_bytes(buf.read(4 if flags & Flag.BIG_SIZE else 2), byteorder="big")

    if not flags & Flag.BINARY:
        msg = "Currently, only binary packets are supported."
        raise ProtocolError(msg)

    return length, flags


def encode(msg: Message) -> bytearray:
    """Encode message to bytearray, TCP-Ready."""
    payload = msg.to_sfs_object().to_bytes()
    return _assemble_header(len(payload)) + payload


@overload
def decode(buf: Buffer) -> Message: ...
@overload
def decode(raw: (bytes, bytearray, memoryview)) -> Message: ...


# noinspection PyTypeChecker
def decode(data):
    """Decode buffer to message."""
    buf = data if isinstance(data, Buffer) else Buffer(data)

    length, flags = _parse_header(buf)
    payload_bytes = buf.read(length)
    root: SFSObject = core_decode(Buffer(payload_bytes))

    controller = root.get("c", 0)
    action = root.get("a", 0)
    params = root.get("p", SFSObject())

    return Message(controller, action, params)
