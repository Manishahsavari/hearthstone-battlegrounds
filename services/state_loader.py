from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common.models import Keyword, Minion, Player, ShopSlot


@dataclass
class RecruitSnapshot:
    match_id: str = ""
    turn: int = 1
    players: Dict[str, Player] = field(default_factory=dict)
    active_player_id: str = "p1"


def load_json(path: str | Path) -> Any:
    raw = Path(path).read_text(encoding="utf-8")
    return json.loads(raw)


def load_recruit_snapshot(path: str | Path, *, active_player_id: Optional[str] = None) -> RecruitSnapshot:
    data = load_json(path)
    return _parse_recruit_snapshot(data, active_player_id=active_player_id)


def _parse_recruit_snapshot(data: Dict[str, Any], *, active_player_id: Optional[str]) -> RecruitSnapshot:
    match_id = data.get("match_id", "")
    turn = int(data.get("turn", 1))
    players_list = data.get("players", [])
    players: Dict[str, Player] = {}

    for payload in players_list:
        player = _parse_player(payload)
        players[player.player_id] = player

    if active_player_id is None:
        active_player_id = players_list[0]["player_id"] if players_list else "p1"

    return RecruitSnapshot(match_id=match_id, turn=turn, players=players, active_player_id=active_player_id)


def _parse_player(payload: Dict[str, Any]) -> Player:
    hero = payload.get("hero")
    hero_id = ""
    hero_name = ""
    hero_power_cost = payload.get("hero_power_cost", 0)
    hero_power_used = payload.get("hero_power_used", False)
    health = payload.get("health", 30)
    armor = payload.get("armor", 0)

    if isinstance(hero, dict):
        hero_id = hero.get("card_id", "")
        hero_name = hero.get("name", "")
        health = hero.get("health", health)
        armor = hero.get("armor", armor)
        hero_power_cost = hero.get("hero_power_cost", hero_power_cost)
        hero_power_used = hero.get("hero_power_used", hero_power_used)
    elif isinstance(hero, str):
        hero_name = hero

    player = Player(
        player_id=payload.get("player_id", ""),
        name=payload.get("name", payload.get("player_id", "")),
        hero_id=payload.get("hero_id", hero_id),
        hero_name=hero_name,
        health=health,
        armor=armor,
        gold=payload.get("gold", 3),
        max_gold=payload.get("max_gold", payload.get("gold", 3)),
        tavern_tier=payload.get("tavern_tier", 1),
        tavern_upgrade_cost=payload.get("upgrade_cost", payload.get("tavern_upgrade_cost", 5)),
        refresh_cost=payload.get("refresh_cost", 1),
        hero_power_cost=hero_power_cost,
        hero_power_used=hero_power_used,
        flags=payload.get("flags", {}),
    )

    player.board = _parse_board(payload.get("board", []))
    player.hand = _parse_hand(payload.get("hand", []))
    player.shop = _parse_shop(payload.get("shop", []))

    return player


def _parse_keywords(names: Optional[List[str]]) -> List[Keyword]:
    if not names:
        return []
    return [Keyword(name=name) for name in names]


def _parse_minion(payload: Dict[str, Any]) -> Minion:
    keywords = _parse_keywords(payload.get("keywords"))
    is_aura = any(keyword.name == "Aura" for keyword in keywords)
    return Minion(
        card_id=payload.get("card_id", ""),
        name=payload.get("name", payload.get("card_id", "Unknown")),
        attack=payload.get("attack", payload.get("base_attack", 0)),
        health=payload.get("health", payload.get("base_health", 0)),
        tier=payload.get("tier", payload.get("sim_tier", 1)),
        keywords=keywords,
        instance_id=payload.get("instance_id"),
        base_attack=payload.get("base_attack"),
        base_health=payload.get("base_health"),
        is_golden=payload.get("is_golden", False),
        has_divine_shield=payload.get("has_divine_shield", False),
        reborn_used=payload.get("reborn_used", False),
        is_aura=is_aura,
    )


def _parse_board(entries: List[Dict[str, Any]]) -> List[Optional[Minion]]:
    board: List[Optional[Minion]] = [None] * 7
    for entry in entries:
        slot = entry.get("slot")
        if slot is None:
            continue
        if 0 <= slot < len(board):
            board[slot] = _parse_minion(entry)
    return board


def _parse_hand(entries: List[Dict[str, Any]]) -> List[Minion]:
    hand: List[Minion] = []
    for entry in entries:
        hand.append(_parse_minion(entry))
    return hand


def _parse_shop(entries: List[Any]) -> List[ShopSlot]:
    shop: List[ShopSlot] = []
    for index, entry in enumerate(entries):
        if entry is None:
            shop.append(ShopSlot(slot=index, minion=None))
            continue
        minion = _parse_minion(entry)
        shop.append(
            ShopSlot(
                slot=entry.get("slot", index),
                minion=minion,
                frozen=entry.get("frozen", False),
                cost=entry.get("cost", 3),
                sim_tier=entry.get("sim_tier", minion.tier),
            )
        )
    return shop


def load_combat_replay(path: str | Path) -> List[Dict[str, Any]]:
    data = load_json(path)
    if isinstance(data, list):
        return data
    return [data]


def apply_state_delta(snapshot: RecruitSnapshot, delta: Dict[str, Any]) -> None:
    if delta.get("type") != "state_delta":
        return

    for event in delta.get("events", []):
        op = event.get("op")
        player_id = event.get("player_id")
        player = snapshot.players.get(player_id) if player_id else None

        if op == "gold" and player is not None:
            player.gold = int(event.get("value", player.gold))
        elif op == "shop_update" and player is not None:
            slots = event.get("slots", [])
            for slot in slots:
                index = slot.get("index")
                if index is None:
                    continue
                while len(player.shop) <= index:
                    player.shop.append(ShopSlot(slot=len(player.shop), minion=None))
                player.shop[index] = ShopSlot(
                    slot=index,
                    minion=_parse_minion(slot),
                    frozen=slot.get("frozen", False),
                    cost=slot.get("cost", 3),
                    sim_tier=slot.get("sim_tier", 1),
                )
        elif op == "board_update" and player is not None:
            slot_index = event.get("slot")
            if slot_index is None:
                continue
            if len(player.board) < 7:
                player.board = (player.board + [None] * 7)[:7]
            player.board[slot_index] = _parse_minion(event)
        elif op == "board_insert" and player is not None:
            slot_index = event.get("slot")
            if slot_index is None:
                continue
            if len(player.board) < 7:
                player.board = (player.board + [None] * 7)[:7]
            player.board[slot_index] = _parse_minion(event)
        elif op == "board_remove" and player is not None:
            slot_index = event.get("slot")
            if slot_index is None:
                continue
            if 0 <= slot_index < len(player.board):
                player.board[slot_index] = None
        elif op == "hand_add" and player is not None:
            card = event.get("card")
            if card:
                player.hand.append(_parse_minion(card))
        elif op == "freeze_state" and player is not None:
            frozen = event.get("value", False)
            player.flags["shop_frozen"] = frozen
            for slot in player.shop:
                slot.frozen = frozen if slot.minion is not None else False
        elif op == "hero_health" and player is not None:
            player.health = int(event.get("value", player.health))
        elif op == "armor" and player is not None:
            player.armor = int(event.get("value", player.armor))
        elif op == "tavern_tier" and player is not None:
            player.tavern_tier = int(event.get("value", player.tavern_tier))
        elif op == "log":
            continue
