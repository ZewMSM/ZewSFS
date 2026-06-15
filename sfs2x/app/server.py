"""High-level SmartFox server.

    server = SFSServer("tcp://0.0.0.0:9933")

    @server.on_login()
    async def on_login(req: LoginRequest, session: ServerSession):
        if req.password != "secret":
            raise LoginErrorResponse(error_code=1, error_message="bad pw")
        session.zone = req.zone
        session.username = req.username
        raise LoginResponse(zone=req.zone, username=req.username, user_id=42)

    @server.on_extension(command="gs_pussy")
    async def on_pussy(req: PussyRequest):
        raise PussyResponse(length=12)

    async with server:
        await server.serve_forever()
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Any, Self

from sfs2x.app.dispatcher import Dispatcher
from sfs2x.app.handlers import HandlerRegistry
from sfs2x.app.session import ServerSession
from sfs2x.protocol import SysAction
from sfs2x.transport import Acceptor, Transport, server_from_url

HandlerFn = Callable[..., Awaitable[Any]]


class SFSServer:
    """Decorator-driven SFS2X server."""

    def __init__(self, url: str, **acceptor_kwargs: Any) -> None:
        self._url = url
        self._acceptor_kwargs = acceptor_kwargs
        self._registry = HandlerRegistry()
        self._acceptor: Acceptor | None = None
        self._sessions: set[ServerSession] = set()
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def sessions(self) -> frozenset[ServerSession]:
        return frozenset(self._sessions)

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

    async def start(self) -> None:
        if self._acceptor is not None:
            return
        self._acceptor = server_from_url(self._url, **self._acceptor_kwargs)
        await self._acceptor.start()

    async def stop(self) -> None:
        if self._acceptor is None:
            return
        await self._acceptor.close()
        for s in list(self._sessions):
            try:
                await s.transport.close()
            except Exception:  # noqa: BLE001
                pass
        for t in list(self._tasks):
            t.cancel()
        self._acceptor = None

    async def serve_forever(self) -> None:
        if self._acceptor is None:
            await self.start()
        assert self._acceptor is not None
        async for transport in self._acceptor:
            task = asyncio.create_task(self._serve_one(transport))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _serve_one(self, transport: Transport) -> None:
        session = ServerSession(transport, self)
        self._sessions.add(session)
        try:
            dispatcher = Dispatcher(self._registry, transport, session, owner=self)
            await dispatcher.run()
        finally:
            self._sessions.discard(session)
            try:
                await transport.close()
            except Exception:  # noqa: BLE001
                pass

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.stop()
