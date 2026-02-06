from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass(frozen=True)
class Keyword:
    name: str

@dataclass
class Minion:
    card_id: str
    name: str
    attack: int
    health: int
    tier: int
    keywords: List[Keyword] = field(default_factory=list)
    instance_id: Optional[str] = None
    base_attack: Optional[int] = None
    base_health: Optional[int] = None
    is_golden: bool = False
    has_divine_shield: bool = False
    reborn_used: bool = False
    is_aura: bool = False

@dataclass
class ShopSlot:
    slot: int
    minion: Optional[Minion]
    frozen: bool = False
    cost: int = 3
    sim_tier: int = 1

@dataclass
class Player:
    player_id: str
    name: str = ""
    hero_id: str = ""
    hero_name: str = ""
    health: int = 30
    armor: int = 0
    gold: int = 3
    max_gold: int = 3
    tavern_tier: int = 1
    tavern_upgrade_cost: int = 5
    tavern_upgrade_base: int = 5
    tavern_upgrade_min: int = 2
    refresh_cost: int = 1
    hero_power_cost: int = 0
    hero_power_used: bool = False
    board: List[Optional[Minion]] = field(default_factory=list)
    hand: List[Minion] = field(default_factory=list)
    shop: List[ShopSlot] = field(default_factory=list)
    flags: Dict = field(default_factory=dict)
    is_dead: bool = False
    is_ghost: bool = False

@dataclass
class CombatEvent:
    event_uuid: str
    step : int
    kind: str
    payload: Dict

@dataclass
class StateDelta:
    delta_uuid: str
    payload: Dict
