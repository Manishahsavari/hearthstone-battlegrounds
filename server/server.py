import asyncio
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson
import websockets


HOST = "127.0.0.1"
PORT = 8888

DATA_DIR = Path(__file__).resolve().parent
USERS_PATH = DATA_DIR / "users.json"


def dumps(obj) -> str:
    return orjson.dumps(obj).decode("utf-8")


def loads(s: str):
    return orjson.loads(s)


def _read_users() -> dict:
    if USERS_PATH.exists():
        try:
            return orjson.loads(USERS_PATH.read_bytes())
        except Exception:
            return {}
    return {}


def _write_users(users: dict) -> None:
    USERS_PATH.write_bytes(orjson.dumps(users))


def _pbkdf2_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000, dklen=32)


def create_user(username: str, password: str) -> tuple[bool, str]:
    users = _read_users()
    if username in users:
        return False, "USER_EXISTS"
    salt = os.urandom(16)
    pw_hash = _pbkdf2_hash(password, salt)
    users[username] = {
        "salt": salt.hex(),
        "hash": pw_hash.hex(),
    }
    _write_users(users)
    return True, "OK"


def verify_user(username: str, password: str) -> bool:
    users = _read_users()
    rec = users.get(username)
    if not isinstance(rec, dict):
        return False
    salt_hex = rec.get("salt")
    hash_hex = rec.get("hash")
    if not (isinstance(salt_hex, str) and isinstance(hash_hex, str)):
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        target = bytes.fromhex(hash_hex)
    except Exception:
        return False
    cand = _pbkdf2_hash(password, salt)
    return hmac.compare_digest(cand, target)


BOT_NAMES = [
    "Ragnaros", "Nefarian", "Valeera", "Anduin", "Jaina",
    "Thrall", "Garrosh", "Tyrande", "Illidan", "Uther",
]

HERO_POOL = ["Sylvanas", "Lich King", "Millhouse", "Yogg-Saron"]


@dataclass
class PlayerState:
    token: str
    username: str
    display_name: str
    hero: str
    ready: bool
    is_bot: bool


@dataclass
class Lobby:
    clients: dict[str, Any] = field(default_factory=dict)
    queue: asyncio.Queue[tuple[str, dict]] = field(default_factory=asyncio.Queue)

    phase: str = "AUTH"
    players: list[PlayerState] = field(default_factory=list)

    game_id: str | None = None
    seed: int | None = None

    matchmaking_task: asyncio.Task | None = None
    matchmaking_progress: float = 0.0

    def _ensure_bots(self) -> None:
        used_names = {p.display_name for p in self.players}
        name_iter = (n for n in BOT_NAMES if n not in used_names)
        while len(self.players) < 4:
            name = next(name_iter, f"Bot{len(self.players)+1}")
            token = f"bot-{secrets.token_hex(8)}"
            hero = HERO_POOL[len(self.players) % len(HERO_POOL)]
            self.players.append(
                PlayerState(
                    token=token,
                    username=token,
                    display_name=name,
                    hero=hero,
                    ready=True,
                    is_bot=True,
                )
            )

    def _payload_players(self) -> list[dict]:
        out = []
        for i, p in enumerate(self.players):
            out.append(
                {
                    "player_index": i,
                    "name": p.display_name,
                    "hero": p.hero,
                    "ready": p.ready,
                    "is_bot": p.is_bot,
                }
            )
        return out

    async def broadcast(self, msg: dict) -> None:
        dead: list[str] = []
        for tok, ws in self.clients.items():
            try:
                await ws.send(dumps(msg))
            except Exception:
                dead.append(tok)
        for tok in dead:
            self.clients.pop(tok, None)

    async def send_to(self, token: str, msg: dict) -> None:
        ws = self.clients.get(token)
        if ws is None:
            return
        try:
            await ws.send(dumps(msg))
        except Exception:
            pass

    async def broadcast_lobby_update(self) -> None:
        can_start = self.phase == "LOBBY" and len(self.players) == 4 and all(p.ready for p in self.players)
        await self.broadcast(
            {
                "type": "LOBBY_UPDATE",
                "payload": {
                    "players": self._payload_players(),
                    "can_start": can_start,
                    "phase": self.phase,
                },
            }
        )

    async def broadcast_matchmaking(self) -> None:
        await self.broadcast(
            {
                "type": "MATCHMAKING_STATUS",
                "payload": {
                    "phase": self.phase,
                    "progress": self.matchmaking_progress,
                    "current": len(self.players),
                    "target": 4,
                },
            }
        )

    def _find_player_index(self, token: str) -> int | None:
        for i, p in enumerate(self.players):
            if p.token == token:
                return i
        return None

    async def start_matchmaking_if_needed(self) -> None:
        if self.matchmaking_task and not self.matchmaking_task.done():
            return
        self.phase = "MATCHMAKING"
        self.matchmaking_progress = 0.0
        await self.broadcast_matchmaking()
        self.matchmaking_task = asyncio.create_task(self._run_matchmaking())

    async def _run_matchmaking(self) -> None:
        steps = 30
        for i in range(steps):
            await asyncio.sleep(0.1)
            self.matchmaking_progress = (i + 1) / steps
            await self.broadcast_matchmaking()
        self._ensure_bots()
        self.phase = "LOBBY"
        await self.broadcast_lobby_update()

    async def start_game(self) -> None:
        self.phase = "RECRUIT"
        self.game_id = secrets.token_hex(8)
        self.seed = secrets.randbits(32)
        await self.broadcast_lobby_update()
        await self.broadcast({"type": "GAME_START", "payload": {"game_id": self.game_id, "seed": self.seed}})

    async def process_loop(self) -> None:
        while True:
            token, data = await self.queue.get()
            action = data.get("action")
            payload = data.get("payload") or {}

            if action == "LOBBY_READY_TOGGLE":
                if self.phase != "LOBBY":
                    continue
                idx = payload.get("player_index")
                if not (isinstance(idx, int) and 0 <= idx < len(self.players)):
                    continue
                if self.players[idx].is_bot:
                    continue
                self.players[idx].ready = not self.players[idx].ready
                await self.broadcast_lobby_update()
                continue

            if action == "LOBBY_START":
                if self.phase != "LOBBY":
                    continue
                pidx = self._find_player_index(token)
                if pidx is None:
                    continue
                if not self.players[pidx].ready:
                    self.players[pidx].ready = True
                await self.broadcast_lobby_update()
                if len(self.players) == 4 and all(p.ready for p in self.players):
                    await self.start_game()
                continue


