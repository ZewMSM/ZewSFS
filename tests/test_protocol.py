import pytest

from sfs2x.core import UtfStringArray, Int, Text
from sfs2x.core.buffer import Buffer
from sfs2x.core.types.containers import SFSObject
from sfs2x.protocol import (
    Message,
    ControllerID,
    SysAction,
    encode,
    decode,
    Flag,
)


def make_payload(**fields):
    """Make simple SFSObject from key-value pairs."""
    return SFSObject({k: Text(v) for k, v in fields.items()})


@pytest.mark.parametrize(
    "controller,action,payload",
    [
        (ControllerID.SYSTEM, SysAction.LOGIN, make_payload(un="neo")),
        (ControllerID.EXTENSION, 0, make_payload(c="ping")),
    ],
)
def test_encode_decode_roundtrip(controller: int, action, payload):
    msg_out = Message(controller, action, payload)
    raw = encode(msg_out)
    msg_in = decode(Buffer(raw))
    assert msg_in == msg_out


def test_expected_short_bytes():
    msg = Message(
        ControllerID.SYSTEM,
        SysAction.PING_PONG,
        make_payload(txt="hello"),
    )

    expected_bytes = encode(msg)
    assert encode(msg) == expected_bytes
    assert decode(Buffer(expected_bytes)) == msg


def test_long_packet():
    big_string = "x" * 70000  # 70 000 > 65535
    msg = Message(
        ControllerID.SYSTEM,
        SysAction.HANDSHAKE,
        make_payload(blob=big_string),
    )
    raw = encode(msg, compress_threshold=None)

    first_flag = Flag(raw[0])
    assert first_flag & Flag.BINARY
    assert first_flag & Flag.BIG_SIZE

    decoded = decode(Buffer(raw))
    assert decoded.payload.get("blob") == big_string


def test_encrypted_and_compressed_long_packet():
    big_string = "x" * 70000
    msg = Message(
        ControllerID.SYSTEM,
        SysAction.HANDSHAKE,
        make_payload(blob=big_string),
    )
    raw = encode(msg, compress_threshold=0, encryption_key=b'1234567890123456')

    first_flag = Flag(raw[0])
    assert first_flag & Flag.BINARY
    assert first_flag & Flag.ENCRYPTED
    assert first_flag & Flag.COMPRESSED

    decoded = decode(Buffer(raw), encryption_key=b'1234567890123456')
    assert decoded.payload.get("blob") == big_string


def test_unpack_binary_packet():
    binary_message = b'\x80\x00T\x12\x00\x03\x00\x01c\x02\x01\x00\x01a\x03\x00\x0c\x00\x01p\x12\x00\x03\x00\x01c\x08\x00\x0ctest_command\x00\x01r\x04\xff\xff\xff\xff\x00\x01p\x12\x00\x02\x00\x03num\x04\xff\xff\xff\xff\x00\x07strings\x10\x00\x02\x00\x02hi\x00\x04mega'
    decoded = decode(binary_message)

    re_encoded = Message.extension("test_command", {
        "num": Int(-1),
        "strings": UtfStringArray(['hi', 'mega'])
    })

    assert decoded.controller == ControllerID.EXTENSION
    assert decoded.action == 12
    assert decoded == re_encoded
