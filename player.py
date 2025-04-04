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

        # Test du mouvement avec des coordonnées temporaires
        new_x = self.x + dx
        new_y = self.y + dy

        # Calculer les nouvelles positions sur la grille
        new_grid_x = new_x // TILE_SIZE
        new_grid_y = new_y // TILE_SIZE

        # Marge de tolérance pour le mouvement (plus petite que précédemment)
        tolerance = 0.7  # 70% du rayon est toléré pour les collisions
        collision_radius = self.radius * tolerance

        # Mouvement horizontal
        if dx != 0:
            can_move_x = True

            # Vérifier uniquement les cases où le cercle pourrait toucher un mur
            left_edge = new_x - collision_radius
            right_edge = new_x + collision_radius
            left_grid_x = left_edge // TILE_SIZE
            right_grid_x = right_edge // TILE_SIZE

            # Vérifier les cases potentiellement en collision
            for check_x in range(int(left_grid_x), int(right_grid_x) + 1):
                if check_x < 0 or check_x >= GRID_WIDTH:
                    can_move_x = False
                    break

                top_edge = self.y - collision_radius
                bottom_edge = self.y + collision_radius
                top_grid_y = max(0, int(top_edge // TILE_SIZE))
                bottom_grid_y = min(GRID_HEIGHT - 1, int(bottom_edge // TILE_SIZE))

                for check_y in range(top_grid_y, bottom_grid_y + 1):
                    if game.grid[check_y][check_x] in [TileType.WALL, TileType.BLOCK]:
                        # Calcul simplifié de la collision
                        wall_center_x = check_x * TILE_SIZE + TILE_SIZE // 2
                        wall_center_y = check_y * TILE_SIZE + TILE_SIZE // 2

                        # Distance entre les centres
                        dist_x = abs(new_x - wall_center_x)
                        dist_y = abs(self.y - wall_center_y)

                        # Distance combinée (approximation simple)
                        combined_radius = collision_radius + TILE_SIZE * 0.4  # Réduire la "taille" du mur

                        # Si le cercle est trop proche du mur
                        if dist_x < combined_radius and dist_y < combined_radius:
                            can_move_x = False
                            break

                if not can_move_x:
                    break

            # Vérifier les bombes
            if can_move_x:
                if game.grid[self.grid_y][new_grid_x] == TileType.BOMB:
                    # Permettre de se déplacer si on est déjà sur une bombe
                    if game.grid[self.grid_y][self.grid_x] != TileType.BOMB:
                        # Ou si c'est notre bombe récemment posée
                        bomb_is_own = False
                        for bomb in game.bombs:
                            if bomb.x == new_grid_x and bomb.y == self.grid_y and bomb.just_placed and bomb.owner == self:
                                bomb_is_own = True
                                break

                        if not bomb_is_own:
                            can_move_x = False

                if can_move_x:
                    self.x = new_x

        # Mouvement vertical (même logique)
        if dy != 0:
            can_move_y = True

            top_edge = new_y - collision_radius
            bottom_edge = new_y + collision_radius
            top_grid_y = top_edge // TILE_SIZE
            bottom_grid_y = bottom_edge // TILE_SIZE

            for check_y in range(int(top_grid_y), int(bottom_grid_y) + 1):
                if check_y < 0 or check_y >= GRID_HEIGHT:
                    can_move_y = False
                    break

                left_edge = self.x - collision_radius
                right_edge = self.x + collision_radius
                left_grid_x = max(0, int(left_edge // TILE_SIZE))
                right_grid_x = min(GRID_WIDTH - 1, int(right_edge // TILE_SIZE))

                for check_x in range(left_grid_x, right_grid_x + 1):
                    if game.grid[check_y][check_x] in [TileType.WALL, TileType.BLOCK]:
                        wall_center_x = check_x * TILE_SIZE + TILE_SIZE // 2
                        wall_center_y = check_y * TILE_SIZE + TILE_SIZE // 2

                        dist_x = abs(self.x - wall_center_x)
                        dist_y = abs(new_y - wall_center_y)

                        combined_radius = collision_radius + TILE_SIZE * 0.4

                        if dist_x < combined_radius and dist_y < combined_radius:
                            can_move_y = False
                            break

                if not can_move_y:
                    break

            if can_move_y:
                if game.grid[new_grid_y][self.grid_x] == TileType.BOMB:
                    if game.grid[self.grid_y][self.grid_x] != TileType.BOMB:
                        bomb_is_own = False
                        for bomb in game.bombs:
                            if bomb.x == self.grid_x and bomb.y == new_grid_y and bomb.just_placed and bomb.owner == self:
                                bomb_is_own = True
                                break

                        if not bomb_is_own:
                            can_move_y = False

                if can_move_y:
                    self.y = new_y

        # Placement de bombe
        if keys[self.key_bomb] and self.active_bombs < self.max_bombs:
            self.place_bomb(game)

    def can_move_to(self, grid_x, grid_y, game):
        """
        Vérifie si le joueur peut se déplacer vers une position donnée
        en évitant tout débordement sur les murs
        """
        # Vérifier si la position est hors de la grille
        if grid_x < 0 or grid_x >= GRID_WIDTH or grid_y < 0 or grid_y >= GRID_HEIGHT:
            return False

        # Conversion précise des coordonnées du cercle en unités de grille
        # Ajouter une petite marge supplémentaire pour éviter les débordements
        safety_margin = 0.05  # 5% de marge supplémentaire
        radius_in_grid = (self.radius / TILE_SIZE) + safety_margin

        # Calculer le centre de la position cible
        center_x = grid_x + 0.5
        center_y = grid_y + 0.5

        # Calcul des points extrêmes du cercle avec la marge
        left_x = center_x - radius_in_grid
        right_x = center_x + radius_in_grid
        top_y = center_y - radius_in_grid
        bottom_y = center_y + radius_in_grid

        # Convertir en indices de grille (arrondir vers l'extérieur pour plus de sécurité)
        left_grid = max(0, int(left_x))
        right_grid = min(GRID_WIDTH - 1, int(right_x + 0.999))
        top_grid = max(0, int(top_y))
        bottom_grid = min(GRID_HEIGHT - 1, int(bottom_y + 0.999))

        # Vérifier les cases qui pourraient être en collision
        for check_x in range(left_grid, right_grid + 1):
            for check_y in range(top_grid, bottom_grid + 1):
                tile_type = game.grid[check_y][check_x]

                # Si c'est un mur ou un bloc, vérifier la collision précise
                if tile_type in [TileType.WALL, TileType.BLOCK]:
                    # Calculer le point le plus proche du rectangle sur le centre du cercle
                    closest_x = max(check_x, min(center_x, check_x + 1))
                    closest_y = max(check_y, min(center_y, check_y + 1))

                    # Distance entre le centre du cercle et le point le plus proche
                    distance = ((center_x - closest_x) ** 2 + (center_y - closest_y) ** 2) ** 0.5

                    # S'il y a collision (avec la marge de sécurité)
                    if distance < radius_in_grid:
                        return False

        # Gestion des bombes (comme avant)
        if game.grid[grid_y][grid_x] == TileType.BOMB:
            # Vérifier si on est déjà sur une bombe (pour pouvoir en sortir)
            current_on_bomb = game.grid[self.grid_y][self.grid_x] == TileType.BOMB

            # Si on est sur une bombe, on peut se déplacer vers une autre bombe
            if current_on_bomb:
                return True

            # Sinon, vérifier si c'est notre bombe récemment posée
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