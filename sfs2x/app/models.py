"""Typed payload models on top of SFSObject.

Field annotations are SFS-types (``UtfString``, ``Int``, ``Long``, nested
``SFSModel`` subclasses, ``SFSObject``/``SFSArray``) — never plain Python
types. The annotation tells the framework how to encode the value on the
wire; the attribute itself stores the raw Python value (``str``/``int``/…)
so the model behaves like a plain dataclass at runtime.
"""

from __future__ import annotations

import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, get_args, get_origin

from sfs2x.core import SFSArray, SFSObject
from sfs2x.core.field import Field


class _MissingType:
    """Sentinel for "no default given"."""

    _instance: _MissingType | None = None

    def __new__(cls) -> _MissingType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING = _MissingType()


class ParseError(ValueError):
    """Failed to construct an SFSModel from an SFSObject."""


@dataclass(slots=True, frozen=True)
class _FieldMarker:
    """Sentinel placed into the class body via ``field(...)``."""

    sfs_key: str
    default: Any
    factory: Callable[[], Any] | None


def field(
    sfs_key: str,
    *,
    default: Any = MISSING,
    default_factory: Callable[[], Any] | None = None,
) -> Any:
    """Mark an SFSModel attribute and bind it to an SFSObject key.

    Example: ``zone: UtfString = field("zn")``.
    """
    if default is not MISSING and default_factory is not None:
        msg = "Cannot specify both default and default_factory"
        raise ValueError(msg)
    return _FieldMarker(sfs_key=sfs_key, default=default, factory=default_factory)


@dataclass(slots=True, frozen=True)
class FieldSpec:
    """Compiled metadata for one model attribute."""

    py_name: str
    sfs_key: str
    field_cls: type
    optional: bool
    default: Any
    factory: Callable[[], Any] | None

    @property
    def has_default(self) -> bool:
        return self.default is not MISSING or self.factory is not None


def _resolve_annotation(ann: Any) -> tuple[type, bool]:
    """Strip ``Optional`` / ``T | None`` and return ``(inner, optional)``."""
    origin = get_origin(ann)
    if origin is typing.Union or origin is type(int | str):
        args = [a for a in get_args(ann) if a is not type(None)]
        if len(args) != 1:
            msg = f"Unsupported Union annotation: {ann!r}"
            raise TypeError(msg)
        return args[0], True
    return ann, False


def _validate_field_class(cls: type) -> None:
    """Allow only Field subclasses, SFSModel subclasses, SFSObject, SFSArray."""
    if cls is SFSObject or cls is SFSArray:
        return
    if isinstance(cls, type) and issubclass(cls, Field):
        return
    if isinstance(cls, type) and issubclass(cls, SFSModel):
        return
    msg = (
        f"SFSModel field annotation must be an SFS type (Field subclass, "
        f"SFSObject, SFSArray, or another SFSModel). Got: {cls!r}"
    )
    raise TypeError(msg)


def _collect_fields(cls: type) -> dict[str, FieldSpec]:
    """Walk MRO and merge per-class field specs (subclass overrides base)."""
    out: dict[str, FieldSpec] = {}
    for base in reversed(cls.__mro__):
        own = base.__dict__.get("__sfs_fields_own__")
        if own:
            out.update(own)
    return out


def _build_own_fields(ns: dict[str, Any], hints: dict[str, Any]) -> dict[str, FieldSpec]:
    """Compile this class body's annotated attributes into FieldSpecs."""
    fields: dict[str, FieldSpec] = {}
    annotations = ns.get("__annotations__", {})
    for attr_name, raw_ann in annotations.items():
        if attr_name.startswith("_"):
            continue
        if attr_name in {"__action__", "__command__"}:
            continue
        ann = hints.get(attr_name, raw_ann)
        inner_cls, optional = _resolve_annotation(ann)
        _validate_field_class(inner_cls)

        marker = ns.get(attr_name, MISSING)
        if isinstance(marker, _FieldMarker):
            sfs_key = marker.sfs_key
            default = marker.default
            factory = marker.factory
        else:
            sfs_key = attr_name
            default = MISSING if marker is MISSING else marker
            factory = None

        fields[attr_name] = FieldSpec(
            py_name=attr_name,
            sfs_key=sfs_key,
            field_cls=inner_cls,
            optional=optional,
            default=default,
            factory=factory,
        )
    return fields


def _make_init(fields: dict[str, FieldSpec]) -> Callable[..., None]:
    names = list(fields.keys())

    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
        if len(args) > len(names):
            msg = f"Too many positional arguments (max {len(names)})"
            raise TypeError(msg)
        for i, val in enumerate(args):
            n = names[i]
            if n in kwargs:
                msg = f"Multiple values for argument {n!r}"
                raise TypeError(msg)
            kwargs[n] = val
        extra = set(kwargs) - set(fields)
        if extra:
            msg = f"Unknown fields for {type(self).__name__}: {sorted(extra)}"
            raise TypeError(msg)
        for name, spec in fields.items():
            if name in kwargs:
                value = kwargs[name]
            elif spec.factory is not None:
                value = spec.factory()
            elif spec.default is not MISSING:
                value = spec.default
            elif spec.optional:
                value = None
            else:
                msg = f"Missing required field {name!r} for {type(self).__name__}"
                raise TypeError(msg)
            object.__setattr__(self, name, value)

    return __init__


