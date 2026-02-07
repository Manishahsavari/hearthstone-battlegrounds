from __future__ import annotations

import asyncio
import threading
from typing import Optional

import orjson
import websockets

from .event_bus import EventBus


def dumps(obj) -> str:
    return orjson.dumps(obj).decode("utf-8")


def loads(s: str):
    return orjson.loads(s)


class NetworkClient:
    def __init__(self, event_bus: EventBus, url: str = "ws://127.0.0.1:8888"):
        self.event_bus = event_bus
        self.url = url
        self.token: str | None = None
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag.set()

    def set_token(self, token: str) -> None:
        self.token = token

    def _run_thread(self) -> None:
        asyncio.run(self._main())

    async def _sender(self, ws) -> None:
        while not self._stop_flag.is_set():
            sent_any = False
            for ev in self.event_bus.drain_server(50):
                await ws.send(dumps(ev))
                sent_any = True
            if not sent_any:
                await asyncio.sleep(0.02)

    async def _receiver(self, ws) -> None:
        async for msg in ws:
            try:
                data = loads(msg)
            except Exception:
                continue
            self.event_bus.post_to_ui(data)

    async def _main(self) -> None:
        while not self._stop_flag.is_set():
            try:
                async with websockets.connect(self.url, ping_interval=None) as ws:
                    if self.token:
                        await ws.send(dumps({"action": "HELLO", "token": self.token}))
                    await asyncio.gather(self._sender(ws), self._receiver(ws))
            except Exception:
                await asyncio.sleep(0.5)
