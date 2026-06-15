import asyncio
import pytest
import pytest_asyncio

from sfs2x.core import Float, UtfString, Int, Double, SFSObject
from sfs2x.transport import client_from_url, server_from_url, Transport
from sfs2x.protocol import Message, ControllerID, SysAction


async def _echo_handler(conn: Transport) -> None:
    async for msg in conn.listen():
        obj = msg.payload.value.get('input')
        obj.value *= 2
        msg.payload['resp'] = obj
        await conn.send(msg)


async def _run_echo_server(url: str, *, encryption_key: bytes | None = None) -> None:
    async with server_from_url(url, encryption_key=encryption_key) as acceptor:
        async for conn in acceptor:
            asyncio.create_task(_echo_handler(conn))


@pytest_asyncio.fixture
async def tcp_echo_server():
    server_task = asyncio.create_task(
        _run_echo_server("tcp://0.0.0.0:9000", encryption_key=b'mega_secured_key')
    )
    await asyncio.sleep(0.2)
    yield
    server_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await server_task


@pytest_asyncio.fixture
async def ws_echo_server():
    server_task = asyncio.create_task(
        _run_echo_server("ws://0.0.0.0:9001/BlueBox/websocket", encryption_key=b'mega_secured_key')
    )
    await asyncio.sleep(0.2)
    yield
    server_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await server_task


@pytest.mark.asyncio
async def test_tcp_echo_roundtrip(tcp_echo_server):
    conn = client_from_url("tcp://localhost:9000", encryption_key=b'mega_secured_key')

    async with conn:
        for value in [UtfString('Friday, '), Int(8), Double(123.12)]:
            test_msg = Message(ControllerID.SYSTEM, SysAction.PING_PONG, SFSObject({'input': value}))
            await conn.send(test_msg)

            answer = await conn.recv()
            assert answer.controller == test_msg.controller
            assert answer.action == test_msg.action
            assert answer.payload.get('resp') == value.value * 2


@pytest.mark.asyncio
async def test_ws_echo_roundtrip(ws_echo_server):
    conn = client_from_url(
        "ws://localhost:9001/BlueBox/websocket",
        encryption_key=b'mega_secured_key',
    )

    async with conn:
        for value in [UtfString('Friday, '), Int(8), Double(123.12)]:
            test_msg = Message(ControllerID.SYSTEM, SysAction.PING_PONG, SFSObject({'input': value}))
            await conn.send(test_msg)

            answer = await conn.recv()
            assert answer.controller == test_msg.controller
            assert answer.action == test_msg.action
            assert answer.payload.get('resp') == value.value * 2


@pytest.mark.asyncio
async def test_msm_server():
    async with client_from_url("tcp://107.20.67.227") as conn:
        session_info = SFSObject()
        session_info.put_utf_string("api", "1.0.3")
        session_info.put_utf_string("cl", "UnityPlayer::")
        session_info.put_bool("bin", True)

        await conn.send(Message(ControllerID.SYSTEM, SysAction.HANDSHAKE, session_info))

        handshake = await conn.recv()
        assert handshake.controller == ControllerID.SYSTEM
        assert handshake.action == SysAction.HANDSHAKE

        auth_info = SFSObject()
        auth_info.put_utf_string("zn", "MySingingPenis")
        auth_info.put_utf_string("un", "")
        auth_info.put_utf_string("pw", "")
        auth_info.put_sfs_object("p", SFSObject())

        await conn.send(Message(ControllerID.SYSTEM, SysAction.LOGIN, auth_info))

        resp = await conn.recv()
        assert resp.payload['ec'] == 1
