import copy
import random

class CombatEngine:
    def __init__(self):
        pass

    def fight(self, board_a , board_b):
        a = copy.deepcopy(board_a)
        b = copy.deepcopy(board_b)

        turn = self._decide_first_turn(a, b)

        while self._has_alive(a) and self._has_alive(b):
            if turn == "A":
                self._single_attack(a,b)
                turn = "B"
            else:
                self._single_attack(b,a)
                turn = "A"
        self._cleanup(a)
        self._cleanup(b)

        return a , b





    def _decide_first_turn(self, board_a, board_b):
        if len(board_a) > len(board_b):
            return "A"
        elif len(board_a) > len(board_b):
            return "B"
        else:
            return random.choice(["A", "B"])

    def _has_alive(self, board):
        return any(m.is_alive for m in board)

    def _single_attack(self, attackers, defenders):

        attacker = None
        for m in attackers:
            if m.is_alive():
                attacker = m
                break
        if attacker is None:
            return

        alive_defenders = [m for m in defenders if m.is_alive()]
        if not alive_defenders:
            return

        defender = random.choice(alive_defenders)

        defender.health -= attacker.attack
        attacker.health -= defender.attack

    def _cleanup(self,board):
        board[:] = [m for m in board if m.is_alive()]