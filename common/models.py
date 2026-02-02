from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict,List,Optional

@dataclass(frozen=True)
class Keyword:
    name: str

@dataclass
class Minion:
    card_id: str
    name: str
    attack : int
    health : int
    tier: int
    keywords : List[Keyword] = field(default_factory=list)
    instance_id : Optional[str] = None

@dataclass
class ShopSlot:
    slot : int
    minion: Optional[Minion]
    frozen: bool = False

@dataclass
class Player:
    player_id: str
    name: str
    hero_id : str
    health : int
    gold : int
    tavern_tier : int
    board: List[Minion] = field(default_factory=list)
    hand: List[Minion] = field(default_factory=list)
    shop: List[ShopSlot] = field(default_factory=list)
    hero_power_used: bool = False

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