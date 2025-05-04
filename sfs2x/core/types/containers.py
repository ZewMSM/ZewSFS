from dataclasses import dataclass
from typing import Any, Dict, List

from ..buffer import Buffer
from ..field import Field
from ..registry import register, decode
from ..type_codes import TypeCode
from ..utils import write_prefixed_string, read_prefixed_string


@register
@dataclass(slots=True)
class Class(Field[Any]):
    type_code = TypeCode.CLASS

    def to_bytes(self) -> bytearray:
        raise NotImplementedError("Class not implemented yet")

    @classmethod
    def from_bytes(cls, buffer: bytearray):
        raise NotImplementedError("Class not implemented yet")


@register
@dataclass(slots=True)
class SFSObject(Field[Dict[str, Field]]):
    type_code = TypeCode.SFS_OBJECT

    value: Dict[str, Field]

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for k, v in self.value.items():
            payload += write_prefixed_string(k)
            payload += v.__class__("", v.value).to_bytes()
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        data: Dict[str, Field] = {}
        for _ in range(length):
            obj = decode(buf)
            data[obj.name] = obj
        return cls(name, data)

    def __getitem__(self, item: str):
        return self.value[item]

    def get(self, item: str, default=None):
        return self.value.get(item, default)

@register
@dataclass(slots=True)
class SFSArray(Field[List[Field]]):
    type_code = TypeCode.SFS_ARRAY

    value: List[Field]

    def to_bytes(self) -> bytearray:
        payload = write_prefixed_string(self.name)
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for elem in self.value:
            # Элементы в массиве *не* имеют собственного имени.
            # Для совместимости ставим name="" – decode примет.
            payload += elem.__class__("", elem.value).to_bytes()
        return payload

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [decode(buf) for _ in range(length)]
        return cls(name, arr)