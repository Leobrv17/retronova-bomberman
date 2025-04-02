import random
from contantes import *
from bomb import Bomb


class AIStrategies:
    def __init__(self, ai_player):
        """Initialise le module de stratégies avec une référence à l'IA parent"""
        self.ai = ai_player

    def execute_hunt_strategy(self, game):
        """Exécute la stratégie de chasse: poursuivre un joueur actif"""
        target = self.ai.find_target_player(game)
        if target:
            path = self.ai.find_path_to_target(target.grid_x, target.grid_y, game)
            if path and len(path) > 1:
                next_x, next_y = path[1]
                dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                self.ai.current_direction = (dx, dy)
            else:
                # Pas de chemin, approche directe
                dx = 1 if target.grid_x > self.ai.grid_x else -1 if target.grid_x < self.ai.grid_x else 0
                dy = 1 if target.grid_y > self.ai.grid_y else -1 if target.grid_y < self.ai.grid_y else 0

                # Si les deux axes sont non-nuls, en choisir un
                if dx != 0 and dy != 0:
                    if abs(target.grid_x - self.ai.grid_x) > abs(target.grid_y - self.ai.grid_y):
                        dy = 0  # Prioriser l'axe horizontal
                    else:
                        dx = 0  # Prioriser l'axe vertical

                self.ai.current_direction = (dx, dy)

    def execute_trap_strategy(self, game):
        """Exécute la stratégie de piège: poser des bombes de manière stratégique pour piéger les joueurs"""
        # Vérifier si on peut placer un piège
        if self.ai.trap_cooldown > 0 or self.ai.active_bombs >= self.ai.max_bombs:
            # Passer temporairement en mode chasse si on ne peut pas poser de piège
            self.execute_hunt_strategy(game)
            return

        # Trouver un joueur cible
        target = self.ai.find_target_player(game)
        if not target:
            # Pas de cible, passer en mode exploration
            self.execute_collect_strategy(game)
            return

        # Analyser les mouvements probables du joueur
        player_probable_positions = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            px, py = target.grid_x + dx, target.grid_y + dy
            if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT and game.grid[py][px] == TileType.EMPTY:
                player_probable_positions.append((px, py))

        if not player_probable_positions:
            # Joueur coincé, attaquer directement
            self.execute_hunt_strategy(game)
            return

        # Stratégies de piège
        trap_strategies = []

        # Stratégie 1: Bloquer une issue
        for pos in player_probable_positions:
            # Vérifier si on peut atteindre cette position
            path = self.ai.find_path_to_position(pos[0], pos[1], game)
            if path:
                trap_strategies.append(("block_exit", pos))

        # Stratégie 2: Encerclement - poser des bombes des deux côtés
        if len(player_probable_positions) <= 2 and self.ai.max_bombs >= 2:
            trap_strategies.append(("surround", player_probable_positions))

        # Stratégie 3: Anticipation - poser une bombe là où le joueur pourrait aller
        common_positions = []
        for pos in player_probable_positions:
            path = self.ai.find_path_to_position(pos[0], pos[1], game)
            if path and len(path) <= 3:  # Si on peut y arriver rapidement
                common_positions.append(pos)

        if common_positions:
            trap_strategies.append(("anticipate", random.choice(common_positions)))

        if trap_strategies:
            # Choisir une stratégie
            strategy, data = random.choice(trap_strategies)

            if strategy == "block_exit":
                # Aller à cette position pour bloquer
                pos = data
                path = self.ai.find_path_to_position(pos[0], pos[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                    dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                    self.ai.current_direction = (dx, dy)

                    # Si on est adjacent à la position, poser une bombe
                    if abs(self.ai.grid_x - pos[0]) + abs(self.ai.grid_y - pos[1]) <= 1:
                        self.ai.place_bomb(game)
                        self.ai.trap_cooldown = 30  # Attendre avant de poser un autre piège

            elif strategy == "surround":
                # Tenter d'encercler le joueur
                positions = data
                if positions:
                    pos = positions[0]
                    path = self.ai.find_path_to_position(pos[0], pos[1], game)
                    if path and len(path) > 1:
                        next_x, next_y = path[1]
                        dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                        dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                        self.ai.current_direction = (dx, dy)

                        # Si on est proche, poser une bombe
                        if abs(self.ai.grid_x - pos[0]) + abs(self.ai.grid_y - pos[1]) <= 2:
                            self.ai.place_bomb(game)
                            self.ai.trap_cooldown = 20

            elif strategy == "anticipate":
                # Aller à la position anticipée
                pos = data
                path = self.ai.find_path_to_position(pos[0], pos[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                    dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                    self.ai.current_direction = (dx, dy)

                    # Si on est à la position ou adjacent, poser une bombe
                    if (self.ai.grid_x == pos[0] and self.ai.grid_y == pos[1]) or \
                            (abs(self.ai.grid_x - pos[0]) + abs(self.ai.grid_y - pos[1]) <= 1):
                        self.ai.place_bomb(game)
                        self.ai.trap_cooldown = 25
        else:
            # Pas de stratégie de piège viable, passer en mode chasse
            self.execute_hunt_strategy(game)

    def execute_collect_strategy(self, game):
        """Exécute la stratégie de collection: aller chercher des power-ups"""
        if self.ai.known_powerups:
            # Trouver le power-up le plus proche ou le préféré
            best_powerup = None
            best_score = float('-inf')

            for px, py in self.ai.known_powerups:
                # Distance (plus proche = meilleur)
                distance = abs(px - self.ai.grid_x) + abs(py - self.ai.grid_y)
                score = 100 - distance * 10

                # Bonus pour le type préféré
                tile_type = game.grid[py][px]
                if (tile_type == TileType.POWER_UP_BOMB and self.ai.powerup_priority == "bomb") or \
                        (tile_type == TileType.POWER_UP_FLAME and self.ai.powerup_priority == "flame") or \
                        (tile_type == TileType.POWER_UP_SPEED and self.ai.powerup_priority == "speed"):
                    score += 30

                # Pénalité si le chemin est dangereux
                path = self.ai.find_path_to_position(px, py, game)
                if not path:
                    score -= 50  # Pénalité si pas de chemin
                elif len(path) > 1:
                    next_x, next_y = path[1]
                    danger = self.ai.calculate_danger_level(next_x, next_y, game)
                    score -= danger * 5

                if score > best_score:
                    best_score = score
                    best_powerup = (px, py)

            if best_powerup:
                path = self.ai.find_path_to_position(best_powerup[0], best_powerup[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                    dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                    self.ai.current_direction = (dx, dy)
                    return

        # Si pas de power-up connu, chercher des blocs à détruire
        blocks_nearby = []
        for distance in range(1, 4):  # Chercher des blocs à proximité
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    # Assurer que nous examinons les cases à exactement "distance" de Manhattan
                    if abs(dx) + abs(dy) != distance:
                        continue

                    bx, by = self.ai.grid_x + dx, self.ai.grid_y + dy
                    if 0 <= bx < GRID_WIDTH and 0 <= by < GRID_HEIGHT and game.grid[by][bx] == TileType.BLOCK:
                        blocks_nearby.append((bx, by))

        # S'il y a des blocs à proximité, aller vers le plus proche
        if blocks_nearby:
            # Trouver le bloc le plus proche
            closest_block = None
            min_distance = float('inf')

            for bx, by in blocks_nearby:
                distance = abs(bx - self.ai.grid_x) + abs(by - self.ai.grid_y)
                if distance < min_distance:
                    min_distance = distance
                    closest_block = (bx, by)

            if closest_block:
                # Trouver une case adjacente au bloc
                adjacent_positions = []
                bx, by = closest_block

                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    ax, ay = bx + dx, by + dy
                    if 0 <= ax < GRID_WIDTH and 0 <= ay < GRID_HEIGHT and game.grid[ay][ax] == TileType.EMPTY:
                        adjacent_positions.append((ax, ay))

                if adjacent_positions:
                    # Choisir la position adjacente la plus proche
                    best_adj = None
                    best_distance = float('inf')

                    for ax, ay in adjacent_positions:
                        distance = abs(ax - self.ai.grid_x) + abs(ay - self.ai.grid_y)
                        if distance < best_distance:
                            best_distance = distance
                            best_adj = (ax, ay)

                    if best_adj:
                        path = self.ai.find_path_to_position(best_adj[0], best_adj[1], game)
                        if path and len(path) > 1:
                            next_x, next_y = path[1]
                            dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                            dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                            self.ai.current_direction = (dx, dy)

                            # Si on est adjacent au bloc, poser une bombe
                            if self.ai.active_bombs < self.ai.max_bombs and abs(self.ai.grid_x - bx) + abs(
                                    self.ai.grid_y - by) <= 1:
                                # Vérifier qu'on a un chemin de fuite
                                escape_path = self.ai.find_escape_path(game)
                                if escape_path:
                                    self.ai.place_bomb(game)
                            return

        # Si aucun bloc ni power-up, explorer aléatoirement
        if random.random() < 0.2:  # 20% de chance de changer de direction
            self.ai.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])

    def execute_escape_strategy(self, game):
        """Exécute la stratégie d'échappement: fuir le danger"""
        # Trouver la position sûre la plus proche
        safe_position = self.ai.find_safest_position(game)

        if safe_position:
            path = self.ai.find_path_to_position(safe_position[0], safe_position[1], game, avoid_danger=False)
            if path and len(path) > 1:
                next_x, next_y = path[1]
                dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                self.ai.current_direction = (dx, dy)
                return True

        # Si aucun chemin sûr n'est trouvé, essayer de s'éloigner des bombes
        escape_directions = []
        for direction in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            test_x = self.ai.grid_x + direction[0]
            test_y = self.ai.grid_y + direction[1]
            if self.ai.can_move_to(test_x, test_y, game):
                danger = self.ai.calculate_danger_level(test_x, test_y, game)
                escape_directions.append((danger, direction))

        if escape_directions:
            # Trier par niveau de danger croissant
            escape_directions.sort()
            self.ai.current_direction = escape_directions[0][1]
            return True

        return False  # Pas d'échappatoire trouvée

    def find_path_to_nearest_block(self, game):
        """Trouve un chemin vers le bloc destructible le plus proche"""
        min_distance = float('inf')
        target_block = None
        target_adjacent = None

        # Chercher des blocs dans un rayon croissant
        for distance in range(1, 10):
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    # Vérifier si c'est à exactement "distance" de Manhattan
                    if abs(dx) + abs(dy) != distance:
                        continue

                    bx, by = self.ai.grid_x + dx, self.ai.grid_y + dy
                    if 0 <= bx < GRID_WIDTH and 0 <= by < GRID_HEIGHT and game.grid[by][bx] == TileType.BLOCK:
                        # Chercher une position adjacente accessible
                        for adj_dx, adj_dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                            adj_x, adj_y = bx + adj_dx, by + adj_dy
                            if 0 <= adj_x < GRID_WIDTH and 0 <= adj_y < GRID_HEIGHT and game.grid[adj_y][
                                adj_x] == TileType.EMPTY:
                                # Vérifier si on peut atteindre cette position
                                path = self.ai.find_path_to_position(adj_x, adj_y, game)
                                if path:
                                    # Calculer la distance totale
                                    total_distance = len(path) - 1
                                    if total_distance < min_distance:
                                        min_distance = total_distance
                                        target_block = (bx, by)
                                        target_adjacent = (adj_x, adj_y)

            # Si on a trouvé un bloc atteignable, pas besoin de chercher plus loin
            if target_block:
                break

        if target_adjacent:
            return self.ai.find_path_to_position(target_adjacent[0], target_adjacent[1], game)

        return None