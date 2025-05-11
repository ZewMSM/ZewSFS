from typing import Any, ClassVar, Protocol, runtime_checkable

from .buffer import Buffer


@runtime_checkable
class Packable(Protocol):
    """Represents a packable object, which can be packed into binary."""

    type_code: ClassVar[int]
    value: Any

    def to_bytes(self) -> bytearray: ...

    @classmethod
    def from_buffer(cls, buf: Buffer) -> "Packable": ...

_registry: dict[int, type[Packable]] = {}


def register(cls: type[Packable]) -> type[Packable]:
    _registry[int(cls.type_code)] = cls
    return cls


def decode(buf: Buffer) -> Packable:
    """Decode buffer into Packable."""
    type_id = int.from_bytes(buf.read(1))

    try:
        cls = _registry[type_id]
    except KeyError as e:
        msg = "Unknown type"
        raise ValueError(msg) from e

    return cls.from_buffer(buf)
