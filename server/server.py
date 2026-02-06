# test for connect to server 
import asyncio 
import websockets
import orjson 



Host = "127.0.0.1"
Port = 8888
def dumps(obj)->str:
    return orjson.dumps(obj).decode("utf-8")

def loads(s: str):
    return orjson.loads(s)

async def handler(ws):
    print("Connected", flush=True)
    
    try:
        async for message in ws:
            print("reccive", message, flush=True)
            try:
                data = loads(message)
            except Exception:
                await ws.send(dumps({"type": "error", "error":"INVALID_JSON"}))
                continue

            action = data.get("action")
            token = data.get("token")

            if action != "HELLO":
                await ws.send(dumps({"type": "error", "error": "UNKNOWN_ACTION"}))
                continue
            if not isinstance(token, str) or len(token) == 0:
                await ws.send(dumps({"type": "error", "error": "MISSING_TOKEN"}))
                continue

            await ws.send(dumps({"type": "WELCOME", "payload":{"message": "hello from server", "token_echo":token}}))
    except websockets.exceptions.ConnectionClosed:
        pass 
    finally:
        print("Disconnected")

async def main():
    print(f"listenning on {Host}:{Port}")
    async with websockets.serve(handler, Host, Port):   
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())