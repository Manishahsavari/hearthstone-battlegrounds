from __future__ import annotations
from ast import Call
from dataclasses import dataclass
from typing import Callable, List
import pygame
from common.models import Minion, Player,ShopSlot
from components.btn import Btn
from components.card_slot import CardSlot


MAX_GOLD = 10
BUY_COST = 3
SELL_GAIN = 1
REFRESH_COST = 1
FREEZ_COST = 0

@dataclass
class RecruitState:
    player : Player
    turn : int =  1
    shop_frozen: bool = False

class RecruitScreen:
    def __init__(self, state: RecruitScreen, on_action : Callable[[dict],None]) -> None:
        self.state = state
        self._on_action = on_action
        self._font = pygame.font.SysFont("Arial", 18)
        self.btn : List[Btn] = []
        

    def _build_layout(self)->None:
        self._shop_slots = [CardSlot(pygame.Rect(40+i*130 , 80,120,160)) for i in range(4)]
        self._hand_slots = [CardSlot(pygame.Rect(40+i*110, 520, 100, 140)) for i in range(10)]
        self._board_slots = [CardSlot(pygame.Rect(40+i*130, 300,120,160)) for i in range(7)]


        refresh_button = Btn("Refresh",
        pygame.Rect(620,80,120,36)
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
    

    def update(self, dt:float)->None:
        self._sync_slots()
    
    def render(self, surface: pygame.Surface)->None:
        