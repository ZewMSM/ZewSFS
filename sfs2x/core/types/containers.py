from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Iterator

from sfs2x.core.field import T
from ..buffer import Buffer
from ..field import Field
from ..registry import register, decode, _registry
from ..type_codes import TypeCode
from ..utils import write_small_string, read_small_string, camel_to_snake


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
            obj_name = read_small_string(buf)
            data[obj_name] = decode(buf)
        return cls(data)

    def get(self, item: str, default=None):
        value = self.value.get(item, default)
        if value is None:
            return default
        if type(value) in (SFSObject, SFSArray):
            return value
        return value.value

    def put(self, item: str, value: Field):
        self.value[item] = value
        return self

    def __getitem__(self, item: str):
        return self.get(item)

    def __setitem__(self, key, value):
        self.value[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.value

    def keys(self) -> Iterator[str]:
        return iter(self.value.keys())

    def values(self) -> Iterator[Dict[str, Field]]:
        return iter([v.value if type(v) not in (SFSObject, SFSArray) else v for v in self.value.values()])

    def items(self):
        return zip(self.keys(), self.values())



@register
@dataclass(slots=True)
class SFSArray(Field[List[Field]]):
    type_code = TypeCode.SFS_ARRAY

    value: List[Field]

    def __init__(self, value: Optional[List[Field]] = None):
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

    def get(self, index: int):
        value = self.value[index]
        if type(value) in (SFSObject, SFSArray):
            return value
        return value.value

    def add(self, value: Field):
        self.value.append(value)
        return self

    def __getitem__(self, index: int):
        return self.get(index)

    def __contains__(self, item):
        return item in self.value

    def __iter__(self) -> Iterator[T]:
        return iter([v.value if type(v) not in (SFSObject, SFSArray) else v for v in self.value])


for _cls in _registry.values():
    name = _cls.__name__
    def _make_put(tp=_cls):
        # noinspection PyArgumentList
        def _put_x(self, key: str, value):
            if type(value) not in (SFSObject, SFSArray):
                return self.put(key, tp(value))
            else:
                return self.put(key, value)
        return _put_x
    def _make_add(tp=_cls):
        # noinspection PyArgumentList
        def _add_x(self, value):
            if type(value) not in (SFSObject, SFSArray):
                return self.add(tp(value))
            else:
                return self.add(value)
        return _add_x
    setattr(SFSObject, f"put_{camel_to_snake(name)}", _make_put())
    setattr(SFSArray, f"add_{camel_to_snake(name)}", _make_add())