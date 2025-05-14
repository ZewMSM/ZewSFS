import asyncio
import logging
from asyncio import AbstractServer, StreamReader, StreamWriter, get_running_loop, start_server
from collections.abc import AsyncIterator

from sfs2x.protocol import Flag
from sfs2x.transport import Acceptor, Transport

logger = logging.getLogger("SFS2X/TCPTransport")


class TCPTransport(Transport):
    """SmartFox Transport realisation with Async Streams."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None

    async def _open(self) -> None:
        self._reader, self.writer = await asyncio.open_connection(self._host, self._port)
        logger.info(f"Opened connection to {self._host}:{self._port}")  # noqa: G004

    async def _send_raw(self, raw: bytes) -> None:
        assert self._writer  # noqa: S101
        self._writer.write(raw)
        await self._writer.drain()
        logger.info(f"Sent {len(raw)} bytes")  # noqa: G004

    async def _recv_raw(self) -> bytes:
        assert self._reader  # noqa: S101

        _flags = await self._reader.readexactly(1)
        flags = Flag(_flags[0])
        assert flags & Flag.BINARY  # noqa: S101

        len_bytes = await self._reader.readexactly(2)
        if flags & Flag.BIG_SIZE:
            len_bytes += await self._reader.readexactly(2)

        length = int.from_bytes(len_bytes, byteorder="big", signed=False)
        body = await self._reader.readexactly(length)

        logger.info(f"Received {length} bytes from {self._host}:{self._port}")  # noqa: G004

        return _flags + len_bytes + body

    async def _close_impl(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        logger.info(f"Closed connection to {self._host}:{self._port}")  # noqa: G004


class TCPAcceptor(Acceptor):
    """Server-Side implementation of the TCP Acceptor."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._server: AbstractServer | None = None

    async def __aiter__(self) -> AsyncIterator[Transport]:
        loop = get_running_loop()
        self._server = await start_server(self._on_conn, self._host, self._port)
        logger.info(f"Started server on {self._host}:{self._port}")  # noqa: G004

        self._queue: asyncio.Queue[TCPTransport] = asyncio.Queue()

        async def producer() -> None:
            async with self._server:
                await self._server.serve_forever()

        loop.create_task(producer())

        try:
            while True:
                yield await self._queue.get()
        finally:
            self._server.close()

    async def _on_conn(self, reader: StreamReader, writer: StreamWriter) -> None:
        host, port = writer.get_extra_info("peername")
        logger.info(f"Connection from {host}:{port}")  # noqa: G004
        transport = TCPTransport(host, port)
        transport._reader = reader
        transport._writer = writer
        transport._closed = False
        await self._queue.put(transport)
