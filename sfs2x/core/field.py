from dataclasses import dataclass
from typing import TypeVar, Generic, ClassVar

from .buffer import Buffer
from .registry import Packable

T = TypeVar('T')

@dataclass(slots=True)
class Field(Packable, Generic[T]):
    name: str
    value: T

    type_code: ClassVar[int]

    def to_bytes(self) -> bytearray:
        raise NotImplementedError()

    @classmethod
    def from_buffer(cls, name: str, buf: Buffer, /):
        raise NotImplementedError()