from sfs2x.core.types import (
    Bool,
    BoolArray,
    Byte,
    ByteArray,
    Class,
    Double,
    DoubleArray,
    Float,
    FloatArray,
    Int,
    IntArray,
    Long,
    LongArray,
    SFSArray,
    SFSObject,
    Short,
    ShortArray,
    Text,
    UtfString,
    UtfStringArray,
)

from .buffer import Buffer
from .registry import _registry, decode, register
from .type_codes import TypeCode

__all__ = [
    "Bool",
    "BoolArray",
    "Buffer",
    "Byte",
    "ByteArray",
    "Class",
    "Double",
    "DoubleArray",
    "Float",
    "FloatArray",
    "Int",
    "IntArray",
    "Long",
    "LongArray",
    "SFSArray",
    "SFSObject",
    "Short",
    "ShortArray",
    "Text",
    "TypeCode",
    "UtfString",
    "UtfStringArray",
    "decode",
    "register",
]


def patch_containers() -> None:
    from collections.abc import Callable
    from typing import Any

    from .utils import camel_to_snake

    for _cls in _registry.values():
        name = _cls.__name__

        def _make_put(tp: Any = _cls) -> Callable:  # noqa: ANN401
            # noinspection PyTypeChecker,PyArgumentList
            def _put_x(self: SFSObject, key: str, value: Any) -> SFSObject:  # noqa: ANN401
                if type(value) not in (SFSObject, SFSArray):
                    return self.put(key, tp(value))
                return self.put(key, value)

            return _put_x

        def _make_add(tp: Any = _cls) -> Callable:  # noqa: ANN401
            def _add_x(self: SFSArray, value: Any) -> SFSArray:  # noqa: ANN401
                if type(value) not in (SFSObject, SFSArray):
                    return self.add(tp(value))
                return self.add(value)

            return _add_x

        setattr(SFSObject, f"put_{camel_to_snake(name)}", _make_put())
        setattr(SFSArray, f"add_{camel_to_snake(name)}", _make_add())

patch_containers()
