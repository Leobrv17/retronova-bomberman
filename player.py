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
        """
        Vérifie si le joueur peut se déplacer vers une position donnée
        en tenant compte du rayon du cercle qui le représente
        """
        # Conversion du rayon en unités de grille
        radius_in_grid = self.radius / TILE_SIZE

        # Calculer les limites du cercle basées sur la nouvelle position potentielle
        # Coordonnées du centre en unités de grille
        center_x = grid_x + 0.5
        center_y = grid_y + 0.5

        # Points extrêmes du cercle (gauche, droite, haut, bas)
        left_x = center_x - radius_in_grid
        right_x = center_x + radius_in_grid
        top_y = center_y - radius_in_grid
        bottom_y = center_y + radius_in_grid

        # Convertir les coordonnées en indices de grille
        left_grid = int(left_x)
        right_grid = int(right_x)
        top_grid = int(top_y)
        bottom_grid = int(bottom_y)

        # Vérifier les cases qui pourraient être en collision avec le cercle
        for check_x in range(left_grid, right_grid + 1):
            for check_y in range(top_grid, bottom_grid + 1):
                # Vérifier si la position est dans les limites de la grille
                if 0 <= check_x < GRID_WIDTH and 0 <= check_y < GRID_HEIGHT:
                    tile_type = game.grid[check_y][check_x]

                    # Si c'est un mur ou un bloc, vérifier la collision précise
                    if tile_type in [TileType.WALL, TileType.BLOCK]:
                        # Centre de la case obstacle
                        obstacle_center_x = check_x + 0.5
                        obstacle_center_y = check_y + 0.5

                        # Distance entre le centre du joueur et le centre de l'obstacle
                        dx = abs(center_x - obstacle_center_x)
                        dy = abs(center_y - obstacle_center_y)

                        # Si le cercle du joueur touche la case obstacle
                        # Coin supérieur gauche: (check_x, check_y), coin inférieur droit: (check_x+1, check_y+1)
                        # On vérifie la distance minimale entre le centre du cercle et le bord de la case

                        # Pour les obstacles rectangulaires, on calcule la distance au bord le plus proche
                        closest_x = max(check_x, min(center_x, check_x + 1))
                        closest_y = max(check_y, min(center_y, check_y + 1))

                        # Distance entre le centre du cercle et le point le plus proche du rectangle
                        distance = ((center_x - closest_x) ** 2 + (center_y - closest_y) ** 2) ** 0.5

                        # Si cette distance est inférieure au rayon, il y a collision
                        if distance < radius_in_grid:
                            return False

        # Vérifier s'il y a une bombe
        if game.grid[grid_y][grid_x] == TileType.BOMB:
            # Vérifier si on est déjà sur une bombe (pour pouvoir en sortir)
            current_on_bomb = game.grid[self.grid_y][self.grid_x] == TileType.BOMB

            # Si on est sur une bombe, on peut se déplacer vers une autre bombe ou une case vide
            if current_on_bomb:
                return True

            # Sinon, on ne peut pas marcher sur une bombe (sauf si on vient de la poser)
            for bomb in game.bombs:
                if bomb.x == grid_x and bomb.y == grid_y and bomb.just_placed and bomb.owner == self:
                    return True
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