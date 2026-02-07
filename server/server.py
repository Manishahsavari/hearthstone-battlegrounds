# test for connect to server 
import asyncio 
import websockets
import orjson 
from dataclasses import dataclass, field
from websockets.server import ServerConnection


Host = "127.0.0.1"
Port = 8888
def dumps(obj)->str:
    return orjson.dumps(obj).decode("utf-8")

def loads(s: str):
    return orjson.loads(s)
@dataclass 
class Lobby:
    clients: dict[str, ServerConnection] = field(default_factory=dict)
    ready: list[bool] = field(default_factory=lambda: [False, False, False, False])
    queue: asyncio.Queue[tuple[str, dict]] = field(default_factory=asyncio.Queue)

    async def broadcast_state(self) -> None:
        msg = {
            "type": "LOBBY_UPDATE",
            "payload": {
                "players": [{"player_index": i, "ready": r} for i, r in enumerate(self.ready)],
                "can_start": all(self.ready),
        },
        }
        dead = []
        for tok , ws in self.clients.items():
            try:
                await ws.send(dumps(msg))
            except Exception:
                dead.append(tok)
        for tok in dead:
            self.clients.pop(tok, None)
    
    async def process_loop(self)->None:
        while True:
            token, data = await self.queue.get()
            action = data.get("action")
            payload = data.get("payload") or {}

            if action == "LOBBY_READY_TOGGLE":
                index = payload.get("player_index")
                if isinstance(index, int) and 0 <= index < 4:
                    self.ready[index] = not self.ready[index]
                    await self.broadcast_state()
                else:
                    pass
            elif action == "LOBBY_START":
                if all(self.ready):
                    await self.broadcast_state()
                else:
                    await self.broadcast_state()
            elif action == "HELLO":
                pass

lobby = Lobby()
async def handler(ws):
    print("[server] CONNECT", flush=True)
    token = None
    try:
        async for message in ws:
            print("[server] RECV_RAW:", message, flush=True)

            try:
                data = loads(message)
            except Exception as e:
                print("[server] BAD_JSON:", repr(e), flush=True)
                await ws.send(dumps({"type": "error", "error": "INVALID_JSON"}))
                continue

            action = data.get("action")

            if action == "HELLO":
                t = data.get("token")
                print("[server] HELLO token=", t, flush=True)
                if isinstance(t, str) and t:
                    token = t
                    lobby.clients[token] = ws
                    await lobby.broadcast_state()
                else:
                    await ws.send(dumps({"type": "error", "error": "MISSING_TOKEN"}))
                continue

            if token is None:
                print("[server] HELLO_REQUIRED", flush=True)
                await ws.send(dumps({"type": "error", "error": "HELLO_REQUIRED"}))
                continue

            print("[server] ENQUEUE action=", action, flush=True)
            await lobby.queue.put((token, data))

    except Exception as e:
        print("[server] HANDLER_EXCEPTION:", repr(e), flush=True)
    finally:
        if token:
            lobby.clients.pop(token, None)
        print("[server] DISCONNECT", flush=True)

async def main():
    print(f"listenning on {Host}:{Port}", flush=True)
    asyncio.create_task(lobby.process_loop())
    async with websockets.serve(handler, Host, Port):   
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())