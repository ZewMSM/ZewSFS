from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from sfs2x.core import Buffer
from sfs2x.protocol import Message, decode, encode


class Transport(ABC):
    """Abstract base class for transports."""

    _closed: bool
    _compress_threshold: int | None = None
    _encryption_key: bytes | None = None

    def __init__(self) -> None:
        self._closed = True

    async def open(self) -> "Transport":
        await self._open()
        self._closed = False
        return self

    async def send(self, msg: Message) -> None:
        if self._closed:
            err_msg = "Connection closed by remote host"
            raise ConnectionError(err_msg)
        await self._send_raw(
            encode(msg, compress_threshold=self._compress_threshold, encryption_key=self._encryption_key))

    async def recv(self) -> Message:
        if self._closed:
            msg = "Connection closed by remote host"
            raise ConnectionError(msg)
        raw = await self._recv_raw()
        return decode(Buffer(raw), encryption_key=self._encryption_key)

    async def close(self) -> None:
        if not self._closed:
            await self._close_impl()
            self._closed = True

    async def listen(self) -> AsyncIterator[Message]:
        """Async iterator over incoming messages."""
        while not self._closed:
            try:
                yield await self.recv()
            except (ConnectionError, RuntimeError):
                break

    async def __aenter__(self) -> "Transport":
        """Async enter."""
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit."""
        await self.close()

    @abstractmethod
    async def _open(self) -> None:
        ...

    @abstractmethod
    async def _send_raw(self, raw: bytes) -> None:
        ...

    @abstractmethod
    async def _recv_raw(self) -> bytes:
        ...

    @abstractmethod
    async def _close_impl(self) -> None:
        ...

    @abstractmethod
    def host(self) -> str:
        ...

    @abstractmethod
    def port(self) -> int:
        ...


class Acceptor(Protocol):
    """Async listener for server."""

    async def __aiter__(self) -> AsyncIterator[Transport]: ...  # noqa: D105
