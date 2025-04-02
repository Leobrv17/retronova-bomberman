import pygame
from contantes import *


class Bomb:
    def __init__(self, x, y, power, owner):
        self.x = x
        self.y = y
        self.power = power
        self.owner = owner
        self.timer = FPS * 3  # 3 secondes avant explosion
        self.just_placed = True
        self.radius = TILE_SIZE // 2 - 5

    def update(self):
        # La bombe n'est plus considérée comme "juste posée" après quelques frames
        if self.timer < FPS * 3 - 10:
            self.just_placed = False

    def draw(self, screen, offset_x, offset_y):
        # Dessiner la bombe (un cercle noir avec une mèche qui pulse)
        rect = pygame.Rect(
            offset_x + self.x * TILE_SIZE,
            offset_y + self.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        pulse_factor = (self.timer % 20) / 20  # Effet de pulsation
        size = int(self.radius * (0.8 + 0.2 * pulse_factor))

        pygame.draw.circle(screen, BLACK, rect.center, size)

        # Dessiner la mèche
        fuse_length = int(TILE_SIZE * 0.2 * (self.timer / (FPS * 3)))
        if fuse_length > 0:
            pygame.draw.line(screen, RED,
                             (rect.centerx, rect.centery - size // 2),
                             (rect.centerx, rect.centery - size // 2 - fuse_length),
                             3)
