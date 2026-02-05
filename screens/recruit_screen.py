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

# Simple local minion pool for offline shop rolls
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


class RecruitScreen:
    def __init__(self, state: RecruitState, on_action: Callable[[dict], None]) -> None:
        self.state = state
        self._on_action = on_action
        self._font = pygame.font.SysFont("Arial", 18)
        self.btn : List[Btn] = []  
        self._build_layout()
        self._drag = DragManager(
            on_buy=self._buy_from_shop,
            on_play=self._play_from_hand,
            on_sell=self._sell_from_board,
        )

    def _build_layout(self)->None:
        self._shop_slots = [CardSlot(pygame.Rect(40+i*130 , 80,120,160)) for i in range(4)]
        self._hand_slots = [CardSlot(pygame.Rect(40+i*110, 520, 100, 140)) for i in range(10)]
        self._board_slots = [CardSlot(pygame.Rect(40+i*130, 300,120,160)) for i in range(7)]


        refresh_button = Btn("Refresh",
        pygame.Rect(620,80,120,36),
        one_click=self.refresh_shop, 
        )
        freez_button = Btn(
            "Freez",
            pygame.Rect(620,130,120,36),
            one_click=self.toggle_freez,
        )
        end_turn_button = Btn(
            "End Turn",
            pygame.Rect(620,180,120,36),
            one_click=self.end_turn,
        )
        self._buttons = [refresh_button,freez_button,end_turn_button]

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
    
    def render(self, surface: pygame.Surface)->None:
        surface.fill((18, 18, 28))

        p = self.state.player
        header = f"{p.name} | HP {p.health} | Gold {p.gold} | Tier {p.tavern_tier} | Turn {self.state.turn}"
        header_surf = self._font.render(header, True, (245, 245, 245))
        surface.blit(header_surf, (40, 24))

        shop_label = self._font.render("Shop", True, (220, 220, 240))
        board_label = self._font.render("Board", True, (220, 220, 240))
        hand_label = self._font.render("Hand", True, (220, 220, 240))
        surface.blit(shop_label, (40, 56))
        surface.blit(board_label, (40, 276))
        surface.blit(hand_label, (40, 496))

        for slot in self._shop_slots:
            slot.render(surface, self._font)
        for slot in self._board_slots:
            slot.render(surface, self._font)
        for slot in self._hand_slots:
            slot.render(surface, self._font)

        for button in self._buttons:
            button.render(surface, self._font)

        self._drag.render(surface, self._font)


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

        # Rolling new shop: keep frozen cards, reroll others.
        # After refresh, freeze is cleared (one-turn effect).
        if not p.shop:
            # Ensure we have a fixed number of slots
            p.shop = [ShopSlot(slot=i, minion=None, frozen=False) for i in range(4)]

        for slot in p.shop:
            if slot.frozen and slot.minion is not None:
                # Keep as-is but clear frozen after use
                slot.frozen = False
                continue

            # Reroll this slot
            template = _SHOP_POOL[(slot.slot or 0) % len(_SHOP_POOL)]
            # Create a fresh copy so stats are independent
            slot.minion = copy.deepcopy(template)
            slot.frozen = False

        self.state.shop_frozen = False

        self._on_action({"action": "REFRESH", "cost": REFRESH_COST})

    def toggle_freez(self) -> None:
        p = self.state.player
        self.state.shop_frozen = not self.state.shop_frozen

        # Toggle freeze flag on current shop slots
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
        self._on_action({"action": "END_TURN"})


    def _buy_from_shop(self, index: int) -> None:
        p = self.state.player
        if index >= len(p.shop):
            return

        slot = p.shop[index]
        if slot.minion is None:
            return
        if p.gold < BUY_COST:
            return
        if len(p.hand) >= 10:
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


def make_recruit_screen(on_action: Callable[[dict], None]) -> RecruitScreen:
    """Helper used by the App for now (offline/dev)."""
    return RecruitScreen(RecruitState(player=_make_mock_player()), on_action)