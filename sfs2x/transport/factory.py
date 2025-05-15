from urllib.parse import urlparse

from sfs2x.transport import Acceptor, TCPAcceptor, TCPTransport, Transport


def client_from_url(url: str, *, compress_threshold: int | None = None, encryption_key: bytes | None = None) -> Transport:
    """
    Create transport from url.

    * ``tcp://host:port``
    * ``ws://host:port/path``
    * ``http://host:port/path
    """
    u = urlparse(url)
    scheme = (u.scheme or "tcp").lower()

    if scheme == "tcp":
        port = u.port or 9933
        return TCPTransport(u.hostname or "localhost", port, compress_threshold=compress_threshold, encryption_key=encryption_key)
    raise NotImplementedError


def server_from_url(url: str, compress_threshold: int | None = None, encryption_key: bytes | None = None) -> TCPAcceptor | Acceptor:
    """
    Create acceptor from url.

    * ``tcp://host:port``
    * ``ws://host:port/path``
    * ``http://host:port/path
    """
    u = urlparse(url)
    scheme = u.scheme.lower()

    if scheme == "tcp":
        port = u.port or 9933
        return TCPAcceptor(u.hostname or "localhost", port, compress_threshold=compress_threshold, encryption_key=encryption_key)
    raise NotImplementedError
