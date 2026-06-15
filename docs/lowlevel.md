# Low-level reference

The high-level API (`SFSClient` / `SFSServer` / `SFSModel`) covers almost
every use case. When you need to talk to the wire directly — interoperate
with a custom SFS dialect, ship raw bytes, or write your own
acceptor — this page documents the building blocks underneath.

- [`sfs2x.core`](#sfs2xcore) — typed primitives and `SFSObject`/`SFSArray`.
- [`sfs2x.protocol`](#sfs2xprotocol) — `Message`, the wire codec, compression and encryption.
- [`sfs2x.transport`](#sfs2xtransport) — `Transport`/`Acceptor`, TCP and WebSocket implementations.

---

## `sfs2x.core`

The data model. Every value that travels on the wire is a `Field`
subclass: a typed wrapper around a raw Python value that knows how to
serialise/deserialise itself.

### Primitives & arrays

```python
from sfs2x.core import (
    Bool, Byte, Short, Int, Long, Float, Double, UtfString, Text,
    BoolArray, ByteArray, ShortArray, IntArray, LongArray,
    FloatArray, DoubleArray, UtfStringArray,
)

i = Int(42)            # i.value == 42, i.type_code is TypeCode.INT
arr = IntArray([1, 2]) # arr.value == [1, 2]
```

### `SFSObject` / `SFSArray`

```python
from sfs2x.core import SFSObject, SFSArray, Int, UtfString

obj = SFSObject()
obj.put_int("score", 1200) \
   .put_utf_string("name", "Zewsic") \
   .put_double_array("history", [3.14, -4.5])

# Declarative form — raw dicts/lists are auto-wrapped:
obj = SFSObject({
    "name":  UtfString("Zewsic"),
    "score": Int(2022),
    "items": [UtfString("Sword"), UtfString("Shield")],
    "object": {"some": UtfString("thing")},
})

# Access (auto-unwraps Field → raw Python value):
obj["score"]              # 1200
obj.get("missing", 0)     # 0
obj.value["score"]        # Int(1200) — the actual Field instance
```

### Round-tripping bytes

```python
from sfs2x.core import decode, SFSObject, Int

obj = SFSObject({"example": Int(42)})
raw = obj.to_bytes()
restored: SFSObject = decode(raw)
print(restored.get("example"))  # 42
```

---

## `sfs2x.protocol`

### `Message`

```python
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject, UtfString

msg = Message(
    controller=ControllerID.SYSTEM,
    action=SysAction.PUBLIC_MESSAGE,
    payload=SFSObject({"text": UtfString("Hello!")}),
)

# Extension calls have a convenience factory:
ext = Message.extension(
    "myCmd",
    SFSObject({"x": UtfString("y")}),
    request_id=42,
)
```

### Encode / decode

```python
from sfs2x.protocol import encode, decode

packet = encode(
    msg,
    compress_threshold=512,         # zlib-compress payloads > 512 bytes
    encryption_key=b"my_secret_16byte",  # AES-128-CBC
)
back = decode(packet, encryption_key=b"my_secret_16byte")
```

### Flag bits

| Bit          | Meaning                          |
| ------------ | -------------------------------- |
| `BINARY`     | Always set on SFS2X binary packets |
| `COMPRESSED` | `zlib` compression applied       |
| `ENCRYPTED`  | AES-128-CBC encryption applied   |
| `BIG_SIZE`   | Payload length > 65535 bytes     |
| `BLUEBOX`    | Reserved (BlueBox transport)     |

### `AESCipher`

`AES-128-CBC` with random IV per encryption, PKCS#7 padding. Requires
`pycryptodome`. Key must be exactly 16 bytes.

```python
from sfs2x.protocol import AESCipher
c = AESCipher(b"my_secret_16byte")
encrypted = c.encrypt(b"hello")
plain = c.decrypt(encrypted)
```

### `ControllerID` / `SysAction`

See [protocol.md](protocol.md) for the full enum tables and SFS2X
payload-key conventions (`c`/`a`/`p`/`r`/`zn`/`un`/…).

---

## `sfs2x.transport`

### `Transport` lifecycle

```python
from sfs2x.transport import client_from_url

async with client_from_url("tcp://localhost:9933") as t:
    await t.send(msg)
    reply = await t.recv()
    async for m in t.listen():
        ...
```

### `Acceptor` lifecycle

```python
from sfs2x.transport import server_from_url

async with server_from_url("tcp://0.0.0.0:9933") as acc:
    async for client in acc:
        asyncio.create_task(handle(client))
```

### URL → transport mapping

| Scheme  | Client             | Server               | Default port | Default path           |
| ------- | ------------------ | -------------------- | ------------ | ---------------------- |
| `tcp`   | `TCPTransport`     | `TCPAcceptor`        | `9933`       | —                      |
| `ws`    | `WSTransport`      | `WSAcceptor`         | `8080`       | `/BlueBox/websocket`   |
| `wss`   | `WSTransport(TLS)` | `WSAcceptor(TLS)`    | `443`        | `/BlueBox/websocket`   |

Pass `ssl=ssl.SSLContext(...)` to the factory for `wss://`.

### Concrete classes

| Symbol                | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `Transport`           | Abstract base for client-side connections.                |
| `Acceptor`            | Abstract base for server-side acceptors.                  |
| `TransportClosedError`| Raised when `send`/`recv` is attempted on a closed transport. |
| `TCPTransport`        | TCP client (`asyncio.open_connection`).                   |
| `TCPAcceptor`         | TCP server (`asyncio.start_server`).                      |
| `WSTransport`         | WebSocket client (`ws://` / `wss://`).                    |
| `WSAcceptor`          | WebSocket server (default path `/BlueBox/websocket`).     |
| `client_from_url`     | URL → `Transport`.                                        |
| `server_from_url`     | URL → `Acceptor`.                                         |
