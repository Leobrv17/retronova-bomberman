import pygame
from contantes import *

class Explosion:
    def __init__(self, x, y, duration):
        self.x = x
        self.y = y
        self.duration = duration * FPS  # Convertir en frames
        self.timer = self.duration
        self.max_radius = TILE_SIZE // 2

    def update(self):
        self.timer -= 1

    def is_finished(self):
        return self.timer <= 0

    def draw(self, screen, offset_x, offset_y):
        # Calculer la taille de l'explosion en fonction du temps restant
        progress = self.timer / self.duration
        radius = int(self.max_radius * progress)

        # Dessiner l'explosion (cercle jaune qui rétrécit)
        rect = pygame.Rect(
            offset_x + self.x * TILE_SIZE,
            offset_y + self.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        pygame.draw.circle(screen, YELLOW, rect.center, radius)
        pygame.draw.circle(screen, RED, rect.center, radius // 2)
