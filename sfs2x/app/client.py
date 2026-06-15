"""High-level SmartFox client.

Wraps a ``Transport`` with decorator-style message handlers, typed
request/response models and lifecycle helpers.

    client = SFSClient("tcp://localhost:9933")

    @client.on_extension(command="gs_pussy")
    async def on_pussy(req: PussyRequest):
        raise PussyResponse(length=12)

    async with client:
        await client.handshake()
        await client.login(zone="MyZone", username="user")
        await client.run_forever()
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self

from sfs2x.app.dispatcher import Dispatcher
from sfs2x.app.handlers import HandlerRegistry
from sfs2x.app.models import SFSModel
from sfs2x.app.responses import Reply
from sfs2x.app.session import ClientSession
from sfs2x.app.system_models import (
    HandshakeRequest,
    LoginRequest,
    LogoutRequest,
)
from sfs2x.core import SFSObject
from sfs2x.protocol import Message, SysAction
from sfs2x.transport import Transport, client_from_url

HandlerFn = Callable[..., Awaitable[Any]]


class SFSClient:
    """Decorator-driven SFS2X client."""

    def __init__(self, url: str, **transport_kwargs: Any) -> None:
        self._url = url
        self._transport_kwargs = transport_kwargs
        self._registry = HandlerRegistry()
        self._transport: Transport | None = None
        self._session: ClientSession | None = None
        self._dispatch_task: asyncio.Task[None] | None = None

    @property
    def transport(self) -> Transport | None:
        return self._transport

    @property
    def session(self) -> ClientSession | None:
        return self._session

    @property
    def connected(self) -> bool:
        return self._transport is not None and not self._transport.closed

    def on_system(self, action: int | SysAction) -> Callable[[HandlerFn], HandlerFn]:
        def wrap(fn: HandlerFn) -> HandlerFn:
            self._registry.register_system(int(action), fn)
            return fn

        return wrap

    def on_handshake(self) -> Callable[[HandlerFn], HandlerFn]:
        return self.on_system(SysAction.HANDSHAKE)

    def on_login(self) -> Callable[[HandlerFn], HandlerFn]:
        return self.on_system(SysAction.LOGIN)

    def on_logout(self) -> Callable[[HandlerFn], HandlerFn]:
        return self.on_system(SysAction.LOGOUT)

    def on_ping_pong(self) -> Callable[[HandlerFn], HandlerFn]:
        return self.on_system(SysAction.PING_PONG)

    def on_extension(self, command: str) -> Callable[[HandlerFn], HandlerFn]:
        def wrap(fn: HandlerFn) -> HandlerFn:
            self._registry.register_extension(command, fn)
            return fn

        return wrap

    def on_message(self) -> Callable[[HandlerFn], HandlerFn]:
        def wrap(fn: HandlerFn) -> HandlerFn:
            self._registry.register_catchall(fn)
            return fn

        return wrap

    def on_connect(self) -> Callable[[HandlerFn], HandlerFn]:
        def wrap(fn: HandlerFn) -> HandlerFn:
            self._registry.register_lifecycle("connect", fn)
            return fn

        return wrap

    def on_disconnect(self) -> Callable[[HandlerFn], HandlerFn]:
        def wrap(fn: HandlerFn) -> HandlerFn:
            self._registry.register_lifecycle("disconnect", fn)
            return fn

        return wrap

    def on_error(self) -> Callable[[HandlerFn], HandlerFn]:
        def wrap(fn: HandlerFn) -> HandlerFn:
            self._registry.register_lifecycle("error", fn)
            return fn

        return wrap

    async def connect(self) -> None:
        if self.connected:
            return
        self._transport = client_from_url(self._url, **self._transport_kwargs)
        await self._transport.open()
        self._session = ClientSession(self._transport, self)
        dispatcher = Dispatcher(
            self._registry, self._transport, self._session, owner=self
        )
        self._dispatch_task = asyncio.create_task(dispatcher.run())

    async def disconnect(self) -> None:
        if self._transport is None:
            return
        await self._transport.close()
        if self._dispatch_task is not None:
            try:
                await self._dispatch_task
            except Exception:  # noqa: BLE001
                pass
        self._transport = None
        self._session = None
        self._dispatch_task = None

    async def run_forever(self) -> None:
        if not self.connected:
            await self.connect()
        assert self._dispatch_task is not None
        await self._dispatch_task

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.disconnect()

    async def send(self, item: Message | SFSModel | Reply) -> None:
        if self._session is None:
            msg = "Client is not connected"
            raise RuntimeError(msg)
        await self._session.send(item)

    async def handshake(
        self,
        api: str = "1.7.3",
        cl: str = "Python/ZewSFS",
        bin: bool = True,  # noqa: A002
    ) -> None:
        await self.send(HandshakeRequest(api=api, cl=cl, bin=bin))

    async def login(
        self,
        zone: str,
        username: str = "",
        password: str = "",
        params: SFSObject | dict | None = None,
    ) -> None:
        if params is None:
            params = SFSObject()
        elif isinstance(params, dict):
            params = SFSObject(params)
        await self.send(
            LoginRequest(zone=zone, username=username, password=password, params=params)
        )

    async def logout(self) -> None:
        await self.send(LogoutRequest())

    async def call_extension(
        self,
        command: str,
        params: SFSModel | SFSObject | dict | None = None,
    ) -> None:
        if params is None:
            obj: SFSObject = SFSObject()
        elif isinstance(params, SFSModel):
            obj = params.to_sfs_object()
        elif isinstance(params, dict):
            obj = SFSObject(params)
        else:
            obj = params
        await self.send(Message.extension(command, obj))
