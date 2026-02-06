from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional
import copy
import pygame

from common.models import Minion, Player, ShopSlot, Keyword
from components.btn import Btn
from components.card_slot import CardSlot
from components.leaderboard_panel import LeaderboardPanel
from components.popup_choice import PopupChoice
from services.drag_manager import DragManager
from services.asset_loader import load_hero_portrait, load_hero_power_icon


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
        self._error_message: Optional[str] = None
        self._error_timer: float = 0.0
        self.btn : List[Btn] = []  
        self._hero_portrait = load_hero_portrait("HERO_SYLVANAS", (140, 140))
        self._hero_power_icon = load_hero_power_icon("HERO_SYLVANAS", (44, 44))
        self._build_layout()
        self._drag = DragManager(
            on_buy=self._buy_from_shop,
            on_play=self._play_from_hand,
            on_sell=self._sell_from_board,
        )

    def _build_layout(self)->None:
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
        test_discover_btn = Btn(
            "Test Discover",
            pygame.Rect(760, 170, 140, 36),
            one_click=self._show_test_discover,
        )
        self._hero_rect = pygame.Rect(24, 56, 200, 300)
        self._hero_power_button = Btn(
            "Hero Power",
            pygame.Rect(self._hero_rect.centerx - 32, self._hero_rect.y + 200, 64, 64),
            one_click=self.use_hero_power,
        )
        view_combat_button = Btn(
            "View Combat",
            pygame.Rect(760, 130, 140, 36),
            one_click=lambda: self._set_screen("combat_viewer"),
        )

        self._buttons = [
            refresh_button,
            freez_button,
            end_turn_button,
            upgrade_button,
            self._hero_power_button,
            view_combat_button,
            test_discover_btn,
        ]

        self._leaderboard = LeaderboardPanel(
            rect=pygame.Rect(920, 80, 240, 220),
        )
        self._discover_popup: Optional[PopupChoice] = None

    def handle_event(self, event: pygame.event.Event)->None:
        if self._discover_popup and self._discover_popup.visible:
            if self._discover_popup.handle_event(event):
                return
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
    

    def update(self, dt: float) -> None:
        self._sync_slots()
        self._sync_leaderboard()
        if self._error_timer > 0:
            self._error_timer -= dt
            if self._error_timer <= 0:
                self._error_message = None
    
    def _render_hero_panel(self, surface: pygame.Surface, p: Player) -> None:
        """Draw HS-style hero panel: circular portrait, health/gold gems, hero power."""
        hero_rect = self._hero_rect
        panel_bg = (35, 28, 22)
        gold_border = (200, 170, 90)
        pygame.draw.rect(surface, panel_bg, hero_rect, border_radius=20)
        pygame.draw.rect(surface, gold_border, hero_rect, width=3, border_radius=20)

        name_surf = self._font.render(p.name or "Sylvanas", True, (255, 248, 220))
        name_rect = name_surf.get_rect(centerx=hero_rect.centerx, top=hero_rect.y + 12)
        surface.blit(name_surf, name_rect)

        portrait_radius = 58
        portrait_center = (hero_rect.centerx, hero_rect.y + 100)
        if self._hero_portrait:
            size = portrait_radius * 2
            final = pygame.Surface((size, size), pygame.SRCALPHA)
            scaled = pygame.transform.smoothscale(self._hero_portrait, (size, size))
            final.blit(scaled, (0, 0))
            cookie = pygame.Surface((size, size), pygame.SRCALPHA)
            cookie.fill((0, 0, 0, 0))
            pygame.draw.circle(cookie, (255, 255, 255, 255), (portrait_radius, portrait_radius), portrait_radius)
            final.blit(cookie, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(final, final.get_rect(center=portrait_center))
        pygame.draw.circle(surface, (60, 50, 30), portrait_center, portrait_radius + 4)
        pygame.draw.circle(surface, gold_border, portrait_center, portrait_radius + 2, width=3)
        pygame.draw.circle(surface, (140, 120, 60), portrait_center, portrait_radius, width=1)

        hp_center = (hero_rect.centerx - 28, hero_rect.y + 168)
        pygame.draw.circle(surface, (80, 20, 20), hp_center, 18)
        pygame.draw.circle(surface, (200, 60, 60), hp_center, 16)
        hp_font = pygame.font.SysFont("Arial", 22, bold=True)
        hp_surf = hp_font.render(str(p.health), True, (255, 255, 255))
        surface.blit(hp_surf, hp_surf.get_rect(center=hp_center))

        gold_center = (hero_rect.centerx + 28, hero_rect.y + 168)
        pygame.draw.circle(surface, (20, 40, 80), gold_center, 18)
        pygame.draw.circle(surface, (70, 130, 200), gold_center, 16)
        gold_surf = hp_font.render(str(p.gold), True, (255, 255, 255))
        surface.blit(gold_surf, gold_surf.get_rect(center=gold_center))
        tier_surf = self._font.render(f"T{p.tavern_tier}", True, (200, 220, 255))
        surface.blit(tier_surf, (gold_center[0] - 12, gold_center[1] + 22))

        hp_btn = self._hero_power_button
        hp_center_btn = hp_btn.rect.center
        pygame.draw.circle(surface, (40, 35, 55), hp_center_btn, 30)
        pygame.draw.circle(surface, gold_border, hp_center_btn, 30, width=2)
        pygame.draw.circle(surface, (90, 75, 50), hp_center_btn, 28, width=1)
        if self._hero_power_icon:
            icon_rect = self._hero_power_icon.get_rect(center=hp_center_btn)
            surface.blit(self._hero_power_icon, icon_rect)
        else:
            label = self._font.render("HP", True, (255, 248, 220))
            surface.blit(label, label.get_rect(center=hp_center_btn))
        cost_rect = pygame.Rect(hp_btn.rect.right - 18, hp_btn.rect.y + 2, 16, 16)
        pygame.draw.circle(surface, (70, 130, 200), cost_rect.center, 8)
        cost_surf = self._font.render("1", True, (255, 255, 255))
        surface.blit(cost_surf, cost_surf.get_rect(center=cost_rect.center))

    def render(self, surface: pygame.Surface)->None:
        w, h = surface.get_width(), surface.get_height()
        for y in range(0, h, 4):
            t = y / max(h, 1)
            r = int(18 + t * 12)
            g = int(22 + t * 10)
            b = int(20 + t * 8)
            pygame.draw.rect(surface, (r, g, b), (0, y, w, 4))
        board_rect = pygame.Rect(200, 48, w - 440, h - 96)
        board_color = (52, 42, 35)
        pygame.draw.rect(surface, board_color, board_rect, border_radius=16)
        pygame.draw.rect(surface, (80, 65, 45), board_rect, width=1, border_radius=16)
        pygame.draw.rect(surface, (140, 110, 70), board_rect, width=2, border_radius=16)

        p = self.state.player
        header = (
            f"Turn {self.state.turn}  ·  Upgrade {self.state.upgrade_cost}g"
        )
        header_surf = self._font.render(header, True, (220, 210, 180))
        surface.blit(header_surf, (board_rect.x + 20, 16))
        turn_banner_rect = pygame.Rect(board_rect.right - 140, board_rect.y + 8, 120, 32)
        pygame.draw.rect(surface, (60, 55, 45), turn_banner_rect, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 90), turn_banner_rect, width=1, border_radius=6)
        turn_surf = pygame.font.SysFont("Arial", 18, bold=True).render("YOUR TURN", True, (255, 248, 200))
        surface.blit(turn_surf, turn_surf.get_rect(center=turn_banner_rect.center))

        self._render_hero_panel(surface, p)

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
            if button is self._hero_power_button:
                continue  
            button.render(surface, self._font)

        self._leaderboard.render(surface, self._font)
        self._drag.render(surface, self._font)
        if self._discover_popup and self._discover_popup.visible:
            self._discover_popup.render(surface, self._font)

        if self._error_message:
            msg_surf = self._font.render(self._error_message, True, (255, 80, 80))
            rect = msg_surf.get_rect(center=(surface.get_width() // 2, 460))
            bg_rect = rect.inflate(16, 8)
            pygame.draw.rect(surface, (40, 20, 20), bg_rect, border_radius=8)
            pygame.draw.rect(surface, (200, 80, 80), bg_rect, width=2, border_radius=8)
            surface.blit(msg_surf, rect)


    def _sync_leaderboard(self) -> None:
        p = self.state.player
        opponents = [
            Player(player_id="p2", name="Opp 2", hero_name="Lich King", health=28, tavern_tier=2),
            Player(player_id="p3", name="Opp 3", hero_name="Millhouse", health=25, tavern_tier=1),
            Player(player_id="p4", name="Opp 4", hero_name="Yogg", health=30, tavern_tier=1),
        ]
        p_display = Player(
            player_id=p.player_id,
            name=p.name,
            hero_name="Sylvanas" if "SYLVANAS" in (p.hero_id or "").upper() else p.hero_id or "Hero",
            health=p.health,
            tavern_tier=p.tavern_tier,
        )
        self._leaderboard.update_players([p_display] + opponents)

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
            self._show_error("Not enough gold to refresh.")
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

    def _play_from_hand(self, hand_index: int, board_index: int) -> None:
        p = self.state.player
        if hand_index >= len(p.hand):
            return
        if len(p.board) >= len(self._board_slots):
            self._show_error("Board is full.")
            return

        minion = p.hand.pop(hand_index)
        # Place at dropped slot (clamp to valid range)
        slot = min(board_index, len(p.board))
        p.board.insert(slot, minion)

        self._on_action(
            {
                "action": "PLAY",
                "hand_index": hand_index,
                "board_index": slot,
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

    def _show_test_discover(self) -> None:
        """Show Discover popup for testing (Triple reward simulation)."""
        opts = [
            Minion("BG_OPT_1", "Option A", 2, 2, 2),
            Minion("BG_OPT_2", "Option B", 3, 1, 2),
            Minion("BG_OPT_3", "Option C", 1, 4, 2),
        ]

        def on_pick(idx: int) -> None:
            m = opts[idx]
            p = self.state.player
            if len(p.hand) < 10:
                p.hand.append(m)
            self._on_action({"action": "DISCOVER_CHOICE", "card_id": m.card_id, "index": idx})

        self._discover_popup = PopupChoice(
            rect=pygame.Rect(340, 220, 400, 220),
            options=opts,
            on_choice=on_pick,
            title="Discover a minion",
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


def make_recruit_screen(
    on_action: Callable[[dict], None],
    set_screen: Callable[[str], None] | None = None,
) -> RecruitScreen:
    """Helper used by the App for now (offline/dev)."""
    return RecruitScreen(
        RecruitState(player=_make_mock_player()),
        on_action,
        set_screen=set_screen,
    )