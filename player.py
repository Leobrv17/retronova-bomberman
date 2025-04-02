from bomb import Bomb
import pygame
from contantes import *


class Player:
    def __init__(self, grid_x, grid_y, color, key_up, key_down, key_left, key_right, key_bomb):
        # Position et apparence
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = grid_x * TILE_SIZE + TILE_SIZE // 2
        self.y = grid_y * TILE_SIZE + TILE_SIZE // 2
        self.color = color
        self.radius = TILE_SIZE // 2 - 5

        # Caractéristiques
        self.speed = 3
        self.max_bombs = 1
        self.bomb_power = 2
        self.active_bombs = 0
        self.alive = True

        # Système de points
        self.score = 0
        self.blocks_destroyed = 0
        self.powerups_collected = 0
        self.survival_time = 0

        # Touches de contrôle
        self.key_up = key_up
        self.key_down = key_down
        self.key_left = key_left
        self.key_right = key_right
        self.key_bomb = key_bomb

    def handle_input(self, keys, game):
        # Déplacement
        dx, dy = 0, 0

        if keys[self.key_up]:
            dy = -self.speed
        elif keys[self.key_down]:
            dy = self.speed
        elif keys[self.key_left]:
            dx = -self.speed
        elif keys[self.key_right]:
            dx = self.speed

        # Vérifier si le mouvement est valide
        new_grid_x = (self.x + dx) // TILE_SIZE
        new_grid_y = (self.y + dy) // TILE_SIZE

        # Mouvement horizontal
        if dx != 0:
            if self.can_move_to(new_grid_x, self.grid_y, game):
                self.x += dx
        # Mouvement vertical
        if dy != 0:
            if self.can_move_to(self.grid_x, new_grid_y, game):
                self.y += dy

        # Placement de bombe
        if keys[self.key_bomb] and self.active_bombs < self.max_bombs:
            self.place_bomb(game)

    def can_move_to(self, grid_x, grid_y, game):
        # Vérifier si la position est dans les limites
        if grid_x < 0 or grid_x >= GRID_WIDTH or grid_y < 0 or grid_y >= GRID_HEIGHT:
            return False

        # Vérifier si la case est libre
        tile_type = game.grid[grid_y][grid_x]
        if tile_type in [TileType.WALL, TileType.BLOCK]:
            return False

        # Vérifier s'il y a une bombe
        if tile_type == TileType.BOMB:
            # On autorise le joueur à marcher sur sa propre bombe qu'il vient de poser
            # mais pas sur les autres bombes
            for bomb in game.bombs:
                if bomb.x == grid_x and bomb.y == grid_y and not bomb.just_placed:
                    return False

        return True

    def update(self, game):
        # Mettre à jour la position sur la grille
        self.grid_x = self.x // TILE_SIZE
        self.grid_y = self.y // TILE_SIZE

        # Vérifier s'il y a un power-up
        tile_type = game.grid[self.grid_y][self.grid_x]
        if tile_type in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
            game.grid[self.grid_y][self.grid_x] = TileType.EMPTY
            self.collect_power_up(tile_type)

        # Régler le décalage pour être au centre de la case
        if self.x % TILE_SIZE == 0 and self.y % TILE_SIZE == 0:
            self.x = self.grid_x * TILE_SIZE + TILE_SIZE // 2
            self.y = self.grid_y * TILE_SIZE + TILE_SIZE // 2

    def collect_power_up(self, power_up_type):
        player_num = 1 if self.color == RED else 2

        # Incrémenter le compteur de power-ups collectés
        self.powerups_collected += 1

        # Points de base pour avoir ramassé un power-up
        self.score += 250

        if power_up_type == TileType.POWER_UP_BOMB:
            # Augmenter le nombre de bombes
            self.max_bombs += 1
            print(f"Joueur {player_num} : +1 bombe! (Total: {self.max_bombs})")
        elif power_up_type == TileType.POWER_UP_FLAME:
            # Augmenter la portée des explosions
            self.bomb_power += 1
            print(f"Joueur {player_num} : +1 puissance! (Total: {self.bomb_power})")
        elif power_up_type == TileType.POWER_UP_SPEED:
            # Augmenter la vitesse de déplacement
            self.speed += 1
            print(f"Joueur {player_num} : +1 vitesse! (Total: {self.speed})")

    def place_bomb(self, game):
        # Placement de bombe sur la grille
        if game.grid[self.grid_y][self.grid_x] == TileType.EMPTY:
            game.grid[self.grid_y][self.grid_x] = TileType.BOMB
            bomb = Bomb(self.grid_x, self.grid_y, self.bomb_power, self)
            game.bombs.append(bomb)
            self.active_bombs += 1

    def draw(self, screen, offset_x, offset_y):
        # Dessiner le joueur (un cercle)
        x_pos = offset_x + self.x
        y_pos = offset_y + self.y
        pygame.draw.circle(screen, self.color, (x_pos, y_pos), self.radius)
