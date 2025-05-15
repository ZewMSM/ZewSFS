import struct
from dataclasses import dataclass
from typing import ClassVar

from sfs2x.core.buffer import Buffer
from sfs2x.core.field import Field
from sfs2x.core.registry import register
from sfs2x.core.type_codes import TypeCode
from sfs2x.core.utils import read_small_string, write_small_string


class _NumericArrayMixin(Field[list[int]]):
    _elem_size: ClassVar[int]
    type_code: ClassVar[int]

    def __init__(self, *args: tuple[list[bool]] | list[bool]) -> None:
        """Initialize a _NumericArrayMixin."""
        if len(args) == 0:
            self.value = []
        elif type(args[0]) is int:
            self.value = list(args)
        else:
            self.value = args[0]

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += v.to_bytes(self._elem_size, "big", signed=True)
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "_NumericArrayMixin":
        length = int.from_bytes(buf.read(2), "big")
        arr = [
            int.from_bytes(buf.read(cls._elem_size), "big", signed=True)
            for _ in range(length)
        ]
        return cls(arr)


@register
@dataclass(slots=True)
class BoolArray(Field[list[bool]]):
    """Array with 1-bit numbers (or booleans)."""

    type_code = TypeCode.BOOL_ARRAY

    def __init__(self, *args: tuple[list[bool]] | list[bool]) -> None:
        """Initialize a BoolArray."""
        if len(args) == 0:
            self.value = []
        elif type(args[0]) is bool:
            self.value = list(args)
        else:
            self.value = args[0]

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload.append(1 if v else 0)
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "BoolArray":
        length = int.from_bytes(buf.read(2), "big")
        arr = [bool(int.from_bytes(buf.read(1), "big")) for _ in range(length)]
        return cls(arr)


@register
@dataclass(slots=True)
class ByteArray(_NumericArrayMixin):
    """Array with 8-bit numbers."""

    _elem_size = 1
    type_code = TypeCode.BYTE_ARRAY


@register
@dataclass(slots=True)
class ShortArray(_NumericArrayMixin):
    """Array with 16-bit numbers."""

    _elem_size = 2
    type_code = TypeCode.SHORT_ARRAY


@register
@dataclass(slots=True)
class IntArray(_NumericArrayMixin):
    """Array with 32-bit numbers."""

    _elem_size = 4
    type_code = TypeCode.INT_ARRAY


@register
@dataclass(slots=True)
class LongArray(_NumericArrayMixin):
    """Array with 64-bit numbers."""

    _elem_size = 8
    type_code = TypeCode.LONG_ARRAY


@register
@dataclass(slots=True)
class FloatArray(Field[list[float]]):
    """Array with floats with simple precision."""

    type_code = TypeCode.FLOAT_ARRAY

    def __init__(self, *args: tuple[list[bool]] | list[bool]) -> None:
        """Initialize a FloatArray."""
        if len(args) == 0:
            self.value = []
        elif type(args[0]) is float:
            self.value = list(args)
        else:
            self.value = args[0]

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += bytearray(struct.pack("f", v))
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "FloatArray":
        length = int.from_bytes(buf.read(2), "big")
        arr = [
            float(struct.unpack("f", buf.read(4))[0]) for _ in range(length)
        ]
        return cls(arr)


@register
@dataclass(slots=True)
class DoubleArray(Field[list[float]]):
    """Array with floats with double precision."""

    type_code = TypeCode.DOUBLE_ARRAY

    def __init__(self, *args: tuple[list[bool]] | list[bool]) -> None:
        """Initialize a DoubleArray."""
        if len(args) == 0:
            self.value = []
        elif type(args[0]) is float:
            self.value = list(args)
        else:
            self.value = args[0]

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += bytearray(struct.pack("d", v))
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "DoubleArray":
        length = int.from_bytes(buf.read(2), "big")
        arr = [
            float(struct.unpack("d", buf.read(8))[0]) for _ in range(length)
        ]
        return cls(arr)


@register
@dataclass(slots=True)
class UtfStringArray(Field[list[str]]):
    """Array of Strings with 16-bit length."""

    type_code = TypeCode.UTF_STRING_ARRAY

    def __init__(self, *args: tuple[list[str]] | list[str]) -> None:
        """Initialize a UtfStringArray."""
        if len(args) == 0:
            self.value = []
        elif type(args[0]) is str:
            self.value = list(args)
        else:
            self.value = args[0]

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += write_small_string(v)
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "UtfStringArray":
        length = int.from_bytes(buf.read(2), "big")
        arr = [read_small_string(buf) for _ in range(length)]
        return cls(arr)
