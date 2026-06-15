import asyncio
from dataclasses import dataclass, field as dc_field
from typing import Any

import pytest

from sfs2x.app import (
    ExtensionRequest,
    ExtensionResponse,
    Int,
    Message,
    Reply,
    SFSModel,
    SFSObject,
    ServerSession,
    Short,
    SystemRequest,
    SystemResponse,
    UtfString,
    field,
)
from sfs2x.app.dispatcher import Dispatcher
from sfs2x.app.handlers import HandlerRegistry, inspect_handler, ParamKind
from sfs2x.protocol import ControllerID, SysAction


class _FakeTransport:
    """In-memory transport that records sent messages and feeds queued ones."""

    def __init__(self):
        self.host = "test"
        self.port = 0
        self._sent: list[Message] = []
        self._incoming: asyncio.Queue[Message | None] = asyncio.Queue()
        self._opened = True

    @property
    def closed(self):
        return not self._opened

    async def send(self, msg):
        self._sent.append(msg)

    async def close(self):
        self._opened = False
        await self._incoming.put(None)

    async def listen(self):
        while True:
            item = await self._incoming.get()
            if item is None:
                break
            yield item

    def push(self, msg):
        self._incoming.put_nowait(msg)


# ---------- handler signature introspection ----------


def test_inspect_message_param():
    async def h(msg: Message): pass
    specs = inspect_handler(h)
    assert specs[0].kind == ParamKind.MESSAGE


def test_inspect_payload_param():
    async def h(payload: SFSObject): pass
    specs = inspect_handler(h)
    assert specs[0].kind == ParamKind.PAYLOAD


def test_inspect_session_param():
    async def h(session: ServerSession): pass
    specs = inspect_handler(h)
    assert specs[0].kind == ParamKind.SESSION


def test_inspect_model_param():
    class M(SFSModel):
        v: Int = field("v")

    async def h(m: M): pass
    specs = inspect_handler(h)
    assert specs[0].kind == ParamKind.MODEL
    assert specs[0].candidates == (M,)


def test_inspect_union_model_param():
    class A(SFSModel):
        a: Int = field("a")
    class B(SFSModel):
        b: Int = field("b")

    async def h(x: A | B): pass
    specs = inspect_handler(h)
    assert specs[0].kind == ParamKind.UNION_MODEL
    assert specs[0].candidates == (A, B)


# ---------- registration ----------


def test_register_system_handler():
    reg = HandlerRegistry()

    async def h(msg: Message): pass

    reg.register_system(SysAction.LOGIN, h)
    assert SysAction.LOGIN in reg.system


def test_register_extension_handler():
    reg = HandlerRegistry()

    async def h(msg: Message): pass

    reg.register_extension("cmd", h)
    assert "cmd" in reg.extension


# ---------- dispatch ----------


class LoginReq(SystemRequest, action=SysAction.LOGIN):
    zone: UtfString = field("zn")


class LoginOk(SystemResponse, action=SysAction.LOGIN):
    uid: Int = field("uid")


class LoginErr(SystemResponse, action=SysAction.LOGIN):
    ec: Short = field("ec")


class PingReq(ExtensionRequest, command="ping"):
    n: Int = field("n")


class PongResp(ExtensionResponse, command="ping"):
    n: Int = field("n")


@pytest.mark.asyncio
async def test_dispatch_system_action():
    reg = HandlerRegistry()
    received = []

    @lambda fn: reg.register_system(SysAction.LOGIN, fn) or fn
    async def on_login(req: LoginReq):
        received.append(req)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(LoginReq(zone="z").to_message())
    await transport.close()
    await dispatcher.run()
    assert received[0].zone == "z"


@pytest.mark.asyncio
async def test_dispatch_extension_by_command():
    reg = HandlerRegistry()
    received = []

    @lambda fn: reg.register_extension("ping", fn) or fn
    async def on_ping(req: PingReq):
        received.append(req)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(PingReq(n=5).to_message(request_id=11))
    await transport.close()
    await dispatcher.run()
    assert received[0].n == 5


@pytest.mark.asyncio
async def test_raise_response_sends_reply():
    reg = HandlerRegistry()

    @lambda fn: reg.register_extension("ping", fn) or fn
    async def on_ping(req: PingReq):
        raise PongResp(n=req.n * 2)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(PingReq(n=3).to_message(request_id=99))
    await transport.close()
    await dispatcher.run()
    assert len(transport._sent) == 1
    sent = transport._sent[0]
    assert sent.controller == ControllerID.EXTENSION
    assert sent.payload.value["c"].value == "ping"
    assert sent.payload.value["r"].value == 99
    assert sent.payload.value["p"].value["n"].value == 6


@pytest.mark.asyncio
async def test_return_response_sends_reply():
    reg = HandlerRegistry()

    @lambda fn: reg.register_extension("ping", fn) or fn
    async def on_ping(req: PingReq):
        return PongResp(n=req.n + 1)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(PingReq(n=4).to_message(request_id=5))
    await transport.close()
    await dispatcher.run()
    assert transport._sent[0].payload.value["p"].value["n"].value == 5


@pytest.mark.asyncio
async def test_reply_wrapper_sends_reply():
    reg = HandlerRegistry()

    @lambda fn: reg.register_extension("ping", fn) or fn
    async def on_ping(req: PingReq):
        raise Reply(PongResp(n=42))

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(PingReq(n=1).to_message())
    await transport.close()
    await dispatcher.run()
    assert transport._sent[0].payload.value["p"].value["n"].value == 42


@pytest.mark.asyncio
async def test_union_dispatch_picks_first_match():
    reg = HandlerRegistry()
    received = []

    @lambda fn: reg.register_system(SysAction.LOGIN, fn) or fn
    async def on_login(req: LoginErr | LoginOk):
        received.append(req)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    # No "ec" field → should pick LoginOk
    transport.push(LoginOk(uid=1).to_message())
    # With "ec" → should pick LoginErr
    transport.push(LoginErr(ec=42).to_message())
    await transport.close()
    await dispatcher.run()
    assert isinstance(received[0], LoginOk)
    assert isinstance(received[1], LoginErr)


@pytest.mark.asyncio
async def test_catchall_handler():
    reg = HandlerRegistry()
    received = []

    @lambda fn: reg.register_catchall(fn) or fn
    async def fallback(msg: Message):
        received.append(msg)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(Message(ControllerID.SYSTEM, 99, SFSObject()))
    await transport.close()
    await dispatcher.run()
    assert len(received) == 1


@pytest.mark.asyncio
async def test_handler_exception_fires_on_error():
    reg = HandlerRegistry()
    errors = []

    @lambda fn: reg.register_extension("ping", fn) or fn
    async def on_ping(req: PingReq):
        raise ValueError("boom")

    @lambda fn: reg.register_lifecycle("error", fn) or fn
    async def on_err(exc: Exception, msg: Message):
        errors.append(exc)

    transport = _FakeTransport()
    dispatcher = Dispatcher(reg, transport, session=None, owner=None)
    transport.push(PingReq(n=1).to_message())
    await transport.close()
    await dispatcher.run()
    assert any(isinstance(e, ValueError) for e in errors)
