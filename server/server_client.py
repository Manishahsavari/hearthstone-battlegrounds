import asyncio 
import websockets
import orjson

def dumps(obj)->str:
    return orjson.dumps(obj).decode("utf-8")

async def main():
    uri = "ws://127.0.0.1:8888"
    async with websockets.connect(uri) as ws:
        await ws.send(dumps({"action":"HELLO", "token": "test-123"}))
        resp = await ws.recv()
        print(resp)


asyncio.run(main())