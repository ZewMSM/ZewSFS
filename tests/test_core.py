import pytest

from sfs2x.core import (decode, Buffer, Bool, Byte, Short, Int, Long, Float, Double, UtfString,
                        Text, BoolArray, ByteArray, ShortArray, IntArray, LongArray, FloatArray,
                        DoubleArray, UtfStringArray, SFSObject)
from sfs2x.core.utils import read_prefixed_string, write_prefixed_string

SAMPLE_TYPES_VALUES = {
    Bool: False,
    Byte: 100,
    Short: 16200,
    Int: -100,
    Long: 79038144099211,
    Float: 3.14,
    Double: -92.1414145,
    UtfString: "Hello, world!",
    BoolArray: [True, False, True],
    ByteArray: [20, -10, 50],
    ShortArray: [100, -1000, 5000],
    IntArray: [10000, -100000, 500000],
    LongArray: [10000000, -100000000, 500000000],
    FloatArray: [3.14, 3.14, 3.14],
    DoubleArray: [-92.14, -92.14, -92.14],
    UtfStringArray: ["Hello, world!", "i'm - Zewsic", "Nice to meet you!"],
    Text: "Lorem Ipsum " * 10000,
    SFSObject: {
        "number": Int("", 12),
        "string": UtfString("", "Hello, world!"),
        "double_array": DoubleArray("", [3.14, 3.14, 3.14]),
        "object": SFSObject("", {
            "number": Int("", 12),
        })
    }
}


SAMPLE_PACKED_VALUES = {
    b'\x12\x00\x03\x00\x03num\x04\x00\x00\x00\x0c\x00\x03str\x08\x00\x05Hello\x00\x03obj\x12\x00\x01\x00\x05short\x03\xff\xec': SFSObject('', {
        'num': Int("num", 12),
        'str': UtfString('str', 'Hello'),
        'obj': SFSObject('obj', {
            'short': Short('short', -20)
        })
    })
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

@pytest.mark.parametrize("cls,sample", SAMPLE_TYPES_VALUES.items())
def test_roundtrip_all_types(cls, sample):
    inst = cls("field", sample)

    raw = inst.to_bytes()
    back = decode(Buffer(raw))

    if cls == Float:
        assert abs(back.value - sample) < 1e-6
    elif cls == FloatArray:
        for _ in range(len(sample)):
            assert abs(back.value[_] - sample[_]) < 1e-6
    else:
        assert back.value == sample

    assert back.name == "field"
    assert back.type_code == cls.type_code
    assert back.to_bytes() == raw

@pytest.mark.parametrize("packed,non_packed", SAMPLE_PACKED_VALUES.items())
def test_roundtrip_all_types(packed: bytes, non_packed: SFSObject):
    new_packed = non_packed.to_bytes()
    assert packed == new_packed

    repacked = decode(Buffer(packed), skip_name=True)
    assert repacked == non_packed


