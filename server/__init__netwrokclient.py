import uuid
from pathlib import Path

def get_or_create_token(path: str = ".client_token") -> str:
    p = Path(path)
    if p.exists():
        t = p.read_text().strip()
        if t:
            return t
    t = str(uuid.uuid4())
    p.write_text(t)
    return t
