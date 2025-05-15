from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar

from .buffer import Buffer
from .registry import Packable

T = TypeVar("T")


@dataclass(slots=True)
class Field(Packable, Generic[T]):
    """Represents a object, which can be packed into sfs binary."""

    type_code: ClassVar[int]
    value: T

    def to_bytes(self) -> bytearray:
        raise NotImplementedError

    @classmethod
    def from_buffer(cls, buf: Buffer, /) -> "Field":
        raise NotImplementedError

    # noinspection PyArgumentList
    def __add__(self, other: "Field") -> "Field":
        """Concatenate two fields."""
        return self.__class__(self.value + (other.value if type(other) is self.__class__ else other))

    def __or__(self, other: "Field") -> "Field":
        """Concatenate two fields."""
        return self.__class__(self.value | (other.value if type(other) is self.__class__ else other))
