from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pygame

from common.models import Keyword, Minion
from components.card_slot import CardSlot
from components.btn import Btn
from components.log_panel import LogPanel


def _load_combat_replay(data_dir: Path) -> List[Dict[str, Any]]:
    advanced = data_dir / "mock_combat_log_advanced.json"
    if advanced.exists():
        with advanced.open("r", encoding="utf-8") as f:
            return json.load(f)

    events: List[Dict[str, Any]] = []
    start_path = data_dir / "combat_start.json"
    if start_path.exists():
        with start_path.open("r", encoding="utf-8") as f:
            events.append(json.load(f))

    for name in ["combat_event_attack.json", "combat_event_deathrattle.json"]:
        p = data_dir / name
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                events.append(json.load(f))

    result_path = data_dir / "combat_result.json"
    if result_path.exists():
        with result_path.open("r", encoding="utf-8") as f:
            events.append(json.load(f))
    return events


class CombatViewerScreen:

    def __init__(
        self,
        on_action: Callable[[dict], None] | List[Dict[str, Any]] = None,
        set_screen: Callable[[str], None] | None = None,
    ) -> None:
        # Support CombatViewerScreen(events) for tests: first arg is list of event dicts
        if isinstance(on_action, list):
            self._events = on_action
            self._on_action = lambda _: None
            self._set_screen = lambda _: None
        else:
            self._on_action = on_action or (lambda _: None)
            self._set_screen = set_screen or (lambda _: None)
            data_dir = Path("data")
            self._events = _load_combat_replay(data_dir)

        self._font = pygame.font.SysFont("Arial", 18)

        self._build_layout()

        self._event_index = 0
        self._boards: Dict[str, List[Optional[Minion]]] = {"p1": [None] * 7, "p2": [None] * 7}
        self._side_order: List[str] = ["p1", "p2"]
        self._left_key = "p1"
        self._right_key = "p2"

        for ev in self._events:
            if ev.get("type") == "combat_start":
                self._apply_combat_start(ev)
                break

        self._log_panel.add_line(f"Loaded {len(self._events)} combat events.")

    def _build_layout(self) -> None:
        width, height = 1280, 720
        grid_x = 200
        self._bottom_slots = [
            CardSlot(pygame.Rect(grid_x + i * 130, height - 220, 120, 160))
            for i in range(7)
        ]
        self._top_slots = [
            CardSlot(pygame.Rect(grid_x + i * 130, 80, 120, 160))
            for i in range(7)
        ]
        self._btn_prev = Btn("Prev", pygame.Rect(40, height - 80, 80, 36), one_click=self._prev_step)
        self._btn_next = Btn("Next", pygame.Rect(140, height - 80, 80, 36), one_click=self._next_step)
        self._btn_back = Btn(
            "Back to Recruit",
            pygame.Rect(40, height - 130, 160, 36),
            one_click=lambda: self._set_screen("recruit"),
        )
        self._log_panel = LogPanel(rect=pygame.Rect(width - 320, 60, 280, height - 120))

    def _minion_from_payload(self, payload: Dict) -> Minion:
        kw = [Keyword(name=k) for k in payload.get("keywords", [])]
        return Minion(
            card_id=payload.get("card_id", ""),
            name=payload.get("name", payload.get("card_id", "?")),
            attack=payload.get("attack", 0),
            health=payload.get("health", 1),
            tier=payload.get("tier", 1),
            keywords=kw,
            instance_id=payload.get("instance_id"),
        )

    def _apply_combat_start(self, ev: Dict) -> None:
        boards = ev.get("boards", {})
        for side, entries in boards.items():
            board = [None] * 7
            for entry in entries:
                slot = entry.get("slot")
                if slot is not None and 0 <= slot < 7:
                    board[slot] = self._minion_from_payload(entry)
            self._boards[side] = board
        self._side_order = list(boards.keys()) if boards else ["p1", "p2"]
        self._left_key = self._side_order[0] if self._side_order else "p1"
        self._right_key = self._side_order[1] if len(self._side_order) > 1 else "p2"
        self._log_panel.add_line("Combat started.")

    def _apply_combat_event(self, ev: Dict) -> None:
        payload = ev.get("payload", {})
        kind = payload.get("kind")
        log = payload.get("log")
        if log:
            self._log_panel.add_line(log)
        if kind == "attack_start":
            att = payload.get("attacker", {})
            def_ = payload.get("defender", {})
            att_player = att.get("player_id") or att.get("player")
            def_player = def_.get("player_id") or def_.get("player")
            att_slot = att.get("slot")
            def_slot = def_.get("slot")
            if att_player and att_slot is not None:
                am = self._get_minion(att_player, att_slot)
                dm = self._get_minion(def_player, def_slot) if def_player else None
                if am and dm:
                    dm.health -= am.attack
                    am.health -= dm.attack
                    self._log_panel.add_line(f"Attack: {am.name} vs {dm.name}")
        elif kind == "deathrattle_trigger":
            src = payload.get("source", {})
            src_player = src.get("player_id") or src.get("player")
            src_slot = src.get("slot")
            if src_player is not None and src_slot is not None:
                board = self._boards.get(src_player)
                if board and 0 <= src_slot < len(board):
                    board[src_slot] = None
            for s in payload.get("summons", []):
                player = s.get("player_id") or s.get("player")
                if player and player in self._boards:
                    m = self._minion_from_payload(s)
                    for i, cell in enumerate(self._boards[player]):
                        if cell is None:
                            self._boards[player][i] = m
                            break

    def _get_minion(self, player: str, slot: int) -> Optional[Minion]:
        b = self._boards.get(player)
        if b and 0 <= slot < len(b):
            return b[slot]
        return None

    def _sync_slots(self) -> None:
        left = self._boards.get(self._left_key, [None] * 7)
        right = self._boards.get(self._right_key, [None] * 7)
        for i, v in enumerate(self._bottom_slots):
            m = left[i] if i < len(left) else None
            if m and m.health > 0:
                v.set_minion(m)
            else:
                v.set_empty()
        for i, v in enumerate(self._top_slots):
            m = right[i] if i < len(right) else None
            if m and m.health > 0:
                v.set_minion(m)
            else:
                v.set_empty()

    def _advance_event(self) -> None:
        """Advance by one event (used by tests)."""
        self._next_step()

    def _prev_step(self) -> None:
        if self._event_index <= 0:
            self._log_panel.add_line("At start.")
            return
        self._event_index -= 1
        self._replay_up_to(self._event_index)
        self._on_action({"action": "COMBAT_PREV", "step": self._event_index})

    def _next_step(self) -> None:
        if self._event_index >= len(self._events):
            self._log_panel.add_line("At end.")
            return
        ev = self._events[self._event_index]
        self._event_index += 1
        if ev.get("type") == "combat_event":
            self._apply_combat_event(ev)
        elif ev.get("type") == "combat_result":
            dmg = ev.get("damage", {})
            self._log_panel.add_line(f"Combat result. Damage: {dmg}")
        self._on_action({"action": "COMBAT_NEXT", "step": self._event_index})

    def _replay_up_to(self, index: int) -> None:
        for ev in self._events:
            if ev.get("type") == "combat_start":
                self._apply_combat_start(ev)
                break
        for i in range(index):
            if i < len(self._events) and self._events[i].get("type") == "combat_event":
                self._apply_combat_event(self._events[i])

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._btn_prev.handle_event(event)
            self._btn_next.handle_event(event)
            self._btn_back.handle_event(event)

    def update(self, dt: float) -> None:
        self._sync_slots()

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((10, 10, 20))
        title = self._font.render(
            f"Combat Viewer | Step {self._event_index}/{len(self._events)}",
            True,
            (240, 240, 240),
        )
        surface.blit(title, (40, 20))
        for slot in self._top_slots:
            slot.render(surface, self._font)
        for slot in self._bottom_slots:
            slot.render(surface, self._font)
        self._btn_prev.render(surface, self._font)
        self._btn_next.render(surface, self._font)
        self._btn_back.render(surface, self._font)
        self._log_panel.render(surface, self._font)
