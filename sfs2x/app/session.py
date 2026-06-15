"""Per-connection session objects passed into handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sfs2x.app.models import SFSModel
from sfs2x.app.responses import (
    ExtensionRequest,
    ExtensionResponse,
    Reply,
    SystemRequest,
    SystemResponse,
)
from sfs2x.protocol import Message
from sfs2x.transport import Transport

if TYPE_CHECKING:
    from sfs2x.app.client import SFSClient
    from sfs2x.app.server import SFSServer


def _to_message(item: Message | SFSModel | Reply) -> Message:
    if isinstance(item, Message):
        return item
    if isinstance(item, Reply):
        item = item.model
    if isinstance(item, (SystemRequest, SystemResponse, ExtensionRequest, ExtensionResponse)):
        return item.to_message()
    msg = f"Cannot send {type(item).__name__} — must be Message, request/response model, or Reply"
    raise TypeError(msg)


class ClientSession:
    """Wraps the client-side transport for handler injection."""

    __slots__ = ("client", "state", "transport")

    def __init__(self, transport: Transport, client: SFSClient) -> None:
        self.transport = transport
        self.client = client
        self.state: dict[str, Any] = {}

    async def send(self, item: Message | SFSModel | Reply) -> None:
        await self.transport.send(_to_message(item))

    @property
    def closed(self) -> bool:
        return self.transport.closed


class ServerSession:
    """Wraps one accepted client connection."""

    __slots__ = ("server", "state", "transport", "user_id", "username", "zone")

    def __init__(self, transport: Transport, server: SFSServer) -> None:
        self.transport = transport
        self.server = server
        self.state: dict[str, Any] = {}
        self.user_id: int | None = None
        self.username: str | None = None
        self.zone: str | None = None

    async def send(self, item: Message | SFSModel | Reply) -> None:
        await self.transport.send(_to_message(item))

    async def kick(self) -> None:
        await self.transport.close()

    @property
    def host(self) -> str:
        return self.transport.host

    @property
    def port(self) -> int:
        return self.transport.port

    @property
    def closed(self) -> bool:
        return self.transport.closed