lobby = Lobby()


async def handler(ws):
    token: str | None = None

    try:
        async for message in ws:
            try:
                data = loads(message)
            except Exception:
                await ws.send(dumps({"type": "error", "error": "INVALID_JSON"}))
                continue

            action = data.get("action")
            payload = data.get("payload") or {}

            if action == "REGISTER":
                username = payload.get("username")
                password = payload.get("password")
                display_name = payload.get("display_name")

                if not (isinstance(username, str) and username.strip()):
                    await ws.send(dumps({"type": "AUTH_ERROR", "error": "MISSING_USERNAME"}))
                    continue
                if not (isinstance(password, str) and len(password) >= 4):
                    await ws.send(dumps({"type": "AUTH_ERROR", "error": "WEAK_PASSWORD"}))
                    continue
                if not (isinstance(display_name, str) and display_name.strip()):
                    display_name = username

                ok, code = create_user(username.strip(), password)
                if not ok:
                    await ws.send(dumps({"type": "AUTH_ERROR", "error": code}))
                    continue

                await ws.send(dumps({"type": "REGISTER_OK"}))
                continue

            if action == "LOGIN":
                username = payload.get("username")
                password = payload.get("password")
                if not (isinstance(username, str) and isinstance(password, str)):
                    await ws.send(dumps({"type": "AUTH_ERROR", "error": "INVALID_CREDENTIALS"}))
                    continue
                if not verify_user(username.strip(), password):
                    await ws.send(dumps({"type": "AUTH_ERROR", "error": "INVALID_CREDENTIALS"}))
                    continue

                token = secrets.token_hex(16)
                old = lobby.clients.get(token)
                if old is not None and old is not ws:
                    try:
                        await old.close(code=4000, reason="replaced")
                    except Exception:
                        pass
                lobby.clients[token] = ws

                display_name = username.strip()
                lobby.players = [p for p in lobby.players if not p.is_bot]
                lobby.players.insert(
                    0,
                    PlayerState(
                        token=token,
                        username=username.strip(),
                        display_name=display_name,
                        hero=HERO_POOL[0],
                        ready=False,
                        is_bot=False,
                    ),
                )

                await ws.send(dumps({"type": "LOGIN_OK", "payload": {"token": token, "display_name": display_name}}))
                await lobby.start_matchmaking_if_needed()
                continue

            if action == "HELLO":
                t = data.get("token")
                if not (isinstance(t, str) and t):
                    await ws.send(dumps({"type": "error", "error": "MISSING_TOKEN"}))
                    continue
                token = t
                lobby.clients[token] = ws
                await lobby.broadcast_lobby_update()
                continue

            if token is None:
                await ws.send(dumps({"type": "error", "error": "AUTH_REQUIRED"}))
                continue

            await lobby.queue.put((token, data))

    finally:
        if token and lobby.clients.get(token) is ws:
            lobby.clients.pop(token, None)


async def main():
    asyncio.create_task(lobby.process_loop())
    async with websockets.serve(handler, HOST, PORT, ping_interval=None):
        print(f"listening on ws://{HOST}:{PORT}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
