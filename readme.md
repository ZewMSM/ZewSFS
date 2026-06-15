# ZewSFS

**High-level SmartFoxServer 2X client & server for Python.**

Decorator-driven handlers, typed request/response models, and async
client/server lifecycle on top of a complete pure-Python
SmartFoxServer 2X (SFS2X) binary protocol stack — TCP and WebSocket,
optional zlib compression and AES-128 encryption.

```python
from sfs2x import SFSClient, ExtensionRequest, ExtensionResponse, field
from sfs2x.app import Int, UtfString


class PingRequest(ExtensionRequest, command="ping"):
    n: Int = field("n")


class PongResponse(ExtensionResponse, command="ping"):
    n: Int = field("n")
    name: UtfString = field("name")


client = SFSClient("tcp://localhost:9933")


@client.on_extension(command="ping")
async def on_pong(reply: PongResponse):
    print(f"pong: {reply.n} from {reply.name}")


async with client:
    await client.handshake()
    await client.login(zone="MyZone", username="alice")
    await client.call_extension("ping", PingRequest(n=42))
    await client.run_forever()
```

## Features

- **Decorator handlers** — `@client.on_login()`, `@server.on_handshake()`,
  `@server.on_extension(command="…")`, `@client.on_message()` catch-all,
  plus `on_connect` / `on_disconnect` / `on_error` lifecycle hooks.
- **Typed models** — annotate fields with SFS types (`UtfString`, `Int`,
  `Long`, …) and the model serialises/parses against `SFSObject`
  automatically. Nested models supported.
- **`raise` to reply** — `raise PongResponse(n=42)` sends the answer.
  `return PongResponse(...)` works too. `raise Reply(model)` if you want
  the explicit wrapper.
- **Union dispatch** — handlers can declare
  `req: LoginResponse | LoginErrorResponse`; the first matching schema
  wins.
- **Built-in system models** — `HandshakeRequest`, `LoginRequest`,
  `LogoutRequest`, `PingPongRequest` and their responses come ready
  to use.
- **Sessions** — server handlers get a `ServerSession` per connection
  with `state: dict`, `zone`/`username`/`user_id` slots, `send()` and
  `kick()`.
- **TCP & WebSocket** transports with the same API. Optional `zlib`
  compression and AES-128-CBC encryption.

## Installation

```bash
pip install sfs2x          # or: uv pip install sfs2x
```

AES encryption requires PyCryptodome:

```bash
pip install sfs2x[crypto]
```

## Quick start

### Client

```python
import asyncio
from sfs2x import SFSClient, ExtensionRequest, ExtensionResponse, field
from sfs2x import LoginErrorResponse, LoginResponse
from sfs2x.app import Int, UtfString


class JoinGameRequest(ExtensionRequest, command="joinGame"):
    room: UtfString = field("r")


class JoinGameResponse(ExtensionResponse, command="joinGame"):
    game_id: Int = field("gid")
    seat: Int = field("s")


client = SFSClient("tcp://localhost:9933")


@client.on_login()
async def on_login(reply: LoginErrorResponse | LoginResponse):
    if isinstance(reply, LoginErrorResponse):
        print(f"login failed: {reply.error_message}")
        return
    print(f"logged in as {reply.username} (id={reply.user_id})")
    await client.call_extension("joinGame", JoinGameRequest(room="main"))


@client.on_extension(command="joinGame")
async def on_joined(reply: JoinGameResponse):
    print(f"joined game {reply.game_id}, seat {reply.seat}")


async def main():
    async with client:
        await client.handshake()
        await client.login(zone="MyZone", username="alice", password="secret")
        await client.run_forever()


asyncio.run(main())
```

### Server

```python
import asyncio
from sfs2x import (
    SFSServer, LoginRequest, LoginResponse, LoginErrorResponse,
    ExtensionRequest, ExtensionResponse, ServerSession, field,
)
from sfs2x.app import Int, UtfString


class JoinGameRequest(ExtensionRequest, command="joinGame"):
    room: UtfString = field("r")


class JoinGameResponse(ExtensionResponse, command="joinGame"):
    game_id: Int = field("gid")
    seat: Int = field("s")


server = SFSServer("tcp://0.0.0.0:9933")


@server.on_login()
async def on_login(req: LoginRequest, session: ServerSession):
    if req.password != "secret":
        raise LoginErrorResponse(error_code=1, error_message="wrong password")
    session.zone = req.zone
    session.username = req.username
    session.user_id = 42
    raise LoginResponse(zone=req.zone, username=req.username, user_id=42)


@server.on_extension(command="joinGame")
async def on_join(req: JoinGameRequest, session: ServerSession):
    print(f"{session.username} joining {req.room}")
    raise JoinGameResponse(game_id=1, seat=3)


asyncio.run(server.serve_forever())
```

## Defining models

A model is a class whose annotations are SFS types — never plain Python
types. The annotation tells the wire format what to encode; the attribute
itself stores the raw Python value, so the model behaves like a dataclass
at runtime.

