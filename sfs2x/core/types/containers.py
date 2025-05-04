from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..buffer import Buffer
from ..field import Field
from ..registry import register, decode
from ..type_codes import TypeCode
from ..utils import write_small_string, read_small_string


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

    def __init__(self, value: Optional[Dict[str, Field]] = None):
        if value is None:
            value = {}
        self.value = value

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for k, v in self.value.items():
            payload += write_small_string(k)
            payload += v.to_bytes()
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        data: Dict[str, Field] = {}
        for _ in range(length):
            name = read_small_string(buf)
            data[name] = decode(buf)
        return cls(data)

    def __getitem__(self, item: str):
        return self.value[item]

    def get(self, item: str, default=None):
        return self.value.get(item, default)

@register
@dataclass(slots=True)
class SFSArray(Field[List[Field]]):
    type_code = TypeCode.SFS_ARRAY

    value: List[Field]

    def __init__(self, value: Optional[List[Field]]):
        if value is None:
            value = []
        self.value = value

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for elem in self.value:
            payload += elem.to_bytes()
        return payload

    @classmethod
    def from_buffer(cls, buf: Buffer):
        length = int.from_bytes(buf.read(2), "big")
        arr = [decode(buf) for _ in range(length)]
        return cls(arr)