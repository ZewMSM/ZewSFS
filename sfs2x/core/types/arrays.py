import struct
from dataclasses import dataclass
from typing import ClassVar

from ..buffer import Buffer
from ..field import Field
from ..registry import register
from ..type_codes import TypeCode
from ..utils import write_prefixed_string, read_prefixed_string


class _NumericArrayMixin(Field[list[int]]):
    _elem_size: ClassVar[int]
    type_code: ClassVar[int]

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += v.to_bytes(self._elem_size, "big", signed=True)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [int.from_bytes(buf.read(cls._elem_size), "big", signed=True) for _ in range(length)]
        return cls(name, arr)

@register
@dataclass(slots=True)
class BoolArray(Field[list[bool]]):
    type_code = TypeCode.BOOL_ARRAY

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload.append(1 if v else 0)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [bool(int.from_bytes(buf.read(1), 'big')) for _ in range(length)]
        return cls(name, arr)


@register
@dataclass(slots=True)
class ByteArray(_NumericArrayMixin):
    _elem_size = 1
    type_code = TypeCode.BYTE_ARRAY


@register
@dataclass(slots=True)
class ShortArray(_NumericArrayMixin):
    _elem_size = 2
    type_code = TypeCode.SHORT_ARRAY


@register
@dataclass(slots=True)
class IntArray(_NumericArrayMixin):
    _elem_size = 4
    type_code = TypeCode.INT_ARRAY


@register
@dataclass(slots=True)
class LongArray(_NumericArrayMixin):
    _elem_size = 8
    type_code = TypeCode.LONG_ARRAY


@register
@dataclass(slots=True)
class FloatArray(Field[list[float]]):
    type_code = TypeCode.FLOAT_ARRAY

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += bytearray(struct.pack('f', v))
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [float(struct.unpack('f', buf.read(4))[0]) for _ in range(length)]
        return cls(name, arr)


@register
@dataclass(slots=True)
class DoubleArray(Field[list[float]]):
    type_code = TypeCode.DOUBLE_ARRAY

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += bytearray(struct.pack('d', v))
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [float(struct.unpack('d', buf.read(8))[0]) for _ in range(length)]
        return cls(name, arr)


@register
@dataclass(slots=True)
class UtfStringArray(Field[list[str]]):
    type_code = TypeCode.UTF_STRING_ARRAY

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for v in self.value:
            payload += write_prefixed_string(v)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [read_prefixed_string(buf) for _ in range(length)]
        return cls(name, arr)
