"""Routes incoming Messages to registered handlers.

The dispatcher is constructed per-connection (one for each ``SFSClient``
and one for each ``ServerSession``). It pulls messages from
``Transport.listen()``, looks up handlers by ``(controller, action)`` or
extension command, binds parameters from the message + session, calls
the handler, and turns any raised/returned response model back into a
``Message`` on the wire.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sfs2x.app.handlers import HandlerEntry, HandlerRegistry, ParamKind
from sfs2x.app.models import ParseError, SFSModel
from sfs2x.app.responses import (
    ExtensionRequest,
    ExtensionResponse,
    Reply,
    SystemRequest,
    SystemResponse,
    _RaisableMixin,
)
from sfs2x.core import SFSObject
from sfs2x.protocol import ControllerID, Message
from sfs2x.transport import Transport

if TYPE_CHECKING:
    from sfs2x.app.session import ClientSession, ServerSession

log = logging.getLogger("sfs2x.app")


class Dispatcher:
    """Drives the receive-loop for a single transport."""

    def __init__(
        self,
        registry: HandlerRegistry,
        transport: Transport,
        session: ClientSession | ServerSession,
        owner: Any,
    ) -> None:
        self._registry = registry
        self._transport = transport
        self._session = session
        self._owner = owner

    async def run(self) -> None:
        await self._fire_lifecycle("connect")
        try:
            async for msg in self._transport.listen():
                await self._dispatch_one(msg)
        finally:
            await self._fire_lifecycle("disconnect")

    async def _fire_lifecycle(self, name: str, *extra: Any) -> None:
        for entry in self._registry.lifecycle.get(name, []):
            try:
                kwargs = self._bind_lifecycle(entry, extra)
                await entry.fn(**kwargs)
            except Exception:  # noqa: BLE001
                log.exception("lifecycle handler %s raised", name)

    def _bind_lifecycle(self, entry: HandlerEntry, extra: tuple[Any, ...]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        extra_iter = iter(extra)
        for spec in entry.params:
            if spec.kind == ParamKind.SESSION:
                kwargs[spec.name] = self._session
            elif spec.kind == ParamKind.CLIENT or spec.kind == ParamKind.SERVER:
                kwargs[spec.name] = self._owner
            else:
                try:
                    kwargs[spec.name] = next(extra_iter)
                except StopIteration:
                    kwargs[spec.name] = None
        return kwargs

    async def _dispatch_one(self, msg: Message) -> None:
        handlers = self._lookup(msg)
        if not handlers:
            return
        for entry in handlers:
            try:
                kwargs = self._bind(entry, msg)
            except ParseError as e:
                log.debug("skipping handler %s: %s", entry.fn.__qualname__, e)
                continue
            try:
                result = await entry.fn(**kwargs)
            except _RaisableMixin as resp:
                await self._send_reply(resp, msg)
                return
            except Reply as r:
                await self._send_reply(r.model, msg)
                return
            except Exception as e:  # noqa: BLE001
                await self._fire_lifecycle("error", e, msg)
                continue
            if isinstance(result, SFSModel):
                await self._send_reply(result, msg)
                return

    def _lookup(self, msg: Message) -> list[HandlerEntry]:
        handlers: list[HandlerEntry] = []
        if msg.controller == ControllerID.SYSTEM:
            handlers.extend(self._registry.system.get(int(msg.action), []))
        elif msg.controller == ControllerID.EXTENSION:
            cmd = msg.payload.get("c")
            if cmd is not None:
                handlers.extend(self._registry.extension.get(str(cmd), []))
        handlers.extend(self._registry.catchall)
        return handlers

    def _extract_payload(self, msg: Message) -> SFSObject:
        if msg.controller == ControllerID.EXTENSION:
            params = msg.payload.value.get("p")
            if isinstance(params, SFSObject):
                return params
            return SFSObject()
        return msg.payload

    def _bind(self, entry: HandlerEntry, msg: Message) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        payload: SFSObject | None = None
        for spec in entry.params:
            if spec.kind == ParamKind.MESSAGE:
                kwargs[spec.name] = msg
            elif spec.kind == ParamKind.PAYLOAD:
                if payload is None:
                    payload = self._extract_payload(msg)
                kwargs[spec.name] = payload
            elif spec.kind == ParamKind.SESSION:
                kwargs[spec.name] = self._session
            elif spec.kind == ParamKind.CLIENT or spec.kind == ParamKind.SERVER:
                kwargs[spec.name] = self._owner
            elif spec.kind == ParamKind.MODEL:
                if payload is None:
                    payload = self._extract_payload(msg)
                kwargs[spec.name] = spec.candidates[0].from_sfs_object(payload)
            elif spec.kind == ParamKind.UNION_MODEL:
                if payload is None:
                    payload = self._extract_payload(msg)
                chosen: SFSModel | None = None
                for cand in spec.candidates:
                    chosen = cand.try_from_sfs_object(payload)
                    if chosen is not None:
                        break
                if chosen is None:
                    names = ", ".join(c.__name__ for c in spec.candidates)
                    msg_err = f"Payload did not match any of: {names}"
                    raise ParseError(msg_err)
                kwargs[spec.name] = chosen
            elif spec.kind == ParamKind.POSITIONAL:
                kwargs[spec.name] = None
        return kwargs

    async def _send_reply(self, model: SFSModel, original: Message) -> None:
        if isinstance(model, (SystemResponse, SystemRequest)):
            reply_msg = model.to_message()
        elif isinstance(model, (ExtensionResponse, ExtensionRequest)):
            request_id = -1
            if original.controller == ControllerID.EXTENSION:
                r = original.payload.get("r")
                if isinstance(r, int):
                    request_id = r
            reply_msg = model.to_message(request_id=request_id)
        else:
            msg_err = (
                f"Cannot turn {type(model).__name__} into a reply Message "
                f"— inherit from SystemResponse or ExtensionResponse."
            )
            raise TypeError(msg_err)
        await self._transport.send(reply_msg)
