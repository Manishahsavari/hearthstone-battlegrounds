from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import orjson


@dataclass
class Profile:
    token: str
    name: str


def load_or_create_profile(path: str = ".client_profile.json") -> Profile:
    p = Path(path)
    if p.exists():
        data = orjson.loads(p.read_bytes())
        token = data.get("token")
        name = data.get("name")
        if isinstance(token, str) and token and isinstance(name, str) and name:
            return Profile(token=token, name=name)

    name = input("Enter your username: ").strip() or "Player"
    token = str(uuid.uuid4())
    p.write_bytes(orjson.dumps({"token": token, "name": name}))
    return Profile(token=token, name=name)
