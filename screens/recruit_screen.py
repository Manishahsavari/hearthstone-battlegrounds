from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import pygame

from common.models import Minion, Player, ShopSlot
from components.btn import Btn
from components.card_slot import CardSlot
from components.leaderboard_panel import LeaderboardPanel
from components.popup_choice import PopupChoice
from services.drag_manager import DragManager
from services.asset_loader import load_hero_portrait, load_hero_power_icon, load_board_background


MAX_GOLD = 10
BUY_COST = 3
SELL_GAIN = 1
REFRESH_COST = 1
FREEZE_COST = 0
HERO_POWER_COST = 0

TAVERN_UPGRADE_TABLE = {
    1: (5, 2),
    2: (7, 2),
    3: (8, 2),
    4: (9, 2),
    5: (10, 2),
    6: (0, 0),
}


@dataclass
class RecruitState:
    player: Player
    turn: int = 1
    shop_frozen: bool = False
    upgrade_cost: int = TAVERN_UPGRADE_TABLE[1][0]


class RecruitScreen:
    def __init__(
        self,
        state: RecruitState,
        on_action: Callable[[dict], None],
        set_screen: Callable[[str], None] | None = None,
    ) -> None:
        self.state = state
        self._on_action = on_action
        self._set_screen = set_screen or (lambda _: None)

        self._font = pygame.font.SysFont("Arial", 18)
        self._font_bold = pygame.font.SysFont("Arial", 18, bold=True)
        self._title_font = pygame.font.SysFont("Arial", 22, bold=True)

        self._error_message: Optional[str] = None
        self._error_timer: float = 0.0

        self._hero_portrait = load_hero_portrait("HERO_SYLVANAS", (120, 120))
        self._hero_power_icon = load_hero_power_icon("HERO_SYLVANAS", (40, 40))
        self._board_bg = load_board_background()

        self._discover_popup: Optional[PopupChoice] = None

        self._dirty_ui: bool = True
        self._last_gold: int = -1
        self._last_shop_frozen: Optional[bool] = None
        self._last_shop_sig: Optional[tuple] = None
        self._last_hand_sig: Optional[tuple] = None
        self._last_board_sig: Optional[tuple] = None

        self._build_layout()

        self._drag = DragManager(
            on_buy=self._buy_from_shop,
            on_play=self._play_from_hand,
            on_sell=self._sell_from_board,
        )

        self._drag_event_fn = getattr(self._drag, "handle_event", None)
        if not callable(self._drag_event_fn):
            self._drag_event_fn = getattr(self._drag, "on_event", None)
        if not callable(self._drag_event_fn):
            self._drag_event_fn = getattr(self._drag, "process_event", None)
        if not callable(self._drag_event_fn):
            self._drag_event_fn = None

        self._drag_update_fn = getattr(self._drag, "update", None)
        if not callable(self._drag_update_fn):
            self._drag_update_fn = None

        self._drag_render_fn = getattr(self._drag, "render", None)
        if not callable(self._drag_render_fn):
            self._drag_render_fn = None

        self._leaderboard = LeaderboardPanel(
            rect=self._rect_leaderboard,
            players=[self.state.player],
        )

        self._ensure_minimum_state()
        self._mark_dirty()

    def _build_layout(self) -> None:
        w, h = 1280, 720

        self._rect_left = pygame.Rect(30, 30, 220, h - 60)
        self._rect_center = pygame.Rect(270, 30, 720, h - 60)
        self._rect_right = pygame.Rect(1010, 30, 240, h - 60)

        self._rect_hero = pygame.Rect(self._rect_left.x + 20, self._rect_left.y + 20, 180, 170)
        self._rect_stats = pygame.Rect(self._rect_left.x + 20, self._rect_left.y + 210, 180, 160)
        self._rect_controls = pygame.Rect(self._rect_left.x + 20, self._rect_left.y + 390, 180, 270)

        self._rect_shop = pygame.Rect(self._rect_center.x + 20, self._rect_center.y + 20, 680, 190)
        self._rect_board = pygame.Rect(self._rect_center.x + 20, self._rect_center.y + 230, 680, 210)
        self._rect_hand = pygame.Rect(self._rect_center.x + 20, self._rect_center.y + 460, 680, 200)

        self._rect_leaderboard = pygame.Rect(self._rect_right.x + 10, self._rect_right.y + 20, 220, 400)
        self._rect_log = pygame.Rect(self._rect_right.x + 10, self._rect_right.y + 440, 220, 210)

        shop_x = self._rect_shop.x + 10
        shop_y = self._rect_shop.y + 40
        self._shop_slots = [CardSlot(pygame.Rect(shop_x + i * 165, shop_y, 155, 140)) for i in range(4)]

        board_x = self._rect_board.x + 10
        board_y = self._rect_board.y + 45
        self._board_slots = [CardSlot(pygame.Rect(board_x + i * 98, board_y, 90, 140)) for i in range(7)]

        hand_x = self._rect_hand.x + 10
        hand_y = self._rect_hand.y + 45
        self._hand_slots = [CardSlot(pygame.Rect(hand_x + i * 68, hand_y, 62, 110)) for i in range(10)]

        bx = self._rect_controls.x
        by = self._rect_controls.y
        bw = self._rect_controls.w

        self._btn_refresh = Btn("Refresh", pygame.Rect(bx, by + 0, bw, 42), self.refresh_shop)
        self._btn_freeze = Btn("Freeze", pygame.Rect(bx, by + 52, bw, 42), self.toggle_freeze)
        self._btn_upgrade = Btn("Upgrade", pygame.Rect(bx, by + 104, bw, 42), self.upgrade_tavern)
        self._btn_hero = Btn("Hero Power", pygame.Rect(bx, by + 156, bw, 42), self.use_hero_power)
        self._btn_end = Btn("End Turn", pygame.Rect(bx, by + 208, bw, 52), self.end_turn)

        self._buttons: List[Btn] = [
            self._btn_refresh,
            self._btn_freeze,
            self._btn_upgrade,
            self._btn_hero,
            self._btn_end,
        ]

        self._cached_bg = None
        try:
            self._cached_bg = pygame.transform.smoothscale(self._board_bg, (w, h))
        except Exception:
            self._cached_bg = None

    def _ensure_minimum_state(self) -> None:
        p = self.state.player
        if p.board is None:
            p.board = []
        # Normalize board to 7 slots (list may be variable-length or 7 with Nones)
        if len(p.board) < 7:
            p.board = (list(p.board) + [None] * 7)[:7]
        elif len(p.board) > 7:
            p.board = p.board[:7]
        if p.hand is None:
            p.hand = []
        if p.shop is None:
            p.shop = []
        if len(p.shop) == 0:
            p.shop = _make_mock_shop()

    def _mark_dirty(self) -> None:
        self._dirty_ui = True

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._discover_popup is not None:
            self._discover_popup.handle_event(event)
            return

        if self._drag_event_fn is not None:
            try:
                self._drag_event_fn(event, self._shop_slots, self._hand_slots, self._board_slots)
            except TypeError:
                try:
                    self._drag_event_fn(event)
                except Exception:
                    self._drag_event_fn = None
            except Exception:
                self._drag_event_fn = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in self._buttons:
                b.handle_event(event)

    def update(self, dt: float) -> None:
        if self._error_timer > 0:
            self._error_timer -= dt
            if self._error_timer <= 0:
                self._error_message = None

        if self._drag_update_fn is not None:
            try:
                self._drag_update_fn(dt)
            except Exception:
                self._drag_update_fn = None

        self._sync_ui_if_needed()

    def render(self, surface: pygame.Surface) -> None:
        if self._cached_bg is not None:
            surface.blit(self._cached_bg, (0, 0))
        else:
            surface.fill((12, 12, 18))

        self._draw_panel(surface, self._rect_left, "Player")
        self._draw_panel(surface, self._rect_center, "Recruit")
        self._draw_panel(surface, self._rect_right, "Info")

        self._render_left(surface)
        self._render_center(surface)
        self._render_right(surface)

        if self._drag_render_fn is not None:
            try:
                self._drag_render_fn(surface, self._font)
            except TypeError:
                try:
                    self._drag_render_fn(surface)
                except Exception:
                    self._drag_render_fn = None
            except Exception:
                self._drag_render_fn = None

        if self._error_message:
            self._render_error(surface)

        if self._discover_popup is not None:
            self._discover_popup.render(surface, self._font)

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect, title: str) -> None:
        pygame.draw.rect(surface, (18, 18, 28), rect, border_radius=14)
        pygame.draw.rect(surface, (60, 60, 90), rect, width=2, border_radius=14)
        t = self._title_font.render(title, True, (235, 235, 245))
        surface.blit(t, (rect.x + 14, rect.y + 10))

    def _render_left(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (14, 14, 22), self._rect_hero, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_hero, 1, border_radius=12)

        if self._hero_portrait is not None:
            surface.blit(self._hero_portrait, (self._rect_hero.x + 30, self._rect_hero.y + 15))

        p = self.state.player
        hero_name = getattr(p, "hero_name", None) or "Hero"
        name = getattr(p, "name", None) or "Player"

        surface.blit(self._font_bold.render(str(name), True, (240, 240, 240)), (self._rect_hero.x + 12, self._rect_hero.y + 132))
        surface.blit(self._font.render(str(hero_name), True, (200, 200, 220)), (self._rect_hero.x + 12, self._rect_hero.y + 152))

        pygame.draw.rect(surface, (14, 14, 22), self._rect_stats, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_stats, 1, border_radius=12)

        lines = [
            f"Turn: {self.state.turn}",
            f"HP: {getattr(p, 'health', 30)}",
            f"Gold: {getattr(p, 'gold', 0)}/{getattr(p, 'max_gold', 0)}",
            f"Tavern: {getattr(p, 'tavern_tier', 1)}",
            f"Upgrade: {self.state.upgrade_cost}",
        ]
        y = self._rect_stats.y + 14
        for s in lines:
            surface.blit(self._font.render(s, True, (230, 230, 235)), (self._rect_stats.x + 12, y))
            y += 26

        pygame.draw.rect(surface, (14, 14, 22), self._rect_controls, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_controls, 1, border_radius=12)

        for b in self._buttons:
            b.render(surface, self._font)

        if self._hero_power_icon is not None:
            icon_rect = pygame.Rect(self._btn_hero.rect.x + 10, self._btn_hero.rect.y + 6, 40, 40)
            surface.blit(self._hero_power_icon, icon_rect)

    def _render_center(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (14, 14, 22), self._rect_shop, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_shop, 1, border_radius=12)
        surface.blit(self._font_bold.render("Shop", True, (230, 230, 240)), (self._rect_shop.x + 12, self._rect_shop.y + 10))

        for slot in self._shop_slots:
            slot.render(surface, self._font)

        pygame.draw.rect(surface, (14, 14, 22), self._rect_board, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_board, 1, border_radius=12)
        surface.blit(self._font_bold.render("Board", True, (230, 230, 240)), (self._rect_board.x + 12, self._rect_board.y + 10))

        for slot in self._board_slots:
            slot.render(surface, self._font)

        pygame.draw.rect(surface, (14, 14, 22), self._rect_hand, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_hand, 1, border_radius=12)
        surface.blit(self._font_bold.render("Hand", True, (230, 230, 240)), (self._rect_hand.x + 12, self._rect_hand.y + 10))

        for slot in self._hand_slots:
            slot.render(surface, self._font)

    def _render_right(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (14, 14, 22), self._rect_leaderboard, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_leaderboard, 1, border_radius=12)
        surface.blit(self._font_bold.render("Leaderboard", True, (230, 230, 240)), (self._rect_leaderboard.x + 12, self._rect_leaderboard.y + 10))

        self._leaderboard.render(surface, self._font)

        pygame.draw.rect(surface, (14, 14, 22), self._rect_log, border_radius=12)
        pygame.draw.rect(surface, (55, 55, 80), self._rect_log, 1, border_radius=12)
        surface.blit(self._font_bold.render("Tips", True, (230, 230, 240)), (self._rect_log.x + 12, self._rect_log.y + 10))

        tips = [
            "Drag shop -> hand to buy",
            "Drag hand -> board to play",
            "Drag board -> left to sell",
            "Freeze keeps shop",
        ]
        y = self._rect_log.y + 40
        for t in tips:
            surface.blit(self._font.render(t, True, (195, 195, 210)), (self._rect_log.x + 12, y))
            y += 22

    def _render_error(self, surface: pygame.Surface) -> None:
        msg = self._error_message or ""
        rect = pygame.Rect(270, 12, 720, 28)
        pygame.draw.rect(surface, (70, 20, 20), rect, border_radius=10)
        pygame.draw.rect(surface, (200, 80, 80), rect, 1, border_radius=10)
        text = self._font.render(msg, True, (255, 220, 220))
        surface.blit(text, (rect.x + 12, rect.y + 6))

    def _sync_ui_if_needed(self) -> None:
        p = self.state.player
        board_7 = (list(p.board) + [None] * 7)[:7]

        shop_sig = tuple((s.minion.card_id if s.minion else None, bool(getattr(s, "frozen", False))) for s in p.shop)
        hand_sig = tuple(getattr(m, "card_id", None) for m in p.hand)
        board_sig = tuple(getattr(m, "card_id", None) if m is not None else None for m in board_7)

        if (
            not self._dirty_ui
            and getattr(p, "gold", 0) == self._last_gold
            and self.state.shop_frozen == self._last_shop_frozen
            and shop_sig == self._last_shop_sig
            and hand_sig == self._last_hand_sig
            and board_sig == self._last_board_sig
        ):
            return

        for i in range(4):
            slot = p.shop[i] if i < len(p.shop) else None
            self._shop_slots[i].set_shop_slot(slot)

        for i in range(10):
            if i < len(p.hand):
                self._hand_slots[i].set_minion(p.hand[i])
            else:
                self._hand_slots[i].set_empty()

        for i in range(7):
            self._board_slots[i].set_minion(board_7[i] if i < len(board_7) else None)

        self._leaderboard.players = [p]

        self._last_gold = getattr(p, "gold", 0)
        self._last_shop_frozen = self.state.shop_frozen
        self._last_shop_sig = shop_sig
        self._last_hand_sig = hand_sig
        self._last_board_sig = board_sig
        self._dirty_ui = False

    def refresh_shop(self) -> None:
        p = self.state.player
        if self.state.shop_frozen:
            self._show_error("Shop is frozen.")
            return
        if getattr(p, "gold", 0) < REFRESH_COST:
            self._show_error("Not enough gold.")
            return

        p.gold -= REFRESH_COST
        p.shop = _make_mock_shop()
        self._mark_dirty()
        self._on_action({"action": "REFRESH", "cost": REFRESH_COST})

    def toggle_freeze(self) -> None:
        self.state.shop_frozen = not self.state.shop_frozen
        for s in self.state.player.shop:
            try:
                s.frozen = self.state.shop_frozen
            except Exception:
                pass
        self._mark_dirty()
        self._on_action({"action": "FREEZE", "frozen": self.state.shop_frozen})

    def upgrade_tavern(self) -> None:
        p = self.state.player
        if getattr(p, "tavern_tier", 1) >= 6:
            self._show_error("Max tier.")
            return
        if getattr(p, "gold", 0) < self.state.upgrade_cost:
            self._show_error("Not enough gold.")
            return

        p.gold -= self.state.upgrade_cost
        p.tavern_tier += 1

        next_cost, _ = TAVERN_UPGRADE_TABLE.get(p.tavern_tier, (0, 0))
        self.state.upgrade_cost = next_cost

        self._mark_dirty()
        self._on_action({"action": "UPGRADE", "tier": p.tavern_tier, "gold": p.gold, "upgrade_cost": self.state.upgrade_cost})

    def end_turn(self) -> None:
        self.state.turn += 1
        p = self.state.player
        p.max_gold = min(MAX_GOLD, 3 + (self.state.turn - 1))
        p.gold = p.max_gold
        if hasattr(p, "hero_power_used"):
            p.hero_power_used = False

        if not self.state.shop_frozen:
            p.shop = _make_mock_shop()

        self._mark_dirty()
        self._on_action({"action": "END_TURN", "turn": self.state.turn, "gold": p.gold, "upgrade_cost": self.state.upgrade_cost})

    def _buy_from_shop(self, index: int) -> None:
        p = self.state.player
        if index >= len(p.shop):
            return
        slot = p.shop[index]
        if slot is None or slot.minion is None:
            return
        if getattr(p, "gold", 0) < BUY_COST:
            self._show_error("Not enough gold.")
            return
        if len(p.hand) >= 10:
            self._show_error("Hand is full.")
            return

        expected_card_id = slot.minion.card_id
        p.gold -= BUY_COST
        p.hand.append(slot.minion)
        p.shop[index] = ShopSlot(slot=index, minion=None, frozen=self.state.shop_frozen, cost=BUY_COST, sim_tier=getattr(p, "tavern_tier", 1))

        self._mark_dirty()
        self._on_action({"action": "BUY_MINION", "payload": {"shop_slot": index, "expected_card_id": expected_card_id}})

    def _play_from_hand(self, hand_index: int, board_index: int) -> None:
        p = self.state.player
        if hand_index >= len(p.hand):
            return
        board_7 = (list(p.board) + [None] * 7)[:7]
        if sum(1 for m in board_7 if m is not None) >= 7:
            self._show_error("Board is full.")
            return

        m = p.hand.pop(hand_index)
        slot = min(max(0, board_index), 6)
        p.board = board_7
        p.board[slot] = m

        self._mark_dirty()
        self._on_action({"action": "PLAY", "hand_index": hand_index, "board_index": slot, "card_id": m.card_id})

    def _sell_from_board(self, index: int) -> None:
        p = self.state.player
        board_7 = (list(p.board) + [None] * 7)[:7]
        if index < 0 or index >= len(board_7):
            return
        m = board_7[index]
        if m is None:
            return
        board_7[index] = None
        p.board = board_7
        p.gold = min(MAX_GOLD, getattr(p, "gold", 0) + SELL_GAIN)

        self._mark_dirty()
        self._on_action({"action": "SELL", "board_index": index, "card_id": m.card_id, "gain": SELL_GAIN})

    def use_hero_power(self) -> None:
        p = self.state.player
        if getattr(p, "hero_power_used", False):
            self._show_error("Hero Power already used.")
            return
        if getattr(p, "gold", 0) < HERO_POWER_COST:
            self._show_error("Not enough gold.")
            return

        if hasattr(p, "hero_power_used"):
            p.hero_power_used = True
        p.gold -= HERO_POWER_COST

        self._mark_dirty()
        self._on_action({"action": "HERO_POWER", "hero_id": getattr(p, "hero_id", "unknown"), "cost": HERO_POWER_COST, "gold": p.gold})

    def _show_error(self, message: str, duration: float = 1.5) -> None:
        self._error_message = message
        self._error_timer = duration


def make_recruit_screen(
    on_action: Callable[[dict], None],
    set_screen: Callable[[str], None] | None = None,
) -> RecruitScreen:
    return RecruitScreen(
        RecruitState(player=_make_mock_player()),
        on_action,
        set_screen=set_screen,
    )


def _make_mock_player() -> Player:
    p = Player(player_id="local", name="Player", hero_id="HERO_SYLVANAS", hero_name="Sylvanas")
    p.health = 30
    p.gold = 3
    p.max_gold = 3
    p.tavern_tier = 1
    p.tavern_upgrade_cost = 5
    p.board = []
    p.hand = []
    p.shop = _make_mock_shop()
    return p


def _make_mock_shop() -> List[ShopSlot]:
    return [
        ShopSlot(slot=0, minion=Minion("BG_MURLOC_001", "Murloc", 2, 1, 1)),
        ShopSlot(slot=1, minion=Minion("BG_TAUNT_001", "Taunt", 1, 3, 1)),
        ShopSlot(slot=2, minion=Minion("BG_DRAGON_001", "Dragon", 3, 2, 1)),
        ShopSlot(slot=3, minion=Minion("BG_BEAST_001", "Beast", 2, 2, 1)),
    ]
