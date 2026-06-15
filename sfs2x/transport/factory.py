from urllib.parse import urlparse

from sfs2x.transport.base import Acceptor, Transport
from sfs2x.transport.tcp import TCPAcceptor, TCPTransport
from sfs2x.transport.ws import DEFAULT_WS_PATH, WSAcceptor, WSTransport

_DEFAULT_PORTS = {"tcp": 9933, "ws": 8080, "wss": 443}


def _parse(url: str) -> tuple[str, str, int, str]:
    """Return ``(scheme, host, port, path)`` from ``url``."""
    u = urlparse(url)
    scheme = (u.scheme or "tcp").lower()
    if scheme not in _DEFAULT_PORTS:
        raise ValueError(f"Unsupported scheme: {scheme!r}. Expected one of {sorted(_DEFAULT_PORTS)}.")
    host = u.hostname or "localhost"
    port = u.port or _DEFAULT_PORTS[scheme]
    path = u.path or DEFAULT_WS_PATH
    return scheme, host, port, path


def client_from_url(
    url: str,
    *,
    compress_threshold: int | None = None,
    encryption_key: bytes | None = None,
    ssl: object | None = None,
) -> Transport:
    """Build a client transport from a URL.

    Supported schemes:

    * ``tcp://host[:port]`` — raw SFS2X TCP socket (default port ``9933``).
    * ``ws://host[:port][/path]`` — SFS2X over WebSocket (default port
      ``8080``, default path ``/BlueBox/websocket``).
    * ``wss://host[:port][/path]`` — SFS2X over secure WebSocket (default
      port ``443``). Pass an ``ssl.SSLContext`` via ``ssl=...`` if needed.
    """
    scheme, host, port, path = _parse(url)
    if scheme == "tcp":
        return TCPTransport(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
    return WSTransport(
        host,
        port,
        path=path,
        secure=scheme == "wss",
        ssl=ssl,  # type: ignore[arg-type]
        compress_threshold=compress_threshold,
        encryption_key=encryption_key,
    )


def server_from_url(
    url: str,
    *,
    compress_threshold: int | None = None,
    encryption_key: bytes | None = None,
    ssl: object | None = None,
) -> Acceptor:
    """Build a server-side acceptor from a URL.

    See :func:`client_from_url` for the supported schemes.
    """
    scheme, host, port, path = _parse(url)
    if scheme == "tcp":
        return TCPAcceptor(
            host,
            port,
            compress_threshold=compress_threshold,
            encryption_key=encryption_key,
        )
    return WSAcceptor(
        host,
        port,
        path=path,
        ssl=ssl,  # type: ignore[arg-type]
        compress_threshold=compress_threshold,
        encryption_key=encryption_key,
    )
