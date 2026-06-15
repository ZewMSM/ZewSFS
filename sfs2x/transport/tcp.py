import asyncio
import contextlib
import logging
from asyncio import AbstractServer, IncompleteReadError, StreamReader, StreamWriter
from typing import Self

from sfs2x.protocol import Flag
from sfs2x.transport.base import Acceptor, Transport, TransportClosedError

logger = logging.getLogger("SFS2X/TCPTransport")


class TCPTransport(Transport):
    """SFS2X transport over raw TCP using asyncio streams."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        super().__init__(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None

    @classmethod
    def _from_streams(
        cls,
        reader: StreamReader,
        writer: StreamWriter,
        *,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> Self:
        host, port = writer.get_extra_info("peername")[:2]
        inst = cls(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
        inst._reader = reader
        inst._writer = writer
        inst._opened = True
        return inst

    async def _open(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        logger.info("Opened connection to %s:%s", self.host, self.port)

    async def _send_raw(self, raw: bytes) -> None:
        if self._writer is None:
            raise TransportClosedError("Connection closed by remote host")
        self._writer.write(raw)
        await self._writer.drain()
        logger.info("Sent %s bytes", len(raw))

    async def _recv_raw(self) -> bytes:
        if self._reader is None:
            raise TransportClosedError("Connection closed by remote host")
        try:
            flag_byte = await self._reader.readexactly(1)
            flags = Flag(flag_byte[0])
            if not flags & Flag.BINARY:
                raise RuntimeError("Invalid packet type")

            len_bytes = await self._reader.readexactly(2)
            if flags & Flag.BIG_SIZE:
                len_bytes += await self._reader.readexactly(2)

            length = int.from_bytes(len_bytes, byteorder="big", signed=False)
            body = await self._reader.readexactly(length)
        except IncompleteReadError as e:
            raise TransportClosedError("Connection closed by remote host") from e

        logger.info("Received %s bytes from %s:%s", length, self.host, self.port)
        return flag_byte + len_bytes + body

    async def _close_impl(self) -> None:
        if self._writer:
            self._writer.close()
            with contextlib.suppress(ConnectionError):
                await self._writer.wait_closed()
        logger.info("Closed connection to %s:%s", self.host, self.port)


class TCPAcceptor(Acceptor):
    """Server-side TCP acceptor.

    Each accepted connection is wrapped in a :class:`TCPTransport` ready
    to ``send`` / ``recv`` / ``listen`` SFS2X messages.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        compress_threshold: int | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        super().__init__(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
        self._server: AbstractServer | None = None

    async def _start(self) -> None:
        self._server = await asyncio.start_server(self._on_conn, self.host, self.port)
        logger.info("Started TCP server on %s:%s", self.host, self.port)

    async def _close(self) -> None:
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
        logger.info("Stopped TCP server on %s:%s", self.host, self.port)

    async def _on_conn(self, reader: StreamReader, writer: StreamWriter) -> None:
        transport = TCPTransport._from_streams(
            reader,
            writer,
            compress_threshold=self._compress_threshold,
            encryption_key=self._encryption_key,
        )
        logger.info("Connection from %s:%s", transport.host, transport.port)
        await self._queue.put(transport)
