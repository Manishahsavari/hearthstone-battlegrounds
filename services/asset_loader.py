
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pygame

_ASSETS_ROOT = Path(__file__).resolve().parent.parent / "bgknowhow-main" / "images"
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_CACHE: Dict[str, pygame.Surface] = {}


def _card_id_to_minion_path(card_id: str) -> Path:
    fallbacks = {
        "BG_MURLOC_001": "BG20_100",
        "BG_DRAGON_001": "BG20_101",
        "BG_TAUNT_001": "BG20_102",
        "BG_FRONT_001": "BG20_100",
        "BG_FRONT_006": "BG20_101",
        "BG_FRONT_009": "BG20_102",
    }
    base = fallbacks.get(card_id, card_id.replace("_", "").split(".")[0])
    return _ASSETS_ROOT / "minions" / f"{base}_render_80.webp"


def _hero_id_to_path(hero_id: str) -> Path:
    mapping = {
        "HERO_SYLVANAS": "BG23_HERO_306",
        "Ragnaros": "BG23_HERO_306",
        "Sylvanas": "BG23_HERO_306",
        "Lich King": "TB_BaconShop_HERO_22",
        "Millhouse": "TB_BaconShop_HERO_49",
        "Yogg-Saron": "TB_BaconShop_HERO_35",
    }
    base = mapping.get(hero_id, "BG23_HERO_306")
    return _ASSETS_ROOT / "heroes" / f"{base}_render_80.webp"


def load_minion_art(card_id: str, size: tuple[int, int] = (100, 100)) -> Optional[pygame.Surface]:
    key = f"minion_{card_id}_{size[0]}x{size[1]}"
    if key in _CACHE:
        return _CACHE[key]
    path = _card_id_to_minion_path(card_id)
    if not path.exists():
        alt = path.parent / f"{card_id}_render_80.webp"
        path = alt if alt.exists() else path
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
        surf = pygame.transform.smoothscale(surf, size)
        _CACHE[key] = surf
        return surf
    except (pygame.error, FileNotFoundError):
        return None


def load_hero_portrait(hero_id: str, size: tuple[int, int] = (120, 120)) -> Optional[pygame.Surface]:
    key = f"hero_{hero_id}_{size[0]}x{size[1]}"
    if key in _CACHE:
        return _CACHE[key]
    path = _hero_id_to_path(hero_id)
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
        surf = pygame.transform.smoothscale(surf, size)
        _CACHE[key] = surf
        return surf
    except (pygame.error, FileNotFoundError):
        return None


_HERO_POWER_PATHS = {
    "HERO_SYLVANAS": "TB_BaconShop_HP_022",  
}
_ASSETS_ROOT_HEROPOWER = _ASSETS_ROOT / "heropowers"


def load_board_background() -> Optional[pygame.Surface]:
    """Load the recruit/combat board background image. Returns None if not found."""
    key = "board_bg_raw"
    if key in _CACHE:
        return _CACHE[key]
    path = _ASSETS_DIR / "board_bg.png"
    try:
        surf = pygame.image.load(str(path)).convert()
        _CACHE[key] = surf
        return surf
    except (pygame.error, FileNotFoundError):
        return None


def load_hero_power_icon(hero_id: str, size: tuple[int, int] = (48, 48)) -> Optional[pygame.Surface]:
    """Load hero power icon for the hero. Returns None if not found."""
    key = f"heropower_{hero_id}_{size[0]}x{size[1]}"
    if key in _CACHE:
        return _CACHE[key]
    base = _HERO_POWER_PATHS.get(hero_id, "TB_BaconShop_HP_022")
    path = _ASSETS_ROOT_HEROPOWER / f"{base}_render_80.webp"
    if not path.exists():
        path = _ASSETS_ROOT_HEROPOWER / "TB_BaconShop_HP_022_render_80.webp"
    try:
        surf = pygame.image.load(str(path)).convert_alpha()
        surf = pygame.transform.smoothscale(surf, size)
        _CACHE[key] = surf
        return surf
    except (pygame.error, FileNotFoundError):
        return None
