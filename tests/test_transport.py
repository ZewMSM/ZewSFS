import asyncio
import pytest
import pytest_asyncio

from sfs2x.core import Float, UtfString, Int, Double, SFSObject
from sfs2x.transport import client_from_url, server_from_url, TCPTransport
from sfs2x.protocol import Message, ControllerID, SysAction

@pytest_asyncio.fixture
async def echo_server(event_loop):
    server_task = event_loop.create_task(run_echo_server())
    await asyncio.sleep(0.2)

    yield

    server_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await server_task

async def run_echo_server():
    async for conn in server_from_url("tcp://0.0.0.0:9000", encryption_key=b'mega_secured_key'):
        asyncio.create_task(some_handler(conn))

async def some_handler(conn: TCPTransport):
    async for msg in conn.listen():
        print(msg)
        obj = msg.payload.value.get('input')
        obj.value *= 2
        msg.payload['resp'] = obj
        await conn.send(msg)

@pytest.mark.asyncio
async def test_tcp_echo_roundtrip(echo_server):
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