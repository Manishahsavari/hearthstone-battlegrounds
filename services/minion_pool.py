from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List

from common.models import Keyword, Minion


@dataclass(frozen=True)
class MinionTemplate:
    card_id: str
    name: str
    attack: int
    health: int
    tier: int
    keywords: List[Keyword]

    def spawn(self) -> Minion:
        is_aura = any(keyword.name == "Aura" for keyword in self.keywords)
        return Minion(
            card_id=self.card_id,
            name=self.name,
            attack=self.attack,
            health=self.health,
            tier=self.tier,
            keywords=list(self.keywords),
            is_aura=is_aura,
        )


def _kw(names: List[str]) -> List[Keyword]:
    return [Keyword(name=n) for n in names]


_POOL: List[MinionTemplate] = [
    MinionTemplate("BG_MURLOC_001", "Murloc", 2, 1, 1, _kw([])),
    MinionTemplate("BG_DRAGON_001", "Dragon Whelp", 3, 4, 1, _kw([])),
    MinionTemplate("BG_TAUNT_001", "Taunt Guy", 1, 6, 1, _kw(["Taunt"])),
    MinionTemplate("BG_BEETLE_001", "Buzzing Vermin", 1, 2, 2, _kw(["Taunt", "Deathrattle"])),
    MinionTemplate("BG_BEETLE_002", "Forest Rover", 2, 3, 2, _kw(["Deathrattle"])),
    MinionTemplate("BG_DIVINE_001", "Bronze Warden", 2, 1, 3, _kw(["Divine Shield", "Reborn"])),
    MinionTemplate("BG_AMALGAM_001", "Nightmare Amalgam", 3, 4, 3, _kw(["Taunt", "Divine Shield"])),
    MinionTemplate("BG_AURA_001", "Baron Aura", 4, 4, 4, _kw(["Aura"])),
    MinionTemplate("BG_TIER4_001", "Ironhide Defender", 5, 7, 4, _kw(["Taunt"])),
]


def by_tier() -> Dict[int, List[MinionTemplate]]:
    tiers: Dict[int, List[MinionTemplate]] = {}
    for entry in _POOL:
        tiers.setdefault(entry.tier, []).append(entry)
    return tiers


def random_minion(tier: int, rng: random.Random) -> Minion:
    tiers = by_tier()
    candidates = tiers.get(tier) or tiers.get(max(tiers.keys()), [])
    template = rng.choice(candidates)
    return template.spawn()


def random_minion_from_tiers(tiers: List[int], rng: random.Random) -> Minion:
    tier_options = [t for t in tiers if t in by_tier()]
    if not tier_options:
        tier_options = list(by_tier().keys())
    tier = rng.choice(tier_options)
    return random_minion(tier, rng)
