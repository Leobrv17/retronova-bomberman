import random
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
        self.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
        self.stuck_counter = 0
        self.last_positions = []
        self.bomb_cooldown = random.randint(20, 60)  # Délai plus court
        self.danger_awareness = 0.95  # Niveau très élevé de conscience du danger

        # Nouvelles variables stratégiques
        self.strategy_mode = "hunt"  # "hunt", "collect", "trap", "escape"
        self.powerup_priority = random.choice(["bomb", "flame", "speed"])  # Préférence de power-up
        self.aggression_level = random.uniform(0.7, 1.0)  # Niveau d'agressivité aléatoire
        self.previous_bomb_positions = []  # Mémoriser où l'IA a posé des bombes
        self.known_powerups = []  # Mémoriser les power-ups repérés
        self.map_knowledge = {}  # Connaissance de la carte
        self.trap_cooldown = 0  # Cooldown pour poser des pièges élaborés
        self.has_clear_path_to_safety = False  # Indique si l'IA a identifié un chemin clair vers la sécurité

        # Créer une personnalité d'IA unique
        self.create_ai_personality()

    def create_ai_personality(self):
        """Donne à l'IA une 'personnalité' unique pour la rendre moins prévisible"""
        personalities = [
            {  # Chasseur
                "strategy_preference": {"hunt": 0.6, "collect": 0.2, "trap": 0.2},
                "powerup_priority": "flame",
                "aggression_level": 0.9,
                "risk_tolerance": 0.7,
                "path_preference": "direct"
            },
            {  # Collecteur
                "strategy_preference": {"hunt": 0.3, "collect": 0.6, "trap": 0.1},
                "powerup_priority": "bomb",
                "aggression_level": 0.6,
                "risk_tolerance": 0.4,
                "path_preference": "safe"
            },
            {  # Piégeur
                "strategy_preference": {"hunt": 0.2, "collect": 0.2, "trap": 0.6},
                "powerup_priority": "speed",
                "aggression_level": 0.8,
                "risk_tolerance": 0.6,
                "path_preference": "tricky"
            },
            {  # Survivant
                "strategy_preference": {"hunt": 0.4, "collect": 0.4, "trap": 0.2},
                "powerup_priority": random.choice(["bomb", "flame", "speed"]),
                "aggression_level": 0.7,
                "risk_tolerance": 0.5,
                "path_preference": "balanced"
            }
        ]

        # Sélectionner une personnalité aléatoire
        self.personality = random.choice(personalities)

        # Appliquer la personnalité
        self.powerup_priority = self.personality["powerup_priority"]
        self.aggression_level = self.personality["aggression_level"]
        self.risk_tolerance = self.personality["risk_tolerance"]
        self.path_preference = self.personality["path_preference"]

        # Stratégie initiale basée sur la personnalité
        strategies = list(self.personality["strategy_preference"].keys())
        weights = list(self.personality["strategy_preference"].values())
        self.strategy_mode = random.choices(strategies, weights=weights)[0]

    def update(self, game):
        if not self.alive:
            return

        # Mettre à jour la position sur la grille
        self.grid_x = self.x // TILE_SIZE
        self.grid_y = self.y // TILE_SIZE

        # Conserver les dernières positions pour détecter si l'IA est bloquée
        self.last_positions.append((self.grid_x, self.grid_y))
        if len(self.last_positions) > 10:
            self.last_positions.pop(0)

        # Mettre à jour la connaissance de la carte
        self.update_map_knowledge(game)

        # Vérifier si l'IA est bloquée
        if len(self.last_positions) == 10 and len(set(self.last_positions)) <= 2:
            self.stuck_counter += 1
            if self.stuck_counter > 15:  # Réagir plus rapidement
                self.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
                self.stuck_counter = 0
                # Plus grande chance de poser une bombe quand bloqué
                if random.random() < 0.9:
                    self.place_bomb(game)

        # Vérifier s'il y a un power-up
        tile_type = game.grid[self.grid_y][self.grid_x]
        if tile_type in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
            game.grid[self.grid_y][self.grid_x] = TileType.EMPTY
            self.collect_power_up(tile_type)
            # Mettre à jour les power-ups connus
            if (self.grid_x, self.grid_y) in self.known_powerups:
                self.known_powerups.remove((self.grid_x, self.grid_y))

        # Régler le décalage pour être au centre de la case
        if self.x % TILE_SIZE == 0 and self.y % TILE_SIZE == 0:
            self.x = self.grid_x * TILE_SIZE + TILE_SIZE // 2
            self.y = self.grid_y * TILE_SIZE + TILE_SIZE // 2

        # Décrémenter les cooldowns
        if self.trap_cooldown > 0:
            self.trap_cooldown -= 1

        # Réévaluer périodiquement la stratégie (environ toutes les 3 secondes)
        # Utiliser une approche basée sur les frames sans dépendre de game_time
        if not hasattr(self, 'strategy_timer'):
            self.strategy_timer = 0

        self.strategy_timer += 1
        if self.strategy_timer >= 180:  # Environ 3 secondes à 60 FPS
            self.reevaluate_strategy(game)
            self.strategy_timer = 0

        # Faire une décision d'IA
        self.make_ai_decision(game)

    def update_map_knowledge(self, game):
        """Met à jour la connaissance de la carte par l'IA"""
        # Observer la grille dans un rayon de vision
        vision_radius = 5
        for y in range(max(0, self.grid_y - vision_radius), min(GRID_HEIGHT, self.grid_y + vision_radius + 1)):
            for x in range(max(0, self.grid_x - vision_radius), min(GRID_WIDTH, self.grid_x + vision_radius + 1)):
                # Enregistrer l'état de la case
                key = (x, y)
                self.map_knowledge[key] = game.grid[y][x]

                # Détecter les power-ups et les mémoriser
                if game.grid[y][x] in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
                    if key not in self.known_powerups:
                        self.known_powerups.append(key)

    def reevaluate_strategy(self, game):
        """Réévalue et potentiellement change la stratégie de l'IA"""
        # Évaluer la situation actuelle
        living_players = [p for p in game.players if p.alive]
        nearest_powerup_distance = self.distance_to_nearest_powerup()
        in_danger = self.is_tile_in_danger(self.grid_x, self.grid_y, game)

        # Calculer les scores pour chaque stratégie
        strategy_scores = {
            "hunt": 0,
            "collect": 0,
            "trap": 0,
            "escape": 0
        }

        # Score pour la chasse
        if living_players:
            nearest_player = self.find_target_player(game)
            if nearest_player:
                distance = abs(nearest_player.grid_x - self.grid_x) + abs(nearest_player.grid_y - self.grid_y)
                # Plus le joueur est proche, plus le score de chasse est élevé
                strategy_scores["hunt"] = 100 / (distance + 1) * self.personality["strategy_preference"].get("hunt",
                                                                                                             0.3)

                # Si le joueur est aligné et à portée, augmenter le score de chasse
                if (
                        nearest_player.grid_x == self.grid_x or nearest_player.grid_y == self.grid_y) and distance <= self.bomb_power:
                    strategy_scores["hunt"] += 50

        # Score pour la collection
        if nearest_powerup_distance is not None:
            strategy_scores["collect"] = 50 / (nearest_powerup_distance + 1) * self.personality[
                "strategy_preference"].get("collect", 0.3)

            # Favoriser la collection si l'IA a peu de power-ups
            if self.max_bombs < 2 or self.bomb_power < 3 or self.speed < 4:
                strategy_scores["collect"] += 30

        # Score pour le piège
        if self.active_bombs == 0 and self.max_bombs > 1:
            strategy_scores["trap"] = 30 * self.personality["strategy_preference"].get("trap", 0.3)
            # Favoriser le piège si l'IA a beaucoup de bombes
            if self.max_bombs >= 3:
                strategy_scores["trap"] += 20

        # Score pour l'échappement
        if in_danger:
            strategy_scores["escape"] = 100  # Priorité absolue si en danger

        # Choisir la stratégie avec le score le plus élevé
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        self.strategy_mode = best_strategy

    def distance_to_nearest_powerup(self):
        """Calcule la distance jusqu'au power-up connu le plus proche"""
        if not self.known_powerups:
            return None

        distances = []
        for x, y in self.known_powerups:
            distance = abs(x - self.grid_x) + abs(y - self.grid_y)
            distances.append(distance)

        return min(distances) if distances else None

    def is_tile_in_danger(self, x, y, game):
        """Vérifie si une case est dans la zone d'explosion potentielle d'une bombe"""
        # Vérifier chaque bombe du jeu
        for bomb in game.bombs:
            # Si c'est sur la même ligne ou colonne que la bombe
            if (bomb.x == x or bomb.y == y):
                # Calculer la distance Manhattan
                distance = abs(bomb.x - x) + abs(bomb.y - y)
                # Si la distance est inférieure ou égale à la puissance de la bombe
                if distance <= bomb.power:
                    # Vérifier s'il y a un mur ou un bloc entre la bombe et la position
                    blocked = False
                    if bomb.x == x:  # Même colonne
                        step = 1 if bomb.y < y else -1
                        for check_y in range(bomb.y + step, y, step):
                            if game.grid[check_y][x] in [TileType.WALL, TileType.BLOCK]:
                                blocked = True
                                break
                    elif bomb.y == y:  # Même ligne
                        step = 1 if bomb.x < x else -1
                        for check_x in range(bomb.x + step, x, step):
                            if game.grid[y][check_x] in [TileType.WALL, TileType.BLOCK]:
                                blocked = True
                                break

                    if not blocked:
                        return True

        # Vérifier aussi les explosions actuelles
        for explosion in game.explosions:
            if explosion.x == x and explosion.y == y:
                return True

        return False

    def calculate_danger_level(self, x, y, game):
        """Calcule un niveau de danger pour une position (0-10)"""
        danger_level = 0

        # Vérifier si la case est directement en danger
        if self.is_tile_in_danger(x, y, game):
            return 10  # Danger maximum

        # Vérifier les cases adjacentes
        adjacent_dangers = 0
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and self.is_tile_in_danger(nx, ny, game):
                adjacent_dangers += 1

        # Ajouter au niveau de danger
        danger_level += adjacent_dangers * 2

        # Vérifier la proximité des bombes
        for bomb in game.bombs:
            distance = abs(bomb.x - x) + abs(bomb.y - y)
            if distance <= bomb.power + 1:  # +1 pour la zone adjacente
                danger_level += max(0, 5 - distance)  # Plus proche = plus dangereux

        return min(danger_level, 9)  # Plafonner à 9 (10 est réservé pour le danger immédiat)

    def find_safest_position(self, game, max_distance=6):
        """Trouve la position la plus sûre dans un rayon donné"""
        best_position = None
        lowest_danger = float('inf')

        for distance in range(1, max_distance + 1):
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    # Assurer que nous examinons les cases à exactement "distance" de Manhattan
                    if abs(dx) + abs(dy) != distance:
                        continue

                    nx, ny = self.grid_x + dx, self.grid_y + dy

                    # Vérifier si c'est une position valide
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        # Vérifier si on peut s'y rendre
                        path = self.find_path_to_position(nx, ny, game)
                        if path:
                            danger = self.calculate_danger_level(nx, ny, game)
                            if danger < lowest_danger:
                                lowest_danger = danger
                                best_position = (nx, ny)

                            # Si nous trouvons une position parfaitement sûre, l'utiliser immédiatement
                            if danger == 0:
                                return (nx, ny)

        return best_position


    def find_path_to_position(self, target_x, target_y, game, max_depth=8, avoid_danger=True):
        """Trouve un chemin vers une position cible"""
        if target_x == self.grid_x and target_y == self.grid_y:
            return [(self.grid_x, self.grid_y)]

        # File pour BFS
        queue = [(self.grid_x, self.grid_y, [])]
        visited = set([(self.grid_x, self.grid_y)])

        while queue:
            x, y, path = queue.pop(0)
            current_path = path + [(x, y)]

            # Limiter la profondeur de recherche
            if len(current_path) > max_depth:
                continue

            # Vérifier les 4 directions
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = x + dx, y + dy

                # Si c'est la cible, retourner le chemin
                if nx == target_x and ny == target_y:
                    return current_path + [(nx, ny)]

                # Vérifier si la position est valide
                if (nx, ny) not in visited and self.can_move_to(nx, ny, game):
                    # En mode évitement de danger, vérifier le niveau de danger
                    if avoid_danger and self.is_tile_in_danger(nx, ny, game):
                        # Éviter cette case si elle est dangereuse, sauf si on est désespéré
                        if random.random() > self.risk_tolerance:
                            continue

                    visited.add((nx, ny))
                    queue.append((nx, ny, current_path))

        # Pas de chemin trouvé
        return None


    def find_path_to_target(self, target_x, target_y, game, max_depth=8):
        """Algorithme pathfinding amélioré avec différentes stratégies selon la personnalité"""
        # Utiliser le pathfinding de base avec des variantes selon la personnalité
        if self.path_preference == "direct":
            return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=False)
        elif self.path_preference == "safe":
            return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=True)
        elif self.path_preference == "tricky":
            # Chemin imprévisible qui peut passer par des détours
            if random.random() < 0.3:
                # Trouver un point intermédiaire
                intermediate_positions = []
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        ix, iy = self.grid_x + dx, self.grid_y + dy
                        if 0 <= ix < GRID_WIDTH and 0 <= iy < GRID_HEIGHT:
                            intermediate_positions.append((ix, iy))

                if intermediate_positions:
                    # Choisir un point intermédiaire aléatoire
                    ix, iy = random.choice(intermediate_positions)
                    path1 = self.find_path_to_position(ix, iy, game, max_depth // 2)
                    if path1:
                        # Continuer depuis ce point intermédiaire
                        path2 = self.find_path_to_position(target_x, target_y, game, max_depth // 2)
                        if path2 and len(path2) > 1:
                            return path1[:-1] + path2  # Éviter de dupliquer le point intermédiaire

            # Fallback au chemin direct
            return self.find_path_to_position(target_x, target_y, game, max_depth)
        else:  # "balanced" ou autre
            # Alterné entre sûr et direct
            if random.random() < 0.6:
                return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=True)
            else:
                return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=False)


    def make_ai_decision(self, game):
        # Simuler un "cerveau" qui pense comme un joueur humain

        # Mettre à jour les variables de temps
        self.game_time = game.game_time if hasattr(game, 'game_time') else 0

        # Décrémentation des compteurs
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            return

        # ÉTAPE 1: Vérifier si on est en danger immédiat
        current_position_dangerous = self.is_tile_in_danger(self.grid_x, self.grid_y, game)

        if current_position_dangerous:
            # Priorité absolue à l'évitement
            self.strategy_mode = "escape"

            # Trouver la position sûre la plus proche
            safe_position = self.find_safest_position(game)

            if safe_position:
                path = self.find_path_to_position(safe_position[0], safe_position[1], game, avoid_danger=False)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
                    dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
                    self.current_direction = (dx, dy)
                    self.x += dx * self.speed
                    self.y += dy * self.speed
                    return

            # Si aucun chemin sûr n'est trouvé, essayer de s'éloigner des bombes
            escape_directions = []
            for direction in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                test_x = self.grid_x + direction[0]
                test_y = self.grid_y + direction[1]
                if self.can_move_to(test_x, test_y, game):
                    danger = self.calculate_danger_level(test_x, test_y, game)
                    escape_directions.append((danger, direction))

            if escape_directions:
                # Trier par niveau de danger croissant
                escape_directions.sort()
                self.current_direction = escape_directions[0][1]
                dx, dy = self.current_direction
                self.x += dx * self.speed
                self.y += dy * self.speed
                return

        # ÉTAPE 2: Suivre la stratégie actuelle
        if self.decision_cooldown > 0:
            self.decision_cooldown -= 1
        else:
            self.decision_cooldown = random.randint(3, 10)  # Très réactif

            # Stratégie basée sur le mode actuel
            if self.strategy_mode == "hunt":
                self.execute_hunt_strategy(game)
            elif self.strategy_mode == "collect":
                self.execute_collect_strategy(game)
            elif self.strategy_mode == "trap":
                self.execute_trap_strategy(game)
            else:  # fallback ou "escape" continué
                self.execute_hunt_strategy(game)  # Default to hunting

        # ÉTAPE 3: Gestion des bombes selon la stratégie
        self.manage_bombs(game)

        # ÉTAPE 4: Exécuter le mouvement actuel
        dx, dy = self.current_direction
        new_grid_x = self.grid_x + dx
        new_grid_y = self.grid_y + dy

        if self.can_move_to(new_grid_x, new_grid_y, game):
            self.x += dx * self.speed
            self.y += dy * self.speed
        else:
            # Si on ne peut pas bouger dans cette direction, en choisir une autre
            possible_directions = []
            for direction in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                test_x = self.grid_x + direction[0]
                test_y = self.grid_y + direction[1]
                if self.can_move_to(test_x, test_y, game):
                    # Calculer un score pour cette direction
                    score = 0

                    # Facteur de danger (inverser pour que moins dangereux = score plus élevé)
                    danger = self.calculate_danger_level(test_x, test_y, game)
                    score -= danger * 10

                    # Facteur d'objectif
                    if self.strategy_mode == "hunt":
                        target = self.find_target_player(game)
                        if target:
                            # Distance au joueur (plus proche = score plus élevé)
                            distance = abs(test_x - target.grid_x) + abs(test_y - target.grid_y)
                            score += 20 - min(20, distance)
                    elif self.strategy_mode == "collect":
                        # Proximité aux power-ups connus
                        for px, py in self.known_powerups:
                            distance = abs(test_x - px) + abs(test_y - py)
                            score += 30 - min(30, distance)

                    # Ajouter la direction avec son score
                    possible_directions.append((score, direction))

            if possible_directions:
                # Trier par score décroissant
                possible_directions.sort(reverse=True)
                # Choisir parmi les meilleures options avec un peu d'aléatoire
                top_n = min(3, len(possible_directions))
                selected_index = 0 if top_n == 1 else random.randint(0, min(2, top_n - 1))
                self.current_direction = possible_directions[selected_index][1]
            else:
                # Aucune direction n'est possible, rester sur place
                if self.active_bombs < self.max_bombs and random.random() < 0.6:
                    self.place_bomb(game)


    def execute_hunt_strategy(self, game):
        """Exécute la stratégie de chasse: poursuivre un joueur actif"""
        target = self.find_target_player(game)
        if target:
            path = self.find_path_to_target(target.grid_x, target.grid_y, game)
            if path and len(path) > 1:
                next_x, next_y = path[1]
                dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
                dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
                self.current_direction = (dx, dy)
            else:
                # Pas de chemin, approche directe
                dx = 1 if target.grid_x > self.grid_x else -1 if target.grid_x < self.grid_x else 0
                dy = 1 if target.grid_y > self.grid_y else -1 if target.grid_y < self.grid_y else 0

                # Si les deux axes sont non-nuls, en choisir un
                if dx != 0 and dy != 0:
                    if abs(target.grid_x - self.grid_x) > abs(target.grid_y - self.grid_y):
                        dy = 0  # Prioriser l'axe horizontal
                    else:
                        dx = 0  # Prioriser l'axe vertical

                self.current_direction = (dx, dy)


    def execute_trap_strategy(self, game):
        """Exécute la stratégie de piège: poser des bombes de manière stratégique pour piéger les joueurs"""
        # Vérifier si on peut placer un piège
        if self.trap_cooldown > 0 or self.active_bombs >= self.max_bombs:
            # Passer temporairement en mode chasse si on ne peut pas poser de piège
            self.execute_hunt_strategy(game)
            return

        # Trouver un joueur cible
        target = self.find_target_player(game)
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
            path = self.find_path_to_position(pos[0], pos[1], game)
            if path:
                trap_strategies.append(("block_exit", pos))

        # Stratégie 2: Encerclement - poser des bombes des deux côtés
        if len(player_probable_positions) <= 2 and self.max_bombs >= 2:
            trap_strategies.append(("surround", player_probable_positions))

        # Stratégie 3: Anticipation - poser une bombe là où le joueur pourrait aller
        common_positions = []
        for pos in player_probable_positions:
            path = self.find_path_to_position(pos[0], pos[1], game)
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
                path = self.find_path_to_position(pos[0], pos[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
                    dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
                    self.current_direction = (dx, dy)

                    # Si on est adjacent à la position, poser une bombe
                    if abs(self.grid_x - pos[0]) + abs(self.grid_y - pos[1]) <= 1:
                        self.place_bomb(game)
                        self.trap_cooldown = 30  # Attendre avant de poser un autre piège

            elif strategy == "surround":
                # Tenter d'encercler le joueur
                positions = data
                if positions:
                    pos = positions[0]
                    path = self.find_path_to_position(pos[0], pos[1], game)
                    if path and len(path) > 1:
                        next_x, next_y = path[1]
                        dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
                        dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
                        self.current_direction = (dx, dy)

                        # Si on est proche, poser une bombe
                        if abs(self.grid_x - pos[0]) + abs(self.grid_y - pos[1]) <= 2:
                            self.place_bomb(game)
                            self.trap_cooldown = 20

            elif strategy == "anticipate":
                # Aller à la position anticipée
                pos = data
                path = self.find_path_to_position(pos[0], pos[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
                    dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
                    self.current_direction = (dx, dy)

                    # Si on est à la position ou adjacent, poser une bombe
                    if (self.grid_x == pos[0] and self.grid_y == pos[1]) or \
                            (abs(self.grid_x - pos[0]) + abs(self.grid_y - pos[1]) <= 1):
                        self.place_bomb(game)
                        self.trap_cooldown = 25
        else:
            # Pas de stratégie de piège viable, passer en mode chasse
            self.execute_hunt_strategy(game)


    def execute_collect_strategy(self, game):
        """Exécute la stratégie de collection: aller chercher des power-ups"""
        if self.known_powerups:
            # Trouver le power-up le plus proche ou le préféré
            best_powerup = None
            best_score = float('-inf')

            for px, py in self.known_powerups:
                # Distance (plus proche = meilleur)
                distance = abs(px - self.grid_x) + abs(py - self.grid_y)
                score = 100 - distance * 10

                # Bonus pour le type préféré
                tile_type = game.grid[py][px]
                if (tile_type == TileType.POWER_UP_BOMB and self.powerup_priority == "bomb") or \
                        (tile_type == TileType.POWER_UP_FLAME and self.powerup_priority == "flame") or \
                        (tile_type == TileType.POWER_UP_SPEED and self.powerup_priority == "speed"):
                    score += 30

                # Pénalité si le chemin est dangereux
                path = self.find_path_to_position(px, py, game)
                if not path:
                    score -= 50  # Pénalité si pas de chemin
                elif len(path) > 1:
                    next_x, next_y = path[1]
                    danger = self.calculate_danger_level(next_x, next_y, game)
                    score -= danger * 5

                if score > best_score:
                    best_score = score
                    best_powerup = (px, py)

            if best_powerup:
                path = self.find_path_to_position(best_powerup[0], best_powerup[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
                    dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
                    self.current_direction = (dx, dy)
                    return

        # Si pas de power-up connu, chercher des blocs à détruire
        blocks_nearby = []
        for distance in range(1, 4):  # Chercher des blocs à proximité
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    # Assurer que nous examinons les cases à exactement "distance" de Manhattan
                    if abs(dx) + abs(dy) != distance:
                        continue

                    bx, by = self.grid_x + dx, self.grid_y + dy
                    if 0 <= bx < GRID_WIDTH and 0 <= by < GRID_HEIGHT and game.grid[by][bx] == TileType.BLOCK:
                        blocks_nearby.append((bx, by))