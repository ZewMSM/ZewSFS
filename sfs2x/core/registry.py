from typing import Protocol, ClassVar, Any, Dict, Type, runtime_checkable

from .buffer import Buffer
from .utils import read_prefixed_string


@runtime_checkable
class Packable(Protocol):
    type_code: ClassVar[int]
    name: str
    value: Any

    def to_bytes(self) -> bytearray: ...

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer) -> "Packable": ...

_registry: Dict[int, Type[Packable]] = {}


def register(cls: Type[Packable]) -> Type[Packable]:
    _registry[int(cls.type_code)] = cls
    return cls


def decode(buf: Buffer, skip_name = False):
    if skip_name:
        name = ""
    else:
        name = read_prefixed_string(buf)
    type_id = int.from_bytes(buf.read(1))

    try:
        cls = _registry[type_id]
    except KeyError as e:
        raise ValueError("Unknown type") from e

    return cls.from_buffer(name, buf)
