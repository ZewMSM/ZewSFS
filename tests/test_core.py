import pytest

from sfs2x.core import (
    Bool,
    BoolArray,
    Buffer,
    Byte,
    ByteArray,
    Double,
    DoubleArray,
    Float,
    FloatArray,
    Int,
    IntArray,
    Long,
    LongArray,
    SFSArray,
    SFSObject,
    Short,
    ShortArray,
    Text,
    UtfString,
    UtfStringArray,
    decode,
)
from sfs2x.core.exceptions import FieldError
from sfs2x.core.utils import read_small_string, write_small_string

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
        "number": Int(12),
        "string": UtfString("Hello, world!"),
        "double_array": DoubleArray([3.14, 3.14, 3.14]),
        "object": SFSObject({
            "number": Int(12),
            "array": SFSArray([
                SFSObject({"str_arr": UtfStringArray(["hi", "antony"])}),
                SFSObject({"test": Double(3.1333)})
            ])
        })
    },
    SFSArray: [
        SFSObject({"int": Int(12)}),
        Double(3.14),
        ByteArray([20, -10, 50]),
        Text("Hello, world!"),
        BoolArray([True, False, True]),
    ]
}

SAMPLE_PACKED_VALUES = {
    b"\x12\x00\x03\x00\x03num\x04\x00\x00\x00\x0c\x00\x03str\x08\x00\x05Hello\x00\x03obj\x12\x00\x01\x00\x05short\x03\xff\xec": SFSObject(
        {
            "num": Int(12),
            "str": UtfString("Hello"),
            "obj": SFSObject({
                "short": Short(-20)
            })
        }),
    b"\x11\x00\x04\x04\x00\x00\x00\r\x10\x00\x02\x00\x02hi\x00\x05world"
    b"\x12\x00\x01\x00\x05short\x03\xff\xec\x11\x00\x01\t\x00\x02\x00\x01": SFSArray([
        Int(13),
        UtfStringArray(["hi", "world"]),
        SFSObject({"short": Short(-20)}),
        SFSArray([
            BoolArray([False, True]),
        ])
    ])
}


def test_decode_unknown_type():
    unknown_packet = bytearray([30])
    with pytest.raises(ValueError):
        decode(Buffer(unknown_packet))


def test_prefixed_string_helpers():
    text = "Hello, world!"
    packed = write_small_string(text)
    unpacked = read_small_string(Buffer(packed))
    assert unpacked == text


# noinspection PyArgumentList
@pytest.mark.parametrize("cls,sample", SAMPLE_TYPES_VALUES.items())
def test_roundtrip_all_types(cls, sample):
    inst = cls(sample)

    raw = inst.to_bytes()
    back = decode(Buffer(raw))

    if cls == Float:
        assert abs(back.value - sample) < 1e-6
    elif cls == FloatArray:
        for _ in range(len(sample)):
            assert abs(back.value[_] - sample[_]) < 1e-6
    else:
        assert back.value == sample

    assert back.type_code == cls.type_code
    assert back.to_bytes() == raw


@pytest.mark.parametrize("packed,non_packed", SAMPLE_PACKED_VALUES.items())
def test_serialization_compatibility(packed: bytes, non_packed: SFSObject):
    new_packed = non_packed.to_bytes()
    assert packed == bytes(new_packed)

    repacked = decode(Buffer(packed))
    assert repacked == non_packed


def test_coding_styles_compatibility():
    imperative = SFSObject()
    imperative.put_int("number", 12)
    imperative.put_bool("bool", False)
    imperative.put_sfs_array("arr", SFSArray().add_short(12)
                             .add_int(1000).add_utf_string_array(["hi", "antony"]))

    sub_imperative = SFSObject()
    sub_imperative["num"] = Short(-20)
    sub_imperative["double_arr"] = DoubleArray([3.14, 3.14, 3.14])
    imperative.put("obj", sub_imperative)

    declarative = SFSObject({
        "number": Int(12),
        "bool": Bool(False),
        "arr": [
            Short(12),
            Int(1000),
            UtfStringArray(["hi", "antony"]),
        ],
        "obj": {
            "num": Short(-20),
            "double_arr": DoubleArray([3.14, 3.14, 3.14]),
        }
    })

    # noinspection PyTypeChecker
    arged = SFSObject(
        number=Int(12),
        bool=Bool(False),
        arr=[
            Short(12),
            Int(1000),
            UtfStringArray("hi", "antony"),
        ],
        obj=SFSObject(
            num=Short(-20),
            double_arr=DoubleArray(3.14, 3.14, 3.14),
        )
    )

    assert imperative == declarative == arged


def test_objects_concatenation():
    obj1 = SFSObject(
        number=Int(10) + 2,
        bool=Bool(False),
    )

    obj2 = SFSObject()
    obj2.put_utf_string('name', "hi")

    obj3 = SFSObject({
        "number": Int(12),
        "bool": Bool(False),
        'name': UtfString('hi')
    })

    assert obj1 + obj2 == obj3
    assert obj1 | obj2 == obj3
    assert obj1.update(name=UtfString('hi')) == obj3

    assert BoolArray(False, False) + BoolArray(True, True) == BoolArray([False, False, True, True])