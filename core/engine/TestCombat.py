import pygame
import sys
import random
from minion import Minion
from combat import CombatEngine

pygame.init()

WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Combat Step-by-Step Test")

font = pygame.font.SysFont("Arial", 20)
clock = pygame.time.Clock()

engine = CombatEngine()

# Board A
board_a = [
    Minion("A1", 3, 2, 1),
    Minion("A2", 2, 3, 1),
    Minion("A3", 1, 5, 1),
]

# Board B
board_b = [
    Minion("B1", 4, 2, 1),
    Minion("B2", 2, 4, 1),
]

# وضعیت جنگ
combat_running = False
combat_finished = False
turn = None  # "A" یا "B"

def draw_board(board, x_start, y):
    for i, m in enumerate(board):
        x = x_start + i * 120
        color = (0, 200, 0) if m.is_alive() else (200, 0, 0)

        pygame.draw.rect(screen, color, (x, y, 100, 120))
        pygame.draw.rect(screen, (0, 0, 0), (x, y, 100, 120), 2)

        name_text = font.render(m.name, True, (0, 0, 0))
        stats_text = font.render(f"{m.attack} / {m.health}", True, (0, 0, 0))

        screen.blit(name_text, (x + 5, y + 10))
        screen.blit(stats_text, (x + 10, y + 70))

# انتخاب طرف شروع
def decide_first_turn():
    if len(board_a) > len(board_b):
        return "A"
    elif len(board_b) > len(board_a):
        return "B"
    else:
        return random.choice(["A", "B"])

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if not combat_running and not combat_finished:
                    combat_running = True
                    turn = decide_first_turn()

    if combat_running:
        # Step-by-step: هر فریم یک حمله
        if engine._has_alive(board_a) and engine._has_alive(board_b):
            if turn == "A":
                engine._single_attack(board_a, board_b)
                turn = "B"
            else:
                engine._single_attack(board_b, board_a)
                turn = "A"

            engine._cleanup(board_a)
            engine._cleanup(board_b)
        else:
            combat_running = False
            combat_finished = True

    # رسم صفحه
    screen.fill((30, 30, 30))
    title = font.render("Press SPACE to start combat (Step-by-step)", True, (255, 255, 255))
    screen.blit(title, (20, 20))

    # Boardها سمت چپ
    label_a = font.render("Board A", True, (255, 255, 0))
    screen.blit(label_a, (50, 70))
    label_b = font.render("Board B", True, (255, 255, 0))
    screen.blit(label_b, (50, 300))
    draw_board(board_a, 50, 100)
    draw_board(board_b, 50, 330)

    # Board نهایی سمت راست بعد از Combat
    if combat_finished:
        result_label = font.render("AFTER COMBAT", True, (255, 255, 255))
        screen.blit(result_label, (500, 70))
        draw_board(board_a, 500, 100)
        draw_board(board_b, 500, 330)

    pygame.display.flip()
    clock.tick(2)  # سرعت اجرای هر حمله: 2 فریم بر ثانیه (می‌توانی تغییر بدهی)

pygame.quit()
sys.exit()
