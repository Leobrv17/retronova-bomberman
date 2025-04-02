import random
from bomb import Bomb
from contantes import *


class AIPlayer:
    def __init__(self, grid_x, grid_y, color, target_player=None):
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

        # Cible prioritaire pour l'IA
        self.target_player = target_player

        # Variables pour l'IA
        self.move_cooldown = 0
        self.decision_cooldown = 0
        self.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])  # Direction initiale aléatoire
        self.stuck_counter = 0
        self.last_positions = []
        self.bomb_cooldown = random.randint(30, 90)  # Délai aléatoire avant de poser une bombe

    def update(self, game):
        if not self.alive:
            return

        # Mettre à jour la position sur la grille
        self.grid_x = self.x // TILE_SIZE
        self.grid_y = self.y // TILE_SIZE

        # Conserver les dernières positions pour détecter si l'IA est bloquée
        self.last_positions.append((self.grid_x, self.grid_y))
        if len(self.last_positions) > 10:  # Ne garde que les 10 dernières positions
            self.last_positions.pop(0)

        # Vérifier si l'IA est bloquée (reste au même endroit)
        if len(self.last_positions) == 10 and len(set(self.last_positions)) <= 2:
            self.stuck_counter += 1
            if self.stuck_counter > 30:  # Si bloqué pendant 30 frames, change de stratégie
                self.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
                self.stuck_counter = 0
                # Poser une bombe si bloqué
                if random.random() < 0.7:  # 70% de chance de poser une bombe quand bloqué
                    self.place_bomb(game)

        # Vérifier s'il y a un power-up
        tile_type = game.grid[self.grid_y][self.grid_x]
        if tile_type in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
            game.grid[self.grid_y][self.grid_x] = TileType.EMPTY
            self.collect_power_up(tile_type)

        # Régler le décalage pour être au centre de la case
        if self.x % TILE_SIZE == 0 and self.y % TILE_SIZE == 0:
            self.x = self.grid_x * TILE_SIZE + TILE_SIZE // 2
            self.y = self.grid_y * TILE_SIZE + TILE_SIZE // 2

        # Faire une décision d'IA
        self.make_ai_decision(game)

    def make_ai_decision(self, game):
        # Décrémentation des compteurs
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            return

        if self.decision_cooldown > 0:
            self.decision_cooldown -= 1
        else:
            # Prendre une nouvelle décision tous les X frames
            self.decision_cooldown = random.randint(10, 30)

            # 80% du temps, essayer de se diriger vers un joueur
            if random.random() < 0.8 and game.players:
                target = self.find_target_player(game)
                if target:
                    # Calculer la direction vers la cible
                    dx = 1 if target.grid_x > self.grid_x else -1 if target.grid_x < self.grid_x else 0
                    dy = 1 if target.grid_y > self.grid_y else -1 if target.grid_y < self.grid_y else 0

                    # Prioriser un axe aléatoirement
                    if dx != 0 and dy != 0 and random.random() < 0.5:
                        dx = 0
                    else:
                        dy = 0

                    self.current_direction = (dx, dy)
            else:
                # Sinon, direction aléatoire
                self.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])

        # Décider si on pose une bombe
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1
        else:
            # Vérifier si un joueur est proche
            player_nearby = False
            for player in game.players:
                if player.alive and abs(player.grid_x - self.grid_x) + abs(player.grid_y - self.grid_y) <= 3:
                    player_nearby = True
                    break

            # Poser une bombe si un joueur est à proximité ou aléatoirement
            if (player_nearby and random.random() < 0.7) or random.random() < 0.1:
                self.place_bomb(game)
                self.bomb_cooldown = random.randint(60, 120)  # Réinitialiser le délai

        # Bouger dans la direction actuelle
        dx, dy = self.current_direction
        new_grid_x = (self.x + dx * self.speed) // TILE_SIZE
        new_grid_y = (self.y + dy * self.speed) // TILE_SIZE

        # Vérifier si le mouvement est valide
        if self.can_move_to(new_grid_x, new_grid_y, game):
            self.x += dx * self.speed
            self.y += dy * self.speed
        else:
            # Si on ne peut pas bouger dans cette direction, en choisir une autre
            possible_directions = []
            for direction in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                test_x = (self.x + direction[0] * self.speed) // TILE_SIZE
                test_y = (self.y + direction[1] * self.speed) // TILE_SIZE
                if self.can_move_to(test_x, test_y, game):
                    possible_directions.append(direction)

            if possible_directions:
                self.current_direction = random.choice(possible_directions)
            else:
                # Si aucune direction n'est possible, rester sur place et potentiellement poser une bombe
                if random.random() < 0.3 and self.active_bombs < self.max_bombs:
                    self.place_bomb(game)

    def find_target_player(self, game):
        # Si une cible spécifique est définie et qu'elle est en vie, la cibler
        if self.target_player and self.target_player.alive:
            return self.target_player

        # Sinon, trouver le joueur le plus proche
        closest_player = None
        min_distance = float('inf')

        for player in game.players:
            if player.alive:
                distance = abs(player.grid_x - self.grid_x) + abs(player.grid_y - self.grid_y)
                if distance < min_distance:
                    min_distance = distance
                    closest_player = player

        return closest_player

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
            # Éviter les bombes
            return False

        # Vérifier s'il y a une explosion
        for explosion in game.explosions:
            if explosion.x == grid_x and explosion.y == grid_y:
                return False

        return True

    def collect_power_up(self, power_up_type):
        # Incrémenter le compteur de power-ups collectés
        self.powerups_collected += 1

        # Points de base pour avoir ramassé un power-up
        self.score += 250

        if power_up_type == TileType.POWER_UP_BOMB:
            # Augmenter le nombre de bombes
            self.max_bombs += 1
        elif power_up_type == TileType.POWER_UP_FLAME:
            # Augmenter la portée des explosions
            self.bomb_power += 1
        elif power_up_type == TileType.POWER_UP_SPEED:
            # Augmenter la vitesse de déplacement
            self.speed += 1

    def place_bomb(self, game):
        # Placement de bombe sur la grille
        if game.grid[self.grid_y][self.grid_x] == TileType.EMPTY and self.active_bombs < self.max_bombs:
            game.grid[self.grid_y][self.grid_x] = TileType.BOMB
            bomb = Bomb(self.grid_x, self.grid_y, self.bomb_power, self)
            game.bombs.append(bomb)
            self.active_bombs += 1

            # Après avoir posé une bombe, essayer de s'en éloigner
            possible_directions = []
            for direction in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                test_x = (self.x + direction[0] * self.speed) // TILE_SIZE
                test_y = (self.y + direction[1] * self.speed) // TILE_SIZE
                if self.can_move_to(test_x, test_y, game):
                    possible_directions.append(direction)

            if possible_directions:
                self.current_direction = random.choice(possible_directions)

    def draw(self, screen, offset_x, offset_y):
        # Dessiner l'IA (un cercle avec contour blanc pour différencier des joueurs)
        x_pos = offset_x + self.x
        y_pos = offset_y + self.y
        pygame.draw.circle(screen, self.color, (x_pos, y_pos), self.radius)
        pygame.draw.circle(screen, WHITE, (x_pos, y_pos), self.radius, 2)  # Contour blanc