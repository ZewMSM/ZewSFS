import struct
from dataclasses import dataclass
from typing import ClassVar

from ..buffer import Buffer
from ..field import Field
from ..registry import register
from ..type_codes import TypeCode
from ..utils import write_prefixed_string, read_prefixed_string


class _NumericMixin(Field[int]):
    _size: ClassVar[int]
    type_code: ClassVar[int]

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += self.value.to_bytes(self._size, "big", signed=True)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        value = int.from_bytes(buf.read(cls._size), "big", signed=True)
        return cls(name, value)


@register
@dataclass(slots=True)
class Bool(Field[bool]): # type: ignore[arg-type]
    type_code = TypeCode.BOOL

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload.append(1 if self.value else 0)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer, /):
        value = bool(int.from_bytes(buf.read(1), 'big'))
        return cls(name, value)


@register
@dataclass(slots=True)
class Byte(_NumericMixin):
    _size = 1
    type_code = TypeCode.BYTE


@register
@dataclass(slots=True)
class Short(_NumericMixin):
    _size = 2
    type_code = TypeCode.SHORT


@register
@dataclass(slots=True)
class Int(_NumericMixin):
    _size = 4
    type_code = TypeCode.INT


@register
@dataclass(slots=True)
class Long(_NumericMixin):
    _size = 8
    type_code = TypeCode.LONG


@register
@dataclass(slots=True)
class Float(Field[float]):
    type_code = TypeCode.FLOAT

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += bytearray(struct.pack('f', self.value))
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer, /):
        value = float(struct.unpack('f', buf.read(4))[0])
        return cls(name, value)


@register
@dataclass(slots=True)
class Double(Field[float]):
    type_code: ClassVar[int] = TypeCode.DOUBLE

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += bytearray(struct.pack('d', self.value))
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer, /):
        value = float(struct.unpack('d', buf.read(8))[0])
        return cls(name, value)


@register
@dataclass(slots=True)
class UtfString(Field[str]):
    type_code: ClassVar[int] = TypeCode.UTF_STRING

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += write_prefixed_string(self.value)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer, /):
        value = read_prefixed_string(buf)
        return cls(name, value)

@register
@dataclass(slots=True)
class Text(Field[str]):
    type_code: ClassVar[int] = TypeCode.TEXT

    def to_bytes(self) -> bytearray:
        encoded = self.value.encode('utf-8')

        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += bytearray(len(encoded).to_bytes(4, 'big') + encoded)
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer, /):
        ln = int.from_bytes(buf.read(4), "big")
        value = bytes(buf.read(ln)).decode("utf-8")
        return cls(name, value)