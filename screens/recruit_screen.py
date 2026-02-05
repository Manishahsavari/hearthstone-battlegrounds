from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional
import copy
import pygame

from common.models import Minion, Player, ShopSlot, Keyword
from components.btn import Btn
from components.card_slot import CardSlot
from services.drag_manager import DragManager


MAX_GOLD = 10
BUY_COST = 3
SELL_GAIN = 1
REFRESH_COST = 1
FREEZ_COST = 0
HERO_POWER_COST = 1

TAVERN_UPGRADE_TABLE: dict[int, tuple[int, int]] = {
    1: (5, 2),
    2: (7, 4),
    3: (8, 5),
    4: (9, 6),
}
TAVERN_MAX_TIER = 4

_SHOP_POOL: list[Minion] = [
    Minion(card_id="BG_MURLOC_001", name="Murloc", attack=2, health=1, tier=1),
    Minion(card_id="BG_DRAGON_001", name="Dragon", attack=3, health=4, tier=1),
    Minion(card_id="BG_TAUNT_001", name="Taunt Guy", attack=1, health=6, tier=1),
]


def _make_mock_player() -> Player:
    """Temporary offline state until we load from mock JSON files."""
    murloc = Minion(card_id="BG_MURLOC_001", name="Murloc", attack=2, health=1, tier=1)
    dragon = Minion(card_id="BG_DRAGON_001", name="Dragon", attack=3, health=4, tier=1)
    taunt = Keyword(name="Taunt")
    tank = Minion(
        card_id="BG_TAUNT_001",
        name="Taunt Guy",
        attack=1,
        health=6,
        tier=1,
        keywords=[taunt],
    )

    p = Player(
        player_id="p1",
        name="Player 1",
        hero_id="HERO_SYLVANAS",
        health=30,
        gold=3,
        tavern_tier=1,
    )
    p.board = [tank, dragon]
    p.hand = [murloc]
    p.shop = [
        ShopSlot(slot=0, minion=murloc, frozen=False),
        ShopSlot(slot=1, minion=dragon, frozen=False),
        ShopSlot(slot=2, minion=tank, frozen=True),
        ShopSlot(slot=3, minion=None, frozen=False),
    ]
    return p


@dataclass
class RecruitState:
    player : Player
    turn : int =  1
    shop_frozen: bool = False
    upgrade_cost: int = TAVERN_UPGRADE_TABLE[1][0]


