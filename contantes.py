from enum import Enum
import pygame

pygame.init()

IMAGE_PATH = "assets/"  # Dossier où vous stockerez vos images

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)


# Création de la classe Enum pour les types de cases
class TileType(Enum):
    EMPTY = 0
    WALL = 1
    BLOCK = 2
    BOMB = 3
    EXPLOSION = 4
    POWER_UP_BOMB = 5
    POWER_UP_FLAME = 6
    POWER_UP_SPEED = 7


# Constantes du jeu
FPS = 60

# Obtenir les dimensions de l'écran
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# Définir la taille du plateau avec des proportions appropriées
GRID_WIDTH = 21
GRID_HEIGHT = 17

# Calculer la taille des cases pour s'adapter à l'écran
TILE_SIZE_W = SCREEN_WIDTH // GRID_WIDTH
TILE_SIZE_H = SCREEN_HEIGHT // GRID_HEIGHT
TILE_SIZE = min(TILE_SIZE_W, TILE_SIZE_H)  # Prendre la plus petite dimension pour les cases carrées

# Recalculer les dimensions du plateau
WIDTH = TILE_SIZE * GRID_WIDTH
HEIGHT = TILE_SIZE * GRID_HEIGHT
