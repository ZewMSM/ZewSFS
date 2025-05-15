from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Never, Union

from sfs2x.core.buffer import Buffer
from sfs2x.core.field import Field
from sfs2x.core.registry import decode, register
from sfs2x.core.type_codes import TypeCode
from sfs2x.core.utils import (
    read_small_string,
    write_small_string,
)


@register
@dataclass(slots=True)
class Class(Field[Any]):
    """Represents a class definition."""

    type_code = TypeCode.CLASS

    def to_bytes(self) -> bytearray:
        msg = "Class not implemented yet"
        raise NotImplementedError(msg)

    @classmethod
    def from_bytes(cls, buffer: bytearray) -> Never:
        msg = "Class not implemented yet"
        raise NotImplementedError(msg)


@register
@dataclass(slots=True)
class SFSObject(Field[dict[str, Field]]):
    """
    SFSObject class for handling a dict of Field objects in serialized format.

    This class represents a dictionary of key-value pairs where keys are
    strings and values are `Field` objects. It supports serialization to bytes,
    deserialization from a buffer, and dictionary-like operations for accessing
    and modifying the data.

    Attributes:
        type_code (TypeCode): The type code for SFSObject.
        value (dict[str, Field]): The dictionary of `Field` objects.

    """

    type_code = TypeCode.SFS_OBJECT

    value: dict[str, Field]

    def __init__(self, value: dict[str, Field] | None = None, **kwargs: Field) -> None:
        if value is None:
            value = {}
        new_value: dict[str, Field] = {}

        value |= kwargs

        for _key, _value in value.items():
            if type(_value) is dict:
                new_value[_key] = SFSObject(_value)
            elif type(_value) is list:
                new_value[_key] = SFSArray(_value)
            else:
                new_value[_key] = _value

        self.value = new_value

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for k, v in self.value.items():
            payload += write_small_string(k)
            payload += v.to_bytes()
        return payload

    # noinspection PyTypeChecker
    @classmethod
    def from_buffer(cls, buf: Buffer) -> "SFSObject":
        """Load SFSObject from a buffer."""
        length = int.from_bytes(buf.read(2), "big")
        data: dict[str, Field] = {}
        for _ in range(length):
            obj_name = read_small_string(buf)
            data[obj_name] = decode(buf)
        return cls(data)

    def get(self, item: str, default: Any = None) -> Any:  # noqa: ANN401
        value = self.value.get(item, default)
        if value is None:
            return default
        if type(value) in (SFSObject, SFSArray):
            return value
        return value.value

    def put(self, item: str, value: Field) -> "SFSObject":
        """Add or update a key-value pair in the SFSObject."""
        if type(value) is dict:
            self.value[item] = SFSObject(value)
        elif type(value) is list:
            self.value[item] = SFSArray(value)
        else:
            self.value[item] = value
        return self

    def __getitem__(self, item: str) -> Any:  # noqa: ANN401
        """Get a value from the SFSObject using dictionary-style access."""
        return self.get(item)

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        """Set a value in the SFSObject using dictionary-style access."""
        if type(value) is dict:
            self.value[key] = SFSObject(value)
        elif type(value) is list:
            self.value[key] = SFSArray(value)
        else:
            self.value[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the SFSObject."""
        return key in self.value

    def keys(self) -> Iterator[str]:
        return iter(self.value.keys())

    def values(self) -> Iterator[Any]:
        for v in self.value.values():
            if type(v) in (SFSObject, SFSArray):
                yield v
            else:
                yield v.value

    def items(self) -> Iterator[tuple[str, Any]]:
        for k, v in self.items():
            if type(v) in (SFSObject, SFSArray):
                yield k, v
            else:
                yield k, v.value

    def __add__(self, other: Union["SFSObject", dict[str, Field]]) -> "SFSObject":
        """Concat 2 SFSArray."""
        return SFSObject(self.value | (other.value if type(other) is SFSObject else other))

    def __or__(self, other: Union["SFSObject", dict[str, Field]]) -> "SFSObject":
        """Concat 2 SFSObjects."""
        return self.__add__(other)

    def update(self, **kwargs: Field) -> "SFSObject":
        return self.__add__(kwargs)


@register
@dataclass(slots=True)
class SFSArray(Field[list[Field]]):
    """
    SFSArray class for handling a list of Field objects in a serialized format.

    This class represents an array of `Field` objects, supporting serialization
    to bytes and deserialization from a buffer. It provides methods for adding
    elements, accessing items, and iterating over the array.

    Attributes:
        type_code (TypeCode): The type code for SFSArray.
        value (list[Field]): The list of `Field` objects.

    """

    type_code = TypeCode.SFS_ARRAY

    value: list[Field]

    def __init__(self, value: list[Field] | None = None, *args: Field) -> None:
        if value is None:
            value = []
        new_value: list[Field] = []

        value.extend(args)

        for _value in value:
            if type(_value) is dict:
                new_value.append(SFSObject(_value))
            elif type(_value) is list:
                new_value.append(SFSArray(_value))
            else:
                new_value.append(_value)

        self.value = new_value

    def to_bytes(self) -> bytearray:
        payload = bytearray()
        payload.append(self.type_code)
        payload += len(self.value).to_bytes(2, "big")
        for elem in self.value:
            payload += elem.to_bytes()
        return payload

    # noinspection PyTypeChecker
    @classmethod
    def from_buffer(cls, buf: Buffer) -> "SFSArray":
        """Load SFSArray from buffer."""
        length = int.from_bytes(buf.read(2), "big")
        arr = [decode(buf) for _ in range(length)]
        return cls(arr)

    def get(self, index: int) -> Any:  # noqa: ANN401
        """Get item from SFSArray."""
        value = self.value[index]
        if type(value) in (SFSObject, SFSArray):
            return value
        return value.value

    def add(self, value: Field) -> "SFSArray":
        """Add field to SFSArray."""
        if type(value) is dict:
            self.value.append(SFSObject(value))
        elif type(value) is list:
            self.value.append(SFSArray(value))
        else:
            self.value.append(value)
        return self

    def __getitem__(self, index: int) -> Any:  # noqa: ANN401
        """Get item from SFSArray."""
        return self.get(index)

    def __iter__(self) -> Iterator[Any]:
        """Iterate all values in SFSArray."""
        for v in self.value:
            if type(v) in (SFSObject, SFSArray):
                yield v.value
            else:
                yield v

    def __add__(self, other: Union["SFSArray", list[Field]]) -> "SFSArray":
        """Concat 2 SFSArray."""
        return SFSArray(self.value + (other.value if type(other) is SFSArray else other))

    def __or__(self, other: Union["SFSArray", list[Field]]) -> "SFSArray":
        """Concat 2 SFSArray."""
        return self.__add__(other)

    def update(self, *kwargs: Field) -> "SFSArray":
        """Update SFSArray."""
        return self.__add__(kwargs)
