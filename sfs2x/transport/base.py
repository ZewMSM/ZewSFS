import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

from sfs2x.core import Buffer
from sfs2x.protocol import Message, decode, encode


class TransportClosedError(ConnectionError):
    """Raised when send/recv is attempted on a closed transport."""


class Transport(ABC):
    """Abstract base class for a bidirectional SFS2X message transport.

    Concrete implementations override the four ``_*`` hooks to plug in a
    specific wire protocol (TCP streams, WebSocket frames, etc). The
    public surface (``open`` / ``send`` / ``recv`` / ``close`` / ``listen``)
    is the same regardless of the underlying transport.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._compress_threshold = compress_threshold
        self._encryption_key = encryption_key
        self._opened = False

    @property
    def closed(self) -> bool:
        return not self._opened

    async def open(self) -> Self:
        if self._opened:
            return self
        await self._open()
        self._opened = True
        return self

    async def send(self, msg: Message) -> None:
        if not self._opened:
            raise TransportClosedError("Connection closed by remote host")
        await self._send_raw(
            encode(
                msg,
                compress_threshold=self._compress_threshold,
                encryption_key=self._encryption_key,
            ),
        )

    async def recv(self) -> Message:
        if not self._opened:
            raise TransportClosedError("Connection closed by remote host")
        raw = await self._recv_raw()
        return decode(Buffer(raw), encryption_key=self._encryption_key)

    async def close(self) -> None:
        if self._opened:
            self._opened = False
            await self._close_impl()

    async def listen(self) -> AsyncIterator[Message]:
        """Yield messages until the transport is closed."""
        while self._opened:
            try:
                yield await self.recv()
            except (ConnectionError, RuntimeError):
                break

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @abstractmethod
    async def _open(self) -> None: ...

    @abstractmethod
    async def _send_raw(self, raw: bytes) -> None: ...

    @abstractmethod
    async def _recv_raw(self) -> bytes:
        """Return one complete on-wire SFS2X packet (header + body)."""

    @abstractmethod
    async def _close_impl(self) -> None: ...


class Acceptor(ABC):
    """Abstract base class for a server-side acceptor.

    Lifecycle::

        acceptor = SomeAcceptor(host, port)
        await acceptor.start()
        async for client in acceptor:
            ...
        await acceptor.close()

    or, equivalently::

        async with SomeAcceptor(host, port) as acceptor:
            async for client in acceptor:
                ...
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self._compress_threshold = compress_threshold
        self._encryption_key = encryption_key
        self._queue: asyncio.Queue[Transport] = asyncio.Queue()
        self._started = False

    async def start(self) -> Self:
        if self._started:
            return self
        await self._start()
        self._started = True
        return self

    async def close(self) -> None:
        if not self._started:
            return
        self._started = False
        await self._close()

    async def accept(self) -> AsyncIterator[Transport]:
        if not self._started:
            await self.start()
        while self._started:
            yield await self._queue.get()

    def __aiter__(self) -> AsyncIterator[Transport]:
        return self.accept()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @abstractmethod
    async def _start(self) -> None: ...

    @abstractmethod
    async def _close(self) -> None: ...
