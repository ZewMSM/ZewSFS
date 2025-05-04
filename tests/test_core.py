import pytest

from sfs2x.core import Bool, decode, Buffer, TypeCode
from sfs2x.core.utils import read_prefixed_string, write_prefixed_string

SAMPLE_VALUES = {
    Bool: True
}

def test_decode_unknown_type():
    unknown_packet = write_prefixed_string("name") + bytearray([30])
    with pytest.raises(ValueError):
        decode(Buffer(unknown_packet))

def test_prefixed_string_helpers():
    text = "Hello, world!"
    packed = write_prefixed_string(text)
    unpacked = read_prefixed_string(Buffer(packed))
    assert unpacked == text

@pytest.mark.parametrize("cls,sample", SAMPLE_VALUES.items())
def test_roundtrip_all_types(cls, sample):
    inst = cls("field", sample)

    raw = inst.to_bytes()
    back = decode(Buffer(raw))

    assert back.name == "field"
    assert back.value == sample
    assert back.type_code == cls.type_code
    assert back.to_bytes() == raw