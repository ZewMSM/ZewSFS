import contextlib
import logging
import ssl as _ssl
from typing import Self

import websockets
from websockets.asyncio.client import ClientConnection, connect
from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from sfs2x.transport.base import Acceptor, Transport, TransportClosedError

logger = logging.getLogger("SFS2X/WSTransport")

DEFAULT_WS_PATH = "/BlueBox/websocket"


class WSTransport(Transport):
    """SFS2X transport over WebSocket binary frames.

    Each WebSocket binary message carries one complete SFS2X packet
    (BINARY-flag byte + 2/4-byte big-endian length + body) — the same
    framing used over plain TCP. This matches SmartFoxServer 2X v2.13+
    where the WebSocket endpoint speaks the standard binary protocol.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        path: str = DEFAULT_WS_PATH,
        secure: bool = False,
        ssl: _ssl.SSLContext | None = None,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        super().__init__(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
        self.path = path if path.startswith("/") else f"/{path}"
        self.secure = secure
        self._ssl_ctx = ssl
        self._ws: ClientConnection | ServerConnection | None = None

    @classmethod
    def _from_ws(
        cls,
        ws: ServerConnection,
        *,
        path: str = DEFAULT_WS_PATH,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> Self:
        host, port = ws.remote_address[:2]
        inst = cls(
            host,
            port,
            path=path,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
        inst._ws = ws
        inst._opened = True
        return inst

    @property
    def url(self) -> str:
        scheme = "wss" if self.secure else "ws"
        return f"{scheme}://{self.host}:{self.port}{self.path}"

    async def _open(self) -> None:
        ssl_arg = self._ssl_ctx if self.secure else None
        self._ws = await connect(self.url, subprotocols=None, ssl=ssl_arg)
        logger.info("Opened WS connection to %s", self.url)

    async def _send_raw(self, raw: bytes) -> None:
        if self._ws is None:
            raise TransportClosedError("Connection closed by remote host")
        try:
            await self._ws.send(bytes(raw))
        except ConnectionClosed as e:
            raise TransportClosedError("Connection closed by remote host") from e
        logger.info("Sent %s bytes (ws)", len(raw))

    async def _recv_raw(self) -> bytes:
        if self._ws is None:
            raise TransportClosedError("Connection closed by remote host")
        try:
            frame = await self._ws.recv()
        except ConnectionClosed as e:
            raise TransportClosedError("Connection closed by remote host") from e

        if isinstance(frame, str):
            raise RuntimeError("Received text frame; expected binary SFS2X packet")

        logger.info("Received %s bytes (ws) from %s:%s", len(frame), self.host, self.port)
        return frame

    async def _close_impl(self) -> None:
        if self._ws is not None:
            with contextlib.suppress(ConnectionClosed):
                await self._ws.close()
        logger.info("Closed WS connection to %s", self.url)


class WSAcceptor(Acceptor):
    """Server-side WebSocket acceptor.

    Accepts connections to ``path`` (default ``/BlueBox/websocket``) and
    yields one :class:`WSTransport` per client.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        path: str = DEFAULT_WS_PATH,
        ssl: _ssl.SSLContext | None = None,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        super().__init__(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
        self.path = path if path.startswith("/") else f"/{path}"
        self._ssl_ctx = ssl
        self._server: Server | None = None

    async def _start(self) -> None:
        self._server = await serve(
            self._on_conn,
            self.host,
            self.port,
            ssl=self._ssl_ctx,
            subprotocols=None,
        )
        logger.info(
            "Started WS server on %s://%s:%s%s",
            "wss" if self._ssl_ctx else "ws",
            self.host,
            self.port,
            self.path,
        )

    async def _close(self) -> None:
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
        logger.info("Stopped WS server on %s:%s", self.host, self.port)

    async def _on_conn(self, ws: ServerConnection) -> None:
        request_path = _ws_request_path(ws)
        if request_path != self.path:
            await ws.close(code=1003, reason=f"Unknown path: {request_path}")
            return

        transport = WSTransport._from_ws(
            ws,
            path=self.path,
            compress_threshold=self._compress_threshold,
            encryption_key=self._encryption_key,
        )
        logger.info("WS connection from %s:%s", transport.host, transport.port)
        await self._queue.put(transport)

        # websockets closes the connection when the handler returns, so we
        # need to keep it alive while the application is using the transport.
        await ws.wait_closed()


def _ws_request_path(ws: ServerConnection) -> str:
    """Extract the HTTP request path from an incoming WebSocket connection."""
    request = getattr(ws, "request", None)
    if request is not None and getattr(request, "path", None):
        return request.path
    # Fallback for older websockets versions.
    return getattr(ws, "path", "/")


__all__ = ["DEFAULT_WS_PATH", "WSAcceptor", "WSTransport"]

# Ensure websockets is importable at module import time so a missing
# install fails fast with a clear hint.
_ = websockets.__version__
