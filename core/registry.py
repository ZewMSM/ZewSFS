from typing import Protocol, ClassVar, Any, Dict, Type

from .buffer import Buffer


class Packable(Protocol):
    type_code: ClassVar[int]
    name: str
    value: Any

    def to_bytes(self) -> bytearray: ...

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "Packable": ...

_registry: Dict[int, Type[Packable]] = {}


def register(cls: Type[Packable]) -> Type[Packable]:
    _registry[int(cls.type_code)] = cls
    return cls


def decode(buf: Buffer) -> Packable:
    type_id = int.from_bytes(buf.read(1))
    try:
        cls = _registry[type_id]
    except KeyError as e:
        raise ValueError("Unknown type") from e

    return cls.from_buffer(buf)