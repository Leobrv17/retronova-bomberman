import random
from contantes import *
from bomb import Bomb
from ai_strategies import AIStrategies


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
        self.game_time = 0  # Initialisation du temps de jeu

        # Nouvelles variables stratégiques
        self.strategy_mode = "hunt"  # "hunt", "collect", "trap", "escape"
        self.powerup_priority = random.choice(["bomb", "flame", "speed"])  # Préférence de power-up
        self.aggression_level = random.uniform(0.7, 1.0)  # Niveau d'agressivité aléatoire
        self.previous_bomb_positions = []  # Mémoriser où l'IA a posé des bombes
        self.known_powerups = []  # Mémoriser les power-ups repérés
        self.map_knowledge = {}  # Connaissance de la carte
        self.trap_cooldown = 0  # Cooldown pour poser des pièges élaborés
        self.has_clear_path_to_safety = False  # Indique si l'IA a identifié un chemin clair vers la sécurité
        self.strategy_timer = 0  # Initialiser le timer de stratégie

        # Initialiser le module de stratégies
        self.strategies = AIStrategies(self)

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
        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1

        # Réévaluer périodiquement la stratégie (environ toutes les 3 secondes)
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

    def find_target_player(self, game):
        """Trouve le joueur cible le plus approprié"""
        # Si nous avons une cible spécifique et qu'elle est vivante, la prioriser
        if self.target_player and self.target_player.alive:
            return self.target_player

        # Sinon, trouver le joueur vivant le plus proche
        living_players = [p for p in game.players if p.alive]
        if not living_players:
            # S'il n'y a pas de joueurs vivants, chercher une IA vivante
            living_ai = [ai for ai in game.ai_players if ai.alive and ai != self]
            if not living_ai:
                return None

            # Trouver l'IA la plus proche
            closest_ai = None
            min_distance = float('inf')
            for ai in living_ai:
                distance = abs(ai.grid_x - self.grid_x) + abs(ai.grid_y - self.grid_y)
                if distance < min_distance:
                    min_distance = distance
                    closest_ai = ai
            return closest_ai

        # Trouver le joueur le plus proche
        closest_player = None
        min_distance = float('inf')
        for player in living_players:
            distance = abs(player.grid_x - self.grid_x) + abs(player.grid_y - self.grid_y)
            if distance < min_distance:
                min_distance = distance
                closest_player = player
        return closest_player

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

    def can_move_to(self, grid_x, grid_y, game):
        """
        Vérifie si l'IA peut se déplacer vers une position donnée
        en tenant compte du rayon du cercle qui la représente
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

    def collect_power_up(self, power_up_type):
        """Collecte un power-up et met à jour les stats de l'IA"""
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
        """Place une bombe si possible"""
        if self.active_bombs < self.max_bombs and game.grid[self.grid_y][self.grid_x] == TileType.EMPTY:
            game.grid[self.grid_y][self.grid_x] = TileType.BOMB
            bomb = Bomb(self.grid_x, self.grid_y, self.bomb_power, self)
            game.bombs.append(bomb)
            self.active_bombs += 1
            # Mémoriser où on a posé la bombe
            self.previous_bomb_positions.append((self.grid_x, self.grid_y))
            return True
        return False

    def find_escape_path(self, game):
        """Trouve un chemin d'évacuation sûr depuis la position actuelle"""
        # Simuler une bombe à notre position
        simulated_bomb_power = self.bomb_power
        danger_tiles = set()

        # Calculer les cases qui seraient touchées
        # Centre
        danger_tiles.add((self.grid_x, self.grid_y))

        # 4 directions
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            for i in range(1, simulated_bomb_power + 1):
                nx, ny = self.grid_x + dx * i, self.grid_y + dy * i

                # Vérifier si on est dans les limites
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    danger_tiles.add((nx, ny))
                    # S'arrêter si on rencontre un mur ou un bloc
                    if game.grid[ny][nx] in [TileType.WALL, TileType.BLOCK]:
                        break

        # Rechercher une case sûre accessible
        for distance in range(1, 7):  # Distance Manhattan maximale
            for tx in range(max(0, self.grid_x - distance), min(GRID_WIDTH, self.grid_x + distance + 1)):
                for ty in range(max(0, self.grid_y - distance), min(GRID_HEIGHT, self.grid_y + distance + 1)):
                    # Vérifier si c'est une case à exactement "distance" de Manhattan
                    if abs(tx - self.grid_x) + abs(ty - self.grid_y) == distance:
                        # Si la case n'est pas dans la zone de danger
                        if (tx, ty) not in danger_tiles and self.can_move_to(tx, ty, game):
                            # Vérifier si on peut y accéder
                            path = self.find_path_to_position(tx, ty, game, max_depth=distance + 1, avoid_danger=True)
                            if path:
                                return path

        return None

    def manage_bombs(self, game):
        """Gère la stratégie de bombe selon le contexte actuel"""
        # Réduire le cooldown des bombes
        if self.bomb_cooldown > 0:
            return False

        # Ne pas poser de bombe si on a atteint le maximum
        if self.active_bombs >= self.max_bombs:
            return False

        target_player = self.find_target_player(game)
        current_danger = self.calculate_danger_level(self.grid_x, self.grid_y, game)

        # 1. Mode offensif: poser une bombe si un joueur est à proximité (aligné)
        if target_player and (target_player.grid_x == self.grid_x or target_player.grid_y == self.grid_y):
            distance = abs(target_player.grid_x - self.grid_x) + abs(target_player.grid_y - self.grid_y)
            if distance <= self.bomb_power:
                # Vérifier qu'il n'y a pas d'obstacles
                blocked = False
                if target_player.grid_x == self.grid_x:  # Même colonne
                    step = 1 if target_player.grid_y > self.grid_y else -1
                    for check_y in range(self.grid_y + step, target_player.grid_y, step):
                        if game.grid[check_y][self.grid_x] in [TileType.WALL, TileType.BLOCK]:
                            blocked = True
                            break
                else:  # Même ligne
                    step = 1 if target_player.grid_x > self.grid_x else -1
                    for check_x in range(self.grid_x + step, target_player.grid_x, step):
                        if game.grid[self.grid_y][check_x] in [TileType.WALL, TileType.BLOCK]:
                            blocked = True
                            break

                if not blocked:
                    # Vérifier si on a une voie d'évacuation
                    escape_path = self.find_escape_path(game)
                    if escape_path:
                        if self.place_bomb(game):
                            self.bomb_cooldown = random.randint(5, 15)
                            return True

        # 2. Mode destructeur: poser une bombe pour détruire des blocs et accéder à des zones
        # Vérifier s'il y a des blocs destructibles adjacents
        blocks_near = False
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = self.grid_x + dx, self.grid_y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if game.grid[ny][nx] == TileType.BLOCK:
                    blocks_near = True
                    break

        if blocks_near and current_danger <= 3:  # Ne pas poser si déjà en danger
            # S'assurer qu'on a un chemin de fuite
            escape_path = self.find_escape_path(game)
            if escape_path and random.random() < 0.7:  # 70% de chance de poser une bombe
                if self.place_bomb(game):
                    self.bomb_cooldown = random.randint(15, 30)
                    return True

        return False

    def make_ai_decision(self, game):
        """Prend une décision pour le prochain mouvement de l'IA"""
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

            # Essayer d'échapper au danger avec la stratégie d'évasion
            escaped = self.strategies.execute_escape_strategy(game)
            if escaped:
                # Exécuter le mouvement après avoir décidé la direction
                dx, dy = self.current_direction
                self.x += dx * self.speed
                self.y += dy * self.speed
                return

        # ÉTAPE 2: Suivre la stratégie actuelle
        if self.decision_cooldown > 0:
            self.decision_cooldown -= 1
        else:
            self.decision_cooldown = random.randint(3, 10)  # Réactif mais pas frénétique

            # Stratégie basée sur le mode actuel
            if self.strategy_mode == "hunt":
                self.strategies.execute_hunt_strategy(game)
            elif self.strategy_mode == "collect":
                self.strategies.execute_collect_strategy(game)
            elif self.strategy_mode == "trap":
                self.strategies.execute_trap_strategy(game)
            elif self.strategy_mode == "escape":
                # Si on était en mode échappement mais plus en danger, revenir au mode chasse
                if not current_position_dangerous:
                    self.reevaluate_strategy(game)
                    self.strategies.execute_hunt_strategy(game)  # Par défaut: chasser
                else:
                    self.strategies.execute_escape_strategy(game)

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

                # Déplacer l'IA dans la nouvelle direction
                dx, dy = self.current_direction
                self.x += dx * self.speed
                self.y += dy * self.speed
            else:
                # Aucune direction n'est possible, rester sur place
                if self.active_bombs < self.max_bombs and random.random() < 0.6:
                    self.place_bomb(game)

    def draw(self, screen, offset_x, offset_y):
        """Dessine l'IA sur l'écran"""
        # Dessiner le joueur (un cercle)
        x_pos = offset_x + self.x
        y_pos = offset_y + self.y
        pygame.draw.circle(screen, self.color, (x_pos, y_pos), self.radius)