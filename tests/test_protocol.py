import asyncio
import logging

from sfs2x.core import Float
from sfs2x.transport import client_from_url, server_from_url, TCPTransport
from sfs2x.protocol import Message, ControllerID, SysAction
from sfs2x.core.types.containers import SFSObject

logging.getLogger("SFS2X/TCPTransport").setLevel(logging.DEBUG)

async def svr():
    async for conn in server_from_url("tcp://0.0.0.0:9000"):
        asyncio.create_task(echo(conn))

async def echo(conn: TCPTransport):
    print('connected ', conn.host)
    while True:
        msg = await conn.recv()
        print("server got", msg)
        await conn.send(msg)

async def cli():
    await asyncio.sleep(1)
    conn = await client_from_url("tcp://localhost:9000").open()
    await conn.send(Message(ControllerID.SYSTEM, SysAction.PING_PONG, SFSObject({'float': Float(123)})))
    answer = await conn.recv()
    print("client got", answer)

async def main():
    await cli()

if __name__ == "__main__":
    asyncio.run(main())