def _make_repr(name: str, fields: dict[str, FieldSpec]) -> Callable[[Any], str]:
    field_names = list(fields.keys())

    def __repr__(self: Any) -> str:
        parts = ", ".join(f"{n}={getattr(self, n)!r}" for n in field_names)
        return f"{name}({parts})"

    return __repr__


def _make_eq(fields: dict[str, FieldSpec]) -> Callable[[Any, Any], bool]:
    field_names = list(fields.keys())

    def __eq__(self: Any, other: Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return all(getattr(self, n) == getattr(other, n) for n in field_names)

    return __eq__


class SFSModelMeta(type):
    """Metaclass: collect fields, install ``__init__``/``__repr__``/``__eq__``."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        ns: dict[str, Any],
        **kwargs: Any,
    ) -> SFSModelMeta:
        cls = super().__new__(mcs, name, bases, ns)

        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            hints = ns.get("__annotations__", {})

        own = _build_own_fields(ns, hints)
        cls.__sfs_fields_own__ = own

        for attr_name in own:
            if attr_name in cls.__dict__ and isinstance(cls.__dict__[attr_name], _FieldMarker):
                try:
                    delattr(cls, attr_name)
                except AttributeError:
                    pass

        cls.__sfs_fields__ = _collect_fields(cls)

        action = kwargs.get("action")
        command = kwargs.get("command")
        if action is not None:
            cls.__action__ = int(action)
        if command is not None:
            cls.__command__ = str(command)

        if cls.__sfs_fields__ and "__init__" not in ns:
            cls.__init__ = _make_init(cls.__sfs_fields__)
        if "__repr__" not in ns and cls.__sfs_fields__:
            cls.__repr__ = _make_repr(name, cls.__sfs_fields__)
        if "__eq__" not in ns and cls.__sfs_fields__:
            cls.__eq__ = _make_eq(cls.__sfs_fields__)

        return cls

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        ns: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, ns)


class SFSModel(metaclass=SFSModelMeta):
    """Base class for typed SFS-payload models.

    Subclasses declare annotated attributes whose types are SFS Field
    classes. The metaclass collects them, generates a keyword-friendly
    ``__init__`` and binds the SFS key for each via ``field("...")``.
    """

    __sfs_fields__: ClassVar[dict[str, FieldSpec]] = {}
    __sfs_fields_own__: ClassVar[dict[str, FieldSpec]] = {}

    def to_sfs_object(self) -> SFSObject:
        out = SFSObject()
        for spec in type(self).__sfs_fields__.values():
            raw = getattr(self, spec.py_name)
            if raw is None:
                if spec.optional:
                    continue
                msg = f"Field {spec.py_name!r} is required but None"
                raise ParseError(msg)
            out.value[spec.sfs_key] = _wrap(raw, spec.field_cls)
        return out

    @classmethod
    def from_sfs_object(cls, obj: SFSObject) -> SFSModel:
        if not isinstance(obj, SFSObject):
            msg = f"Expected SFSObject, got {type(obj).__name__}"
            raise ParseError(msg)
        kwargs: dict[str, Any] = {}
        for spec in cls.__sfs_fields__.values():
            if spec.sfs_key not in obj.value:
                if spec.has_default or spec.optional:
                    continue
                msg = f"Missing required key {spec.sfs_key!r} for {cls.__name__}"
                raise ParseError(msg)
            raw_field = obj.value[spec.sfs_key]
            kwargs[spec.py_name] = _unwrap(raw_field, spec.field_cls)
        try:
            return cls(**kwargs)
        except TypeError as e:
            raise ParseError(str(e)) from e

    @classmethod
    def try_from_sfs_object(cls, obj: SFSObject) -> SFSModel | None:
        try:
            return cls.from_sfs_object(obj)
        except (ParseError, TypeError, ValueError):
            return None


def _wrap(raw: Any, field_cls: type) -> Any:
    """Encode a raw Python value into the declared SFS field instance."""
    if field_cls is SFSObject or field_cls is SFSArray:
        if isinstance(raw, (SFSObject, SFSArray)):
            return raw
        if field_cls is SFSObject and isinstance(raw, dict):
            return SFSObject(raw)
        if field_cls is SFSArray and isinstance(raw, list):
            return SFSArray(raw)
        msg = f"Cannot pack {type(raw).__name__} as {field_cls.__name__}"
        raise ParseError(msg)
    if isinstance(field_cls, type) and issubclass(field_cls, SFSModel):
        if isinstance(raw, field_cls):
            return raw.to_sfs_object()
        if isinstance(raw, SFSObject):
            return raw
        msg = f"Expected {field_cls.__name__} or SFSObject, got {type(raw).__name__}"
        raise ParseError(msg)
    if isinstance(raw, Field):
        return raw
    return field_cls(raw)


def _unwrap(raw_field: Any, field_cls: type) -> Any:
    """Decode a Field instance from the wire back into the runtime value."""
    if field_cls is SFSObject or field_cls is SFSArray:
        return raw_field
    if isinstance(field_cls, type) and issubclass(field_cls, SFSModel):
        if isinstance(raw_field, SFSObject):
            return field_cls.from_sfs_object(raw_field)
        if isinstance(raw_field, Field) and isinstance(raw_field.value, SFSObject):
            return field_cls.from_sfs_object(raw_field.value)
        msg = f"Expected SFSObject for {field_cls.__name__}, got {type(raw_field).__name__}"
        raise ParseError(msg)
    if isinstance(raw_field, Field):
        return raw_field.value
    return raw_field
