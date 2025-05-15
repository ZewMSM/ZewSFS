import asyncio
import logging
from asyncio import AbstractServer, IncompleteReadError, StreamReader, StreamWriter, get_running_loop, start_server
from collections.abc import AsyncIterator

from sfs2x.protocol import Flag
from sfs2x.transport import Acceptor, Transport

logger = logging.getLogger("SFS2X/TCPTransport")


class TCPTransport(Transport):
    """SmartFox Transport realisation with Async Streams."""

    def __init__(self, host: str, port: int, compress_threshold: int | None = None, encryption_key: bytes | None = None) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._reader: StreamReader | None = None
        self._writer: StreamWriter | None = None
        self._encryption_key = encryption_key
        self._compress_threshold = compress_threshold

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    async def _open(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        logger.info("Opened connection to %s:%s", self._host, self._port)

    async def _send_raw(self, raw: bytes) -> None:
        if not self._writer:
            msg = "Connection closed by remote host"
            raise ConnectionError(msg)

        self._writer.write(raw)
        await self._writer.drain()
        logger.info("Sent %s bytes", {len(raw)})

    async def _recv_raw(self) -> bytes:
        if not self._reader:
            msg = "Connection closed by remote host"
            raise ConnectionError(msg)

        try:
            _flags = await self._reader.readexactly(1)
            flags = Flag(_flags[0])
            if not flags & Flag.BINARY:
                msg = "Invalid packet type"
                raise RuntimeWarning(msg)

            len_bytes = await self._reader.readexactly(2)
            if flags & Flag.BIG_SIZE:
                len_bytes += await self._reader.readexactly(2)

            length = int.from_bytes(len_bytes, byteorder="big", signed=False)
            body = await self._reader.readexactly(length)
        except IncompleteReadError as e:
            msg = "Connection closed by remote host"
            raise ConnectionError(msg) from e

        logger.info("Received %s bytes from %s:%s", length, self._host, self._port)

        return _flags + len_bytes + body

    async def _close_impl(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        logger.info("Closed connection to %s:%s", self._host, self._port)


class TCPAcceptor(Acceptor):
    """Server-Side implementation of the TCP Acceptor."""

    def __init__(self, host: str, port: int, compress_threshold: int | None = None, encryption_key: bytes | None = None) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._server: AbstractServer | None = None
        self._compress_threshold = compress_threshold
        self._encryption_key = encryption_key

    async def __aiter__(self) -> AsyncIterator[Transport]:  # type: ignore  # noqa: PGH003
        """Iterate all new connections."""
        loop = get_running_loop()
        self._server = await start_server(self._on_conn, self._host, self._port)
        logger.info("Started server on %s:%s", self._host, self._port)

        self._queue: asyncio.Queue[TCPTransport] = asyncio.Queue()

        async def producer() -> None:
            async with self._server:  # type: ignore  # noqa: PGH003
                await self._server.serve_forever()  # type: ignore  # noqa: PGH003

        loop.create_task(producer())  # noqa: RUF006

        try:
            while True:
                yield await self._queue.get()
        finally:
            self._server.close()

    async def _on_conn(self, reader: StreamReader, writer: StreamWriter) -> None:
        host, port = writer.get_extra_info("peername")
        logger.info("Connection from %s:%s", host, port)
        transport = TCPTransport(host, port)
        transport._reader = reader  # noqa: SLF001
        transport._writer = writer  # noqa: SLF001
        transport._closed = False  # noqa: SLF001
        transport._encryption_key = self._encryption_key  # noqa: SLF001
        transport._compress_threshold = self._compress_threshold  # noqa: SLF001
        await self._queue.put(transport)
