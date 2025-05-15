from urllib.parse import urlparse

from sfs2x.transport import Acceptor, TCPAcceptor, TCPTransport, Transport


def client_from_url(url: str) -> Transport:
    """
    Create transport from url.

    * ``tcp://host:port``
    * ``ws://host:port/path``
    * ``http://host:port/path
    """
    u = urlparse(url)
    scheme = u.scheme.lower()

    if scheme == "tcp":
        port = u.port or 9933
        return TCPTransport(u.hostname or "localhost", port)
    raise NotImplementedError


def server_from_url(url: str) -> TCPAcceptor | Acceptor:
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
        return TCPAcceptor(u.hostname or "localhost", port)
    raise NotImplementedError
