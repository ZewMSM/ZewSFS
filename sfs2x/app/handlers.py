"""Handler registry and signature introspection.

Decorators on ``SFSClient`` / ``SFSServer`` register async functions
here. At registration time we introspect the function's signature and
remember how to fill each parameter (Message / SFSObject / Session /
Model / Union of models). The dispatcher uses the precomputed
``ParamSpec`` tuple to bind args at call time.
"""

from __future__ import annotations

import inspect
import typing
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field as dc_field
from enum import Enum, auto
from typing import Any, get_args, get_origin

from sfs2x.app.models import SFSModel
from sfs2x.core import SFSObject
from sfs2x.protocol import Message

# Forward references — these classes live in client.py / server.py / session.py
# but we only need to identify them by name at registration time.


class ParamKind(Enum):
    MESSAGE = auto()
    PAYLOAD = auto()
    SESSION = auto()
    CLIENT = auto()
    SERVER = auto()
    MODEL = auto()
    UNION_MODEL = auto()
    POSITIONAL = auto()  # opaque slot, filled positionally for lifecycle hooks


@dataclass(slots=True, frozen=True)
class ParamSpec:
    name: str
    kind: ParamKind
    candidates: tuple[type[SFSModel], ...] = ()


@dataclass(slots=True, frozen=True)
class HandlerEntry:
    fn: Callable[..., Awaitable[Any]]
    params: tuple[ParamSpec, ...]


def _is_model_class(t: Any) -> bool:
    return isinstance(t, type) and issubclass(t, SFSModel)


def _classify(name: str, ann: Any) -> ParamSpec:
    # Lazy imports to avoid cycles
    from sfs2x.app.client import SFSClient
    from sfs2x.app.server import SFSServer
    from sfs2x.app.session import ClientSession, ServerSession

    if ann is inspect.Parameter.empty or ann is None:
        if name in {"msg", "message"}:
            return ParamSpec(name, ParamKind.MESSAGE)
        if name in {"payload", "raw"}:
            return ParamSpec(name, ParamKind.PAYLOAD)
        if name in {"session", "ctx", "ses"}:
            return ParamSpec(name, ParamKind.SESSION)
        if name == "client":
            return ParamSpec(name, ParamKind.CLIENT)
        if name == "server":
            return ParamSpec(name, ParamKind.SERVER)
        return ParamSpec(name, ParamKind.POSITIONAL)

    if ann is Message:
        return ParamSpec(name, ParamKind.MESSAGE)
    if ann is SFSObject:
        return ParamSpec(name, ParamKind.PAYLOAD)
    if ann in (ClientSession, ServerSession):
        return ParamSpec(name, ParamKind.SESSION)
    if ann is SFSClient:
        return ParamSpec(name, ParamKind.CLIENT)
    if ann is SFSServer:
        return ParamSpec(name, ParamKind.SERVER)

    origin = get_origin(ann)
    if origin is typing.Union or origin is type(int | str):
        args = tuple(a for a in get_args(ann) if a is not type(None))
        if all(_is_model_class(a) for a in args) and args:
            if len(args) == 1:
                return ParamSpec(name, ParamKind.MODEL, candidates=(args[0],))
            return ParamSpec(name, ParamKind.UNION_MODEL, candidates=args)
        msg = f"Union parameter {name!r} must contain only SFSModel subclasses"
        raise TypeError(msg)

    if _is_model_class(ann):
        return ParamSpec(name, ParamKind.MODEL, candidates=(ann,))

    return ParamSpec(name, ParamKind.POSITIONAL)


def inspect_handler(fn: Callable[..., Any]) -> tuple[ParamSpec, ...]:
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}
    out: list[ParamSpec] = []
    for name, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        ann = hints.get(name, p.annotation)
        out.append(_classify(name, ann))
    return tuple(out)


@dataclass(slots=True)
class HandlerRegistry:
    system: dict[int, list[HandlerEntry]] = dc_field(default_factory=dict)
    extension: dict[str, list[HandlerEntry]] = dc_field(default_factory=dict)
    catchall: list[HandlerEntry] = dc_field(default_factory=list)
    lifecycle: dict[str, list[HandlerEntry]] = dc_field(default_factory=dict)

    def register_system(self, action: int, fn: Callable[..., Awaitable[Any]]) -> None:
        entry = HandlerEntry(fn=fn, params=inspect_handler(fn))
        self.system.setdefault(int(action), []).append(entry)

    def register_extension(self, command: str, fn: Callable[..., Awaitable[Any]]) -> None:
        entry = HandlerEntry(fn=fn, params=inspect_handler(fn))
        self.extension.setdefault(str(command), []).append(entry)

    def register_catchall(self, fn: Callable[..., Awaitable[Any]]) -> None:
        entry = HandlerEntry(fn=fn, params=inspect_handler(fn))
        self.catchall.append(entry)

    def register_lifecycle(self, name: str, fn: Callable[..., Awaitable[Any]]) -> None:
        entry = HandlerEntry(fn=fn, params=inspect_handler(fn))
        self.lifecycle.setdefault(name, []).append(entry)
