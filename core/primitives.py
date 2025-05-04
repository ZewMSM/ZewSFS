from dataclasses import dataclass

from .buffer import Buffer
from .field import Field
from .registry import register
from .type_codes import TypeCode
from .utils import write_prefixed_string, read_prefixed_string


@register
@dataclass(slots=True)
class Bool(Field[bool]):
    type_code = TypeCode.BOOL

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload += write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload.append(1 if self.value else 0)
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer, /):
        name = read_prefixed_string(buf)
        value = bool(int.from_bytes(buf.read(1), 'big'))
        return cls(name, value)