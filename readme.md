# ZewSFS

**ZewSFS** is a Python implementation of the
[SmartFoxServer 2X (SFS2X)](https://www.smartfoxserver.com/) binary protocol —
both the client and the server side. It ships the rich SFS2X data model
(`SFSObject`, `SFSArray`, typed fields), a message codec with optional
compression and AES encryption, and pluggable transports for raw TCP and
WebSockets (the standard binary sub-protocol introduced in SFS2X v2.13).

```
                    ┌──────────────────────────┐
                    │        Application       │
                    └────────────┬─────────────┘
                       Message(controller, action, payload)
                    ┌────────────┴─────────────┐
                    │  sfs2x.protocol  (codec) │   ← compression, AES
                    └────────────┬─────────────┘
                            on-wire bytes
                    ┌────────────┴─────────────┐
                    │ sfs2x.transport (TCP/WS) │
                    └──────────────────────────┘
```

## Contents

- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
    - [TCP client](#tcp-client)
    - [TCP server](#tcp-server)
    - [WebSocket client](#websocket-client)
    - [WebSocket server](#websocket-server)
- [Modules overview](#modules-overview)
- [Working with `SFSObject` / `SFSArray`](#working-with-sfsobject--sfsarray)
- [Compression and encryption](#compression-and-encryption)
- [URL → transport mapping](#url--transport-mapping)
- [Status and roadmap](#status-and-roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Core data model** — `SFSObject`, `SFSArray` and all the typed primitives
  (`Bool`, `Byte`, `Short`, `Int`, `Long`, `Float`, `Double`, `UtfString`,
  `Text`, and their array variants) with byte-perfect round-trip encoding.
- **Protocol codec** — `Message ↔ bytes` with optional `zlib` compression
  over a configurable threshold and optional AES-128-CBC encryption.
- **TCP transport** — async client (`TCPTransport`) and acceptor
  (`TCPAcceptor`) built on `asyncio.open_connection` /
  `asyncio.start_server`.
- **WebSocket transport** — async client (`WSTransport`) and acceptor
  (`WSAcceptor`) speaking SFS2X v2.13+'s binary WebSocket sub-protocol over
  `ws://` and `wss://`. Each WebSocket binary frame carries one complete
  SFS2X packet so the codec is shared with the TCP transport.
- **URL factories** — `client_from_url("tcp://...")` /
  `server_from_url("ws://.../BlueBox/websocket")` pick the right transport
  for you.

## Installation

```bash
pip install sfs2x          # or: uv pip install sfs2x
```

`websockets` is pulled in as a hard dependency. AES encryption is optional
and requires PyCryptodome:

```bash
pip install sfs2x[crypto]  # or: pip install pycryptodome
```

## Quick start

### TCP client

```python
import asyncio
from sfs2x.transport import client_from_url
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject


async def main() -> None:
    async with client_from_url("tcp://localhost:9933") as client:
        payload = SFSObject().put_utf_string("message", "Hello from ZewSFS!")
        await client.send(Message(
            controller=ControllerID.SYSTEM,
            action=SysAction.PUBLIC_MESSAGE,
            payload=payload,
        ))
        print("Reply:", await client.recv())


asyncio.run(main())
```

### TCP server

```python
import asyncio
from sfs2x.transport import server_from_url, Transport
from sfs2x.protocol import Message
from sfs2x.core import SFSObject


async def handle(client: Transport) -> None:
    async for msg in client.listen():
        await client.send(Message(
            controller=msg.controller,
            action=msg.action,
            payload=SFSObject({"echo": msg.payload}),
        ))


async def main() -> None:
    async with server_from_url("tcp://0.0.0.0:9933") as acceptor:
        async for client in acceptor:
            print(f"Client connected: {client.host}:{client.port}")
            asyncio.create_task(handle(client))


asyncio.run(main())
```

### WebSocket client

The default SFS2X WebSocket endpoint path is `/BlueBox/websocket`.

```python
import asyncio
from sfs2x.transport import client_from_url
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject


async def main() -> None:
    url = "ws://localhost:8080/BlueBox/websocket"
    async with client_from_url(url) as client:
        await client.send(Message(
            controller=ControllerID.SYSTEM,
            action=SysAction.HANDSHAKE,
            payload=SFSObject()
                .put_utf_string("api", "1.7.3")
                .put_utf_string("cl", "Python/ZewSFS")
                .put_bool("bin", True),
        ))
        print("Handshake reply:", await client.recv())


asyncio.run(main())
```

For TLS, point the client at `wss://...` and (optionally) pass an
`ssl.SSLContext`:

```python
import ssl
client_from_url("wss://game.example.com/BlueBox/websocket", ssl=ssl.create_default_context())
```

### WebSocket server

```python
import asyncio
from sfs2x.transport import server_from_url, Transport
from sfs2x.protocol import Message


async def handle(client: Transport) -> None:
    async for msg in client.listen():
        await client.send(msg)  # echo


async def main() -> None:
    async with server_from_url("ws://0.0.0.0:8080/BlueBox/websocket") as acceptor:
        async for client in acceptor:
            print(f"WS client connected: {client.host}:{client.port}")
            asyncio.create_task(handle(client))


asyncio.run(main())
```

## Modules overview

### `sfs2x.core`

Low-level data model and binary encoding/decoding:

- **Primitives**: `Bool`, `Byte`, `Short`, `Int`, `Long`, `Float`, `Double`,
  `UtfString`, `Text`.
- **Arrays**: `BoolArray`, `ByteArray`, `ShortArray`, `IntArray`,
  `LongArray`, `FloatArray`, `DoubleArray`, `UtfStringArray`.
- **Containers**: `SFSObject` (keyed) and `SFSArray` (ordered).
- **Helpers**: `Buffer` (byte cursor), `decode` / `register` (raw
  bytes ↔ typed values).

### `sfs2x.protocol`

Wire-format codec:

- `Message(controller, action, payload)` — high-level packet.
- `Flag` — header bit flags (`BINARY`, `COMPRESSED`, `ENCRYPTED`,
  `BIG_SIZE`, `BLUEBOX`).
- `encode(msg, *, compress_threshold, encryption_key)` and
  `decode(buf_or_bytes, *, encryption_key)`.
- `AESCipher` — AES-128-CBC helper (requires `pycryptodome`).
- `ControllerID`, `SysAction` — protocol-level enums.

### `sfs2x.transport`

Connection-level abstractions and concrete implementations:

| Symbol                | Purpose                                       |
| --------------------- | --------------------------------------------- |
| `Transport`           | Abstract base for client-side connections.    |
| `Acceptor`            | Abstract base for server-side acceptors.      |
| `TransportClosedError`| Raised when the connection is no longer open. |
| `TCPTransport`        | TCP client via `asyncio.open_connection`.     |
| `TCPAcceptor`         | TCP server via `asyncio.start_server`.        |
| `WSTransport`         | WebSocket client (`ws://` / `wss://`).        |
| `WSAcceptor`          | WebSocket server (default path `/BlueBox/websocket`). |
| `client_from_url`     | URL → `Transport`.                            |
| `server_from_url`     | URL → `Acceptor`.                             |

A `Transport` lifecycle is:

```python
async with client_from_url(url) as t:
    await t.send(msg)
    reply = await t.recv()
    async for msg in t.listen():
        ...
```

An `Acceptor` lifecycle mirrors it:

```python
async with server_from_url(url) as acceptor:
    async for client in acceptor:
        ...
```

## Working with `SFSObject` / `SFSArray`

**Fluent / imperative**:

```python
from sfs2x.core import SFSObject, SFSArray

obj = SFSObject()
obj.put_int("score", 1200) \
   .put_double_array("history", [3.14, -4.5, 2.7]) \
   .put_bool("isAdmin", True)

arr = SFSArray()
arr.add_utf_string("item1").add_utf_string("item2")
obj["items"] = arr
```

**Declarative**:

```python
from sfs2x.core import UtfString, Int, SFSObject

obj = SFSObject({
    "name": UtfString("Zewsic"),
    "score": Int(2022),
    "items": [
        UtfString("Sword"),
        UtfString("Shield"),
        SFSObject({"key": UtfString("value")}),
    ],
    "object": {"some": UtfString("thing")},
})
```

**Round-tripping bytes**:

```python
from sfs2x.core import decode, SFSObject, Int

obj = SFSObject({"example": Int(42)})
raw = obj.to_bytes()
restored: SFSObject = decode(raw)
print(restored.get("example"))  # 42
```

## Compression and encryption

Both transports accept the same kwargs and forward them straight to the
codec:

```python
from sfs2x.transport import client_from_url

client = client_from_url(
    "ws://game.example.com/BlueBox/websocket",
    compress_threshold=512,       # zlib-compress payloads > 512 bytes
    encryption_key=b"my_secret_16byte",  # AES-128-CBC
)
```

Or, using the codec directly:

```python
from sfs2x.protocol import Message, encode, decode, ControllerID
from sfs2x.core import SFSObject, UtfString

msg = Message(controller=ControllerID.EXTENSION, action=18,
              payload={"secret": UtfString("HideMe")})
packet = encode(msg, compress_threshold=512, encryption_key=b"my_secret_16byte")
restored = decode(packet, encryption_key=b"my_secret_16byte")
```

## URL → transport mapping

| Scheme  | Client             | Server               | Default port | Default path           |
| ------- | ------------------ | -------------------- | ------------ | ---------------------- |
| `tcp`   | `TCPTransport`     | `TCPAcceptor`        | `9933`       | —                      |
| `ws`    | `WSTransport`      | `WSAcceptor`         | `8080`       | `/BlueBox/websocket`   |
| `wss`   | `WSTransport(TLS)` | `WSAcceptor(TLS)`    | `443`        | `/BlueBox/websocket`   |

Path defaults are the SFS2X conventions — set an explicit path in the URL
to override (e.g. `ws://host:8080/custom/socket`). For `wss://`, pass
`ssl=ssl.SSLContext(...)` to the factory.

## Status and roadmap

This library covers the **binary protocol** and the **two main transports**
(TCP and WebSocket). It is intended as a low-level building block — there
is no high-level SmartFox-style session yet.

Planned / in development:

- `SFSClient` / `SFSServer` high-level wrappers (handshake, login, room and
  user variables, extension call helpers).
- BlueBox HTTP tunneling transport.
- UDP transport for unreliable high-frequency channels.

Contributions and protocol-edge bug reports are very welcome.

## Contributing

Issues and pull requests are tracked on
[GitHub](https://github.com/zewmsm/ZewSFS). Run the tests with:

```bash
pip install -e . websockets pytest pytest-asyncio pycryptodome
pytest
```

## License

MIT — see [LICENSE](LICENSE).
