# ZewSFS

**ZewSFS** is a Python-based implementation of the [SmartFoxServer 2X (SFS2X)](https://www.smartfoxserver.com/)
protocol, offering both client and server-side capabilities. This library provides fundamental data types, transport
abstractions (TCP/WebSocket in the future), message encoding/decoding, and extensibility for custom encryption and
compression.

## Table of Contents

- [Features](#features)
- [Installation](#installation)

- [Quick Start](#quick-start)
    - [Client Example](#client-example)
    - [Server Example](#server-example)

- [Modules Overview](#modules-overview)
    - [Core](#core)
    - [Protocol](#protocol)
    - [Transport](#transport)

- [Usage Examples](#usage-examples)
    - [Working with `SFSObject` and `SFSArray`](#working-with-sfsobject-and-sfsarray)
    - [Serialization / Deserialization](#serialization--deserialization)
    - [Encrypted or Compressed Packets](#encrypted-or-compressed-packets)
 
- [Handling Requests](#handling-requests)
    - [Handling Handshake Requests](#handling-handshake-requests)
    - [Handling Extension Requests](#handling-extension-requests)

- [Development Status](#development-status)
- [Contributing](#contributing)
- [License](#license)
- [Todo](#todo)

---

## Features

- **Core**: Rich, low-level data structures (e.g., `SFSObject`, `SFSArray`) mirroring SmartFoxServer object models.
- **Protocol**: Easy-to-use encoding/decoding functions to convert between raw bytes and high-level `Message` objects.
- **Transport**: Ready-made TCP server (via `TCPAcceptor`) and client (`TCPTransport`) for sending and receiving SFS2X
  messages.
- **Encryption**: Optional AES-128-CBC support via [PyCryptodome](https://pypi.org/project/pycryptodome/).

---

## Installation

Install module with **pip** or **uv**

   ```bash
   uv pip install sfs2x
   ```

If you plan to use **encrypted packets**, install PyCryptodome:

   ```bash
   pip install pycryptodome
   ```

---

## Quick Start

> **Note**: These examples describe the server-client for the low-Level transport module. High-level server and client
> modules are currently under development.

### Transport Client Example

```python
import asyncio
from sfs2x.transport.factory import client_from_url
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject


async def run_client():
    async with client_from_url("tcp://localhost:9933") as client:
        payload = SFSObject()
        payload.put_utf_string("message", "Hello from ZewSFS client!")

        await client.send(Message(
            controller=ControllerID.SYSTEM,
            action=SysAction.PUBLIC_MESSAGE,
            payload=payload
        ))

        response = await client.recv()
        print("Response:", response)


if __name__ == "__main__":
    asyncio.run(run_client())
```

### Server Example

```python
import asyncio
from sfs2x.transport import server_from_url, TCPTransport
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject


async def handle_client(client: TCPTransport):
    async for message in client.listen():
        response_payload = SFSObject(message="Hello back from server!")
        
        await client.send(Message(
            controller=ControllerID.SYSTEM,
            action=SysAction.PUBLIC_MESSAGE,
            payload=response_payload
        ))


async def run_server():
    async for client in server_from_url("tcp://localhost:9933"):
        print(f"New client connected: {client.host}:{client.port}")
        asyncio.create_task(handle_client(client))


if __name__ == "__main__":
    asyncio.run(run_server())
```

---

## Modules Overview

### Core

The `core` package provides fundamental data structures and serialization logic:

1. **Fields and Arrays**:
    - `Bool`, `Byte`, `Short`, `Int`, `Long`, `Float`, `Double`, `UtfString`, `Text`
    - `BoolArray`, `ByteArray`, `ShortArray`, `IntArray`, `LongArray`, `FloatArray`, `DoubleArray`, `UtfStringArray`

2. **Containers**:
    - `SFSObject` for key-value pairs
    - `SFSArray` for sequential lists

3. **Utility Classes**:
    - `Buffer` for reading raw bytes
    - `Field` as a base for packable items
    - `registry`, `decode`, and `encode` for bridging raw bytes ↔ SFS data types

### Protocol

The `protocol` package focuses on reading/writing SFS2X-compliant packets:

- **`Message`**: High-level class representing a single SFS2X message with `controller`, `action`, and `payload`.
- **`Flag`**: Enum for packet flags (binary, compressed, encrypted, etc.).
- **`encode` / `decode`**: Convert `Message` ↔ binary packets, optionally using compression and AES encryption.
- **`AESCipher`**: AES-128-CBC encryption/decryption for securing packets (requires PyCryptodome).

### Transport

The `transport` package provides abstractions for client-server communication:

- **`Transport` (abstract)**: Defines the required methods (`open`, `send`, `recv`, `close`) for any transport.
- **`TCPTransport`**: Client-side implementation using asyncio streams (TCP).
- **`TCPAcceptor`**: Server-side implementation using asyncio `start_server` (TCP).
- **`client_from_url` / `server_from_url`**: Factory methods to instantiate a transport from a URL (e.g.,
  `tcp://localhost:9933`).

---

## Usage Examples

### Working with `SFSObject` and `SFSArray`

**Imperative style**:

```python
from sfs2x.core import SFSObject, SFSArray

obj = SFSObject()
obj.put_int("score", 1200)
obj.put_double_array("history", [3.14, -4.5, 2.7]) \
    .put_bool("isAdmin", True)

arr = SFSArray()
arr.add_utf_string("item1")
arr.add_utf_string("item2")

obj["myArray"] = arr
```

**Declarative style**:

```python
from sfs2x.core import UtfString, Int, SFSObject, SFSArray

obj = SFSObject({
    "name": UtfString("Zewsic"),
    "score": Int(2022),
    "items": [
        UtfString("Sword"),
        UtfString("Shield"),
        SFSObject({"key": UtfString("value")})
    ], # SFSArray
    "object": {
        "some": UtfString("Thing")
    } # SFSObject
})
```

**Argument style**:
> **Note**: Added as experiment, unstable.
```python
from sfs2x.core import UtfString, Int, SFSObject, SFSArray

obj = SFSObject(
    username=UtfString("Zewsic"),
    coins=Int(1200)
)
```

### Serialization / Deserialization

```python
from sfs2x.core import decode, SFSObject, Int

# Serialize
obj = SFSObject({"example": Int(42)})
raw_bytes = obj.to_bytes()

# Deserialize
deserialized_obj: SFSObject = decode(raw_bytes)
print(deserialized_obj.get("example"))  # 42
```

### Encrypted or Compressed Packets

When creating or decoding messages, you can specify a threshold for compression and a key for encryption:

```python
from sfs2x.protocol import Message, encode, decode, SysAction, ControllerID
from sfs2x.core import SFSObject, UtfString

encryption_key = b"my_secret_16byte"

# Compress if payload > 512 bytes, encrypt with a 16-byte key
msg = Message(controller=ControllerID.EXTENSION, action=18, payload={"secret": UtfString("HideMe")})
packet = encode(msg, compress_threshold=512, encryption_key=encryption_key)

# Decoding
decoded_msg = decode(packet, encryption_key=encryption_key)
```

## Handling Requests

### Handling Handshake Requests

To perform a handshake, generate a token from the client’s host and send session info in the handshake response.

```python
import asyncio
import hashlib
from sfs2x.transport import server_from_url, TCPTransport
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject

async def handle_client(client: TCPTransport):
    async for message in client.listen():
        if message.action == SysAction.HANDSHAKE:
            token = hashlib.md5(client._host.encode()).hexdigest()

            session_info = SFSObject()
            session_info.put_int("ct", 1000000) # protocol Compression Threshold
            session_info.put_int("ms", 8000000) # max Incoming Request Size
            session_info.put_utf_string("tk", token) # Session Token
            
            await client.send(Message(
                controller=ControllerID.SYSTEM,
                action=SysAction.HANDSHAKE,
                payload=session_info
            ))

async def run_server():
    async for client in server_from_url("tcp://localhost:9933"):
        print(f"New client connected: {client.host}:{client.port}")
        asyncio.create_task(handle_client(client))

if __name__ == "__main__":
    asyncio.run(run_server())
```

### Handling Extension Requests

To handle extension requests, simply parse the incoming payload and check for the command field.

#### Server Example

```python
import asyncio
import time
from sfs2x.transport import server_from_url, TCPTransport
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core import SFSObject, SFSArray

async def send_extension_response(client, cmd, params):
    ext_resp = SFSObject()
    ext_resp.put_utf_string("c", cmd)
    ext_resp.put_int("r", -1)
    ext_resp.put_sfs_object("p", params)

    await client.send(Message(
        controller=ControllerID.EXTENSION,
        action=12,
        payload=ext_resp
    ))

async def handle_client(client: TCPTransport):
    async for message in client.listen():
        payload = message.payload
        cmd = payload.get("c")
        print("Received command:", cmd)

        if cmd == "gs_quest":
            response = SFSObject()
            response.put_sfs_array("result", SFSArray())
            await send_extension_response(client, cmd, response)


async def run_server():
    async for client in server_from_url("tcp://localhost:9933"):
        print(f"New client connected: {client.host}:{client.port}")
        asyncio.create_task(handle_client(client))

if __name__ == "__main__":
    asyncio.run(run_server())
```

## TODO

We’re actively working to expand and improve ZewSFS. Here are some key features and enhancements planned for upcoming releases:

- [ ] **WebSocket Transport:** Add support for WebSocket connections alongside TCP, enabling browser clients and increasing flexibility.

- [ ] **High-Level Modules:** Build simplified, user-friendly server and client APIs to reduce boilerplate and speed up development.

- [ ] **Advanced Encryption:** Introduce additional encryption algorithms beyond AES-128-CBC to enhance security options.

- [ ] **Extensive Documentation:** Expand tutorials, guides, and real-world examples to help users onboard quickly and effectively.

We welcome contributions and ideas! Stay tuned for updates as we continue making ZewSFS better for everyone.