class RecruitScreen:
    def __init__(self, state: RecruitState, on_action: Callable[[dict], None]) -> None:
        self.state = state
        self._on_action = on_action
        self._font = pygame.font.SysFont("Arial", 18)
        self._error_message: Optional[str] = None
        self._error_timer: float = 0.0
        self.btn : List[Btn] = []  
        self._build_layout()
        self._drag = DragManager(
            on_buy=self._buy_from_shop,
            on_play=self._play_from_hand,
            on_sell=self._sell_from_board,
        )

    def _build_layout(self)->None:
        # Leave left side free for hero panel; start grid at x=240.
        grid_x = 240
        self._shop_slots = [
            CardSlot(pygame.Rect(grid_x + i * 130, 80, 120, 160)) for i in range(4)
        ]
        self._hand_slots = [
            CardSlot(pygame.Rect(grid_x + i * 110, 520, 100, 140)) for i in range(10)
        ]
        self._board_slots = [
            CardSlot(pygame.Rect(grid_x + i * 130, 300, 120, 160)) for i in range(7)
        ]


        refresh_button = Btn(
            "Refresh",
            pygame.Rect(620, 80, 120, 36),
            one_click=self.refresh_shop,
        )
        freez_button = Btn(
            "Freez",
            pygame.Rect(620, 130, 120, 36),
            one_click=self.toggle_freez,
        )
        end_turn_button = Btn(
            "End Turn",
            pygame.Rect(620, 180, 120, 36),
            one_click=self.end_turn,
        )
        upgrade_button = Btn(
            "Upgrade",
            pygame.Rect(760, 80, 140, 36),
            one_click=self.upgrade_tavern,
        )
        # Hero panel layout
        self._hero_rect = pygame.Rect(40, 80, 170, 260)
        self._hero_power_button = Btn(
            "Hero Power",
            pygame.Rect(self._hero_rect.x + 20, self._hero_rect.y + 150, 130, 40),
            one_click=self.use_hero_power,
        )

        self._buttons = [
            refresh_button,
            freez_button,
            end_turn_button,
            upgrade_button,
            self._hero_power_button,
        ]

    def handle_event(self, event: pygame.event.Event)->None:
        for button in self._buttons:
            button.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._drag.handle_mouse_down(
                event.pos,
                self._shop_slots,
                self._hand_slots,
                self._board_slots,
            )
        elif event.type == pygame.MOUSEMOTION:
            self._drag.handle_mouse_move(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag.handle_mouse_up(
                event.pos,
                self._shop_slots,
                self._hand_slots,
                self._board_slots,
            )
    

    def update(self, dt:float)->None:
        self._sync_slots()
        if self._error_timer > 0:
            self._error_timer -= dt
            if self._error_timer <= 0:
                self._error_message = None
    
    def render(self, surface: pygame.Surface)->None:
        surface.fill((18, 18, 28))

        p = self.state.player
        header = (
            f"{p.name} | HP {p.health} | Gold {p.gold} | "
            f"Tavern {p.tavern_tier} (Upgrade {self.state.upgrade_cost}g) | "
            f"Turn {self.state.turn}"
        )
        header_surf = self._font.render(header, True, (245, 245, 245))
        surface.blit(header_surf, (40, 24))

        hero_rect = self._hero_rect
        pygame.draw.rect(surface, (30, 30, 50), hero_rect, border_radius=16)
        pygame.draw.rect(surface, (200, 180, 80), hero_rect, width=2, border_radius=16)

        hero_name = self._font.render("Sylvanas", True, (245, 245, 245))
        surface.blit(hero_name, (hero_rect.x + 16, hero_rect.y + 14))

        big_font = pygame.font.SysFont("Arial", 32, bold=True)
        hp_surf = big_font.render(str(p.health), True, (220, 50, 50))
        surface.blit(hp_surf, (hero_rect.x + 20, hero_rect.y + 60))

        stats_line = self._font.render(
            f"{p.gold}g · T{p.tavern_tier}", True, (220, 220, 200)
        )
        surface.blit(stats_line, (hero_rect.x + 20, hero_rect.y + 110))

        # Hero power button (Btn) drawn here for layering
        self._hero_power_button.render(surface, self._font)

        shop_label = self._font.render("Shop", True, (220, 220, 240))
        board_label = self._font.render("Board", True, (220, 220, 240))
        hand_label = self._font.render("Hand", True, (220, 220, 240))
        surface.blit(shop_label, (240, 56))
        surface.blit(board_label, (240, 276))
        surface.blit(hand_label, (240, 496))

        for slot in self._shop_slots:
            slot.render(surface, self._font)
        for slot in self._board_slots:
            slot.render(surface, self._font)
        for slot in self._hand_slots:
            slot.render(surface, self._font)

        for button in self._buttons:
            button.render(surface, self._font)

        self._drag.render(surface, self._font)

        if self._error_message:
            msg_surf = self._font.render(self._error_message, True, (255, 80, 80))
            rect = msg_surf.get_rect(center=(surface.get_width() // 2, 460))
            bg_rect = rect.inflate(16, 8)
            pygame.draw.rect(surface, (40, 20, 20), bg_rect, border_radius=8)
            pygame.draw.rect(surface, (200, 80, 80), bg_rect, width=2, border_radius=8)
            surface.blit(msg_surf, rect)


    def _sync_slots(self) -> None:
        p = self.state.player

        for i, view in enumerate(self._shop_slots):
            slot: Optional[ShopSlot] = p.shop[i] if i < len(p.shop) else None
            view.set_shop_slot(slot)

        for i, view in enumerate(self._board_slots):
            if i < len(p.board):
                view.set_minion(p.board[i])
            else:
                view.set_empty()

        for i, view in enumerate(self._hand_slots):
            if i < len(p.hand):
                view.set_minion(p.hand[i])
            else:
                view.set_empty()


    def refresh_shop(self) -> None:
        p = self.state.player
        if p.gold < REFRESH_COST:
            return

        p.gold -= REFRESH_COST

        if not p.shop:
            p.shop = [ShopSlot(slot=i, minion=None, frozen=False) for i in range(4)]

        for slot in p.shop:
            if slot.frozen and slot.minion is not None:
                slot.frozen = False
                continue

            template = _SHOP_POOL[(slot.slot or 0) % len(_SHOP_POOL)]
            slot.minion = copy.deepcopy(template)
            slot.frozen = False

        self.state.shop_frozen = False

        self._on_action({"action": "REFRESH", "cost": REFRESH_COST})

    def toggle_freez(self) -> None:
        p = self.state.player
        self.state.shop_frozen = not self.state.shop_frozen

        for slot in p.shop:
            if slot.minion is None:
                slot.frozen = False
            else:
                slot.frozen = self.state.shop_frozen

        self._on_action(
            {
                "action": "FREEZE",
                "enabled": self.state.shop_frozen,
                "cost": FREEZ_COST,
            }
        )

    def end_turn(self) -> None:
        self.state.turn += 1

        base_gold = min(3 + (self.state.turn - 1), MAX_GOLD)
        self.state.player.gold = base_gold

        tier = self.state.player.tavern_tier
        if tier in TAVERN_UPGRADE_TABLE:
            base_cost, min_cost = TAVERN_UPGRADE_TABLE[tier]
            self.state.upgrade_cost = max(min_cost, self.state.upgrade_cost - 1)

        self._on_action(
            {
                "action": "END_TURN",
                "turn": self.state.turn,
                "gold": self.state.player.gold,
                "upgrade_cost": self.state.upgrade_cost,
            }
        )

    def upgrade_tavern(self) -> None:
        p = self.state.player
        if p.tavern_tier >= TAVERN_MAX_TIER:
            self._show_error("Tavern is already at max tier.")
            return

        cost = self.state.upgrade_cost
        if cost <= 0 or p.gold < cost:
            self._show_error("Not enough gold to upgrade.")
            return

        p.gold -= cost
        old_tier = p.tavern_tier
        p.tavern_tier += 1

        if p.tavern_tier in TAVERN_UPGRADE_TABLE:
            base_cost, _ = TAVERN_UPGRADE_TABLE[p.tavern_tier]
            self.state.upgrade_cost = base_cost

        self._on_action(
            {
                "action": "UPGRADE_TAVERN",
                "from_tier": old_tier,
                "to_tier": p.tavern_tier,
                "cost": cost,
                "gold": p.gold,
                "upgrade_cost": self.state.upgrade_cost,
            }
        )


    def _buy_from_shop(self, index: int) -> None:
        p = self.state.player
        if index >= len(p.shop):
            return

        slot = p.shop[index]
        if slot.minion is None:
            self._show_error("Empty shop slot.")
            return
        if p.gold < BUY_COST:
            self._show_error("Not enough gold to buy.")
            return
        if len(p.hand) >= 10:
            self._show_error("Hand is full.")
            return

        minion = slot.minion
        p.gold -= BUY_COST
        p.hand.append(minion)
        slot.minion = None
        slot.frozen = False

        self._on_action(
            {
                "action": "BUY",
                "shop_slot": index,
                "card_id": minion.card_id,
                "cost": BUY_COST,
            }
        )

    def _play_from_hand(self, index: int) -> None:
        p = self.state.player
        if index >= len(p.hand):
            return
        if len(p.board) >= len(self._board_slots):
            self._show_error("Board is full.")
            return

        minion = p.hand.pop(index)
        p.board.append(minion)

        self._on_action(
            {
                "action": "PLAY",
                "hand_index": index,
                "board_index": len(p.board) - 1,
                "card_id": minion.card_id,
            }
        )

    def _sell_from_board(self, index: int) -> None:
        p = self.state.player
        if index >= len(p.board):
            return

        minion = p.board.pop(index)
        p.gold = min(MAX_GOLD, p.gold + SELL_GAIN)

        self._on_action(
            {
                "action": "SELL",
                "board_index": index,
                "card_id": minion.card_id,
                "gain": SELL_GAIN,
            }
        )

    def use_hero_power(self) -> None:
        """Sylvanas hero power (simplified): buff board minions."""
        p = self.state.player
        if p.gold < HERO_POWER_COST:
            self._show_error("Not enough gold for Hero Power.")
            return

        if not p.board:
            self._show_error("No minions on board.")
            return

        p.gold -= HERO_POWER_COST

        for m in p.board:
            m.attack += 2
            m.health += 1

        self._on_action(
            {
                "action": "HERO_POWER",
                "hero_id": p.hero_id,
                "cost": HERO_POWER_COST,
                "gold": p.gold,
            }
        )

    def _show_error(self, message: str, duration: float = 1.5) -> None:
        self._error_message = message
        self._error_timer = duration


def make_recruit_screen(on_action: Callable[[dict], None]) -> RecruitScreen:
    """Helper used by the App for now (offline/dev)."""
    return RecruitScreen(RecruitState(player=_make_mock_player()), on_action)