```python
from sfs2x import SFSModel, field
from sfs2x.app import UtfString, Int, Long, SFSObject, UtfStringArray


class PlayerProfile(SFSModel):
    name:      UtfString       = field("n")
    score:     Long            = field("s")        # 64-bit on the wire
    level:     Int             = field("lvl")
    nicknames: UtfStringArray  = field("alts")     # list of strings
    extras:    SFSObject       = field("x", default_factory=SFSObject)
    bio:       UtfString | None = field("bio", default=None)   # optional


p = PlayerProfile(name="alice", score=99999, level=12, nicknames=["a", "al"])
obj = p.to_sfs_object()        # → SFSObject ready to send
back = PlayerProfile.from_sfs_object(obj)
assert back == p
```

Nested models work the same way — just use another `SFSModel` subclass
as the annotation:

```python
class Vec2(SFSModel):
    x: Int = field("x")
    y: Int = field("y")


class Move(SFSModel):
    player: UtfString = field("p")
    target: Vec2      = field("t")     # nested SFSObject on the wire
```

For one-off payloads where you don't want a model, declare the field as
`SFSObject` / `SFSArray` and pass them through directly.

## Handler signatures

The dispatcher inspects each handler's signature and injects whatever
you annotate. Pick any subset:

| Annotation                          | What gets injected                          |
|-------------------------------------|----------------------------------------------|
| `Message`                           | the raw `Message` packet                     |
| `SFSObject`                         | extension `"p"` sub-object, or system payload|
| `ServerSession` / `ClientSession`   | the per-connection session                   |
| `SFSClient` / `SFSServer`           | the owning client or server                  |
| `MyModel` (an `SFSModel` subclass)  | the parsed model                             |
| `A \| B` (union of models)          | first candidate that parses successfully     |

```python
@server.on_extension(command="x")
async def h(req: RequestA | RequestB,
            raw: SFSObject,
            session: ServerSession,
            msg: Message):
    if isinstance(req, RequestA):
        ...
```

## Sending responses

Three equivalent forms, pick whichever reads best:

```python
@server.on_extension(command="x")
async def h(req: XRequest):
    raise XResponse(value=1)                # raise the response model

@server.on_extension(command="x")
async def h(req: XRequest):
    return XResponse(value=1)               # or return it

@server.on_extension(command="x")
async def h(req: XRequest, session):
    raise Reply(XResponse(value=1))         # or wrap in Reply
    # equivalent: await session.send(XResponse(value=1))
```

`raise` is convenient because it short-circuits nested logic; the
dispatcher catches it, builds the reply `Message` (echoing the original
extension request id so the peer can correlate), and sends it.

## Built-in system models

| Action            | Request                 | Response                                       |
|-------------------|--------------------------|------------------------------------------------|
| `HANDSHAKE`       | `HandshakeRequest`       | `HandshakeResponse`                            |
| `LOGIN`           | `LoginRequest`           | `LoginResponse` / `LoginErrorResponse`         |
| `LOGOUT`          | `LogoutRequest`          | `LogoutResponse`                               |
| `PING_PONG`       | `PingPongRequest`        | `PingPongResponse`                             |

Convenience helpers on `SFSClient`:

```python
await client.handshake(api="1.7.3", cl="Python/ZewSFS")
await client.login(zone="MyZone", username="alice", password="secret")
await client.logout()
await client.call_extension("cmd", MyRequest(x=1))
```

## WebSocket & TLS

Swap the URL — everything else stays identical.

```python
SFSClient("ws://localhost:8080/BlueBox/websocket")
SFSClient("wss://game.example.com/BlueBox/websocket", ssl=ssl.create_default_context())

SFSServer("ws://0.0.0.0:8080/BlueBox/websocket")
```

The default WebSocket path is `/BlueBox/websocket` (SFS2X v2.13+).

## Compression & encryption

Both transports take the same kwargs and forward them straight to the
codec:

```python
client = SFSClient(
    "ws://game.example.com/BlueBox/websocket",
    compress_threshold=512,                # zlib-compress payloads > 512 bytes
    encryption_key=b"my_secret_16byte",    # AES-128-CBC
)
```

## Going lower-level

For direct access to the wire format — raw `Message`, `encode`/`decode`,
`SFSObject` construction, custom `Transport` implementations — see:

- [`docs/lowlevel.md`](docs/lowlevel.md) — `sfs2x.core`, `sfs2x.protocol`,
  `sfs2x.transport`.
- [`docs/protocol.md`](docs/protocol.md) — `ControllerID` / `SysAction`
  tables, wire envelope, SFS2X payload-key conventions.

All low-level symbols are re-exported from `sfs2x.app`:

```python
from sfs2x.app import Message, SFSObject, encode, decode, client_from_url, ...
```

## Status & roadmap

The high-level API covers handshake, login/logout, ping-pong and
arbitrary extension calls on both TCP and WebSocket. Planned:

- Room and user-variable helpers.
- Request/response correlation for `await client.call_extension(...) -> Response`.
- BlueBox HTTP tunnelling.
- UDP transport for high-frequency channels.

Contributions and protocol-edge bug reports are very welcome.

## Contributing

```bash
pip install -e . websockets pytest pytest-asyncio pycryptodome
pytest
```

Issues and pull requests are tracked on
[GitHub](https://github.com/zewmsm/ZewSFS).

## License

MIT — see [LICENSE](LICENSE).
