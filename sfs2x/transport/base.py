from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Protocol

from sfs2x.core import Buffer
from sfs2x.protocol import Message, decode, encode
from sfs2x.transport.exceptions import ConnectionClosed


class Transport(ABC):
    """Abstract base class for transports."""

    _closed: bool

    def __init__(self) -> None:
        self._closed = True

    async def open(self) -> None:
        await self._open()
        self._closed = False
        return self

    async def send(self, msg: Message) -> None:
        if self._closed:
            raise ConnectionClosed
        await self._send_raw(encode(msg))

    async def recv(self) -> Message:
        if self._closed:
            raise ConnectionClosed
        raw = await self._recv_raw()
        return decode(Buffer(raw))

    async def close(self):
        if not self._closed:
            await self._close_impl()
            self._closed = True

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


class Acceptor(Protocol):
    """Async listener for server."""

    async def __aiter__(self) -> AsyncIterator[Transport]: ...  # noqa: D105
