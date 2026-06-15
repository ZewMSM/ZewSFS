import asyncio

import pytest
import pytest_asyncio

from sfs2x.app import (
    ExtensionRequest,
    ExtensionResponse,
    Int,
    LoginErrorResponse,
    LoginRequest,
    LoginResponse,
    SFSClient,
    SFSObject,
    SFSServer,
    ServerSession,
    Short,
    UtfString,
    field,
)


class EchoRequest(ExtensionRequest, command="echo"):
    text: UtfString = field("t")


class EchoResponse(ExtensionResponse, command="echo"):
    text: UtfString = field("t")
    length: Int = field("len")


@pytest_asyncio.fixture
async def tcp_server():
    server = SFSServer("tcp://127.0.0.1:29933")

    @server.on_extension(command="echo")
    async def on_echo(req: EchoRequest):
        raise EchoResponse(text=req.text, length=len(req.text))

    @server.on_login()
    async def on_login(req: LoginRequest, session: ServerSession):
        if req.password == "bad":
            raise LoginErrorResponse(error_code=1, error_message="wrong password")
        session.zone = req.zone
        session.username = req.username
        raise LoginResponse(zone=req.zone, username=req.username, user_id=42)

    await server.start()
    serve_task = asyncio.create_task(server.serve_forever())
    await asyncio.sleep(0.05)
    yield server
    serve_task.cancel()
    await server.stop()


@pytest.mark.asyncio
async def test_extension_roundtrip_via_raise(tcp_server):
    captured = {}
    client = SFSClient("tcp://127.0.0.1:29933")

    @client.on_extension(command="echo")
    async def on_echo(resp: EchoResponse):
        captured["reply"] = resp

    async with client:
        await client.call_extension("echo", EchoRequest(text="hello"))
        await asyncio.sleep(0.2)

    assert captured["reply"].text == "hello"
    assert captured["reply"].length == 5


@pytest.mark.asyncio
async def test_login_success_roundtrip(tcp_server):
    captured = {}
    client = SFSClient("tcp://127.0.0.1:29933")

    @client.on_login()
    async def on_login(resp: LoginErrorResponse | LoginResponse):
        captured["reply"] = resp

    async with client:
        await client.login(zone="MyZone", username="alice", password="ok")
        await asyncio.sleep(0.2)

    reply = captured["reply"]
    assert isinstance(reply, LoginResponse)
    assert reply.zone == "MyZone"
    assert reply.username == "alice"
    assert reply.user_id == 42


@pytest.mark.asyncio
async def test_login_error_union_dispatch(tcp_server):
    captured = {}
    client = SFSClient("tcp://127.0.0.1:29933")

    @client.on_login()
    async def on_login(resp: LoginErrorResponse | LoginResponse):
        captured["reply"] = resp

    async with client:
        await client.login(zone="MyZone", username="bob", password="bad")
        await asyncio.sleep(0.2)

    reply = captured["reply"]
    assert isinstance(reply, LoginErrorResponse)
    assert reply.error_code == 1
    assert reply.error_message == "wrong password"


@pytest.mark.asyncio
async def test_handler_receives_session_and_raw(tcp_server):
    seen = {}
    client = SFSClient("tcp://127.0.0.1:29933")

    @client.on_extension(command="echo")
    async def on_echo(resp: EchoResponse, raw: SFSObject):
        seen["resp"] = resp
        seen["raw_keys"] = list(raw.value.keys())

    async with client:
        await client.call_extension("echo", EchoRequest(text="hi"))
        await asyncio.sleep(0.2)

    assert seen["resp"].length == 2
    assert "t" in seen["raw_keys"]
    assert "len" in seen["raw_keys"]
