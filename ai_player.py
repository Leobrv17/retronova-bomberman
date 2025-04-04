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
        self.bomb_cooldown = random.randint(20, 40)  # Délai plus raisonnable
        self.danger_awareness = 0.98  # Niveau encore plus élevé de conscience du danger
        self.game_time = 0  # Initialisation du temps de jeu
        self.last_safe_position = None  # Mémoriser la dernière position sûre connue

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
        self.last_bomb_position = None  # Position de la dernière bombe posée
        self.bomb_escape_path = None  # Chemin d'évacuation après avoir posé une bombe
        self.safe_tile_history = []  # Historique des cases sûres visitées récemment

        # Nouvelles variables pour l'évitement amélioré des bombes
        self.danger_map = {}  # Carte des dangers potentiels
        self.bomb_recovery_time = 0  # Temps d'attente avant de reposer une bombe après échec
        self.failed_attack_count = 0  # Nombre d'attaques échouées consécutives

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

        # Mettre à jour la carte des dangers
        self.update_danger_map(game)

        # Vérifier si l'IA est bloquée
        if len(self.last_positions) == 10 and len(set(self.last_positions)) <= 2:
            self.stuck_counter += 1
            if self.stuck_counter > 15:  # Réagir plus rapidement
                self.current_direction = random.choice([(0, -1), (1, 0), (0, 1), (-1, 0)])
                self.stuck_counter = 0

                # Vérifier si on peut poser une bombe sans danger
                safe_to_bomb = self.is_safe_to_place_bomb(game)
                if safe_to_bomb and random.random() < 0.7:
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
        if self.bomb_recovery_time > 0:
            self.bomb_recovery_time -= 1

        # Vérifier si la position actuelle est sûre
        current_danger = self.calculate_danger_level(self.grid_x, self.grid_y, game)
        if current_danger == 0:
            # Mémoriser cette position comme sûre
            self.last_safe_position = (self.grid_x, self.grid_y)

            # Ajouter à l'historique des cases sûres
            self.safe_tile_history.append((self.grid_x, self.grid_y))
            if len(self.safe_tile_history) > 20:  # Garder un historique limité
                self.safe_tile_history.pop(0)

        # Réévaluer périodiquement la stratégie
        self.strategy_timer += 1
        if self.strategy_timer >= 120:  # Environ 2 secondes à 60 FPS
            self.reevaluate_strategy(game)
            self.strategy_timer = 0

        # Faire une décision d'IA
        self.make_ai_decision(game)

    def update_map_knowledge(self, game):
        """Met à jour la connaissance de la carte par l'IA"""
        # Observer la grille dans un rayon de vision
        vision_radius = 6  # Augmenté pour une meilleure connaissance
        for y in range(max(0, self.grid_y - vision_radius), min(GRID_HEIGHT, self.grid_y + vision_radius + 1)):
            for x in range(max(0, self.grid_x - vision_radius), min(GRID_WIDTH, self.grid_x + vision_radius + 1)):
                # Enregistrer l'état de la case
                key = (x, y)
                self.map_knowledge[key] = game.grid[y][x]

                # Détecter les power-ups et les mémoriser
                if game.grid[y][x] in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
                    if key not in self.known_powerups:
                        self.known_powerups.append(key)

    def update_danger_map(self, game):
        """Met à jour une carte des niveaux de danger pour chaque case visible"""
        vision_radius = 8  # Plus large que la vision normale pour anticiper
        self.danger_map = {}

        for y in range(max(0, self.grid_y - vision_radius), min(GRID_HEIGHT, self.grid_y + vision_radius + 1)):
            for x in range(max(0, self.grid_x - vision_radius), min(GRID_WIDTH, self.grid_x + vision_radius + 1)):
                # Calculer et stocker le niveau de danger
                danger = self.calculate_danger_level(x, y, game)
                self.danger_map[(x, y)] = danger

                # Marquer également les cases qui seront touchées par des bombes existantes
                if self.is_tile_in_bomb_range(x, y, game):
                    self.danger_map[(x, y)] = max(self.danger_map.get((x, y), 0), 7)

    def is_tile_in_bomb_range(self, x, y, game):
        """Vérifie si une case est dans la portée d'une bombe existante"""
        for bomb in game.bombs:
            if bomb.x == x and bomb.y == y:
                return True

            # Vérifier si la case est alignée avec la bombe
            if bomb.x == x or bomb.y == y:
                # Calculer la distance
                distance = abs(bomb.x - x) + abs(bomb.y - y)

                # Si la distance est dans la portée de la bombe
                if distance <= bomb.power:
                    # Vérifier s'il y a des obstacles entre la bombe et la case
                    blocked = False

                    if bomb.x == x:  # Même colonne
                        start_y = min(bomb.y, y) + 1
                        end_y = max(bomb.y, y)
                        for check_y in range(start_y, end_y):
                            if game.grid[check_y][x] in [TileType.WALL, TileType.BLOCK]:
                                blocked = True
                                break
                    else:  # Même ligne
                        start_x = min(bomb.x, x) + 1
                        end_x = max(bomb.x, x)
                        for check_x in range(start_x, end_x):
                            if game.grid[y][check_x] in [TileType.WALL, TileType.BLOCK]:
                                blocked = True
                                break

                    if not blocked:
                        return True

        return False

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

        # AMÉLIORATION: Score de chasse plus intelligent
        if living_players:
            nearest_player = self.find_target_player(game)
            if nearest_player:
                distance = abs(nearest_player.grid_x - self.grid_x) + abs(nearest_player.grid_y - self.grid_y)
                # Score de base pour la chasse
                strategy_scores["hunt"] = 100 / (distance + 1) * self.personality["strategy_preference"].get("hunt",
                                                                                                             0.3)

                # Bonus pour la chasse si:
                # 1. On a plus de bombes ou de puissance que le joueur cible
                if self.max_bombs > nearest_player.max_bombs or self.bomb_power > nearest_player.bomb_power:
                    strategy_scores["hunt"] += 20

                # 2. Le joueur est aligné et à portée
                if (
                        nearest_player.grid_x == self.grid_x or nearest_player.grid_y == self.grid_y) and distance <= self.bomb_power + 1:
                    strategy_scores["hunt"] += 50

                # 3. Le joueur est dans un cul-de-sac
                if self.is_player_cornered(nearest_player, game):
                    strategy_scores["hunt"] += 40

        # AMÉLIORATION: Score de collection avec meilleures priorités
        if nearest_powerup_distance is not None:
            base_collect_score = 50 / (nearest_powerup_distance + 1) * self.personality["strategy_preference"].get(
                "collect", 0.3)
            strategy_scores["collect"] = base_collect_score

            # Prioriser les power-ups selon les besoins actuels
            if self.max_bombs < 2:
                # Besoin urgent de plus de bombes
                if self.are_specific_powerups_available(game, TileType.POWER_UP_BOMB):
                    strategy_scores["collect"] += 50
            elif self.bomb_power < 3:
                # Besoin d'augmenter la puissance
                if self.are_specific_powerups_available(game, TileType.POWER_UP_FLAME):
                    strategy_scores["collect"] += 40
            elif self.speed < 4:
                # Besoin de vitesse
                if self.are_specific_powerups_available(game, TileType.POWER_UP_SPEED):
                    strategy_scores["collect"] += 30

        # Score pour le piège - prioriser si on a beaucoup de bombes
        if self.active_bombs == 0 and self.max_bombs > 1:
            strategy_scores["trap"] = 30 * self.personality["strategy_preference"].get("trap", 0.3)

            # Favoriser le piège si cible à proximité et vulnérable
            nearest_player = self.find_target_player(game)
            if nearest_player and self.max_bombs >= 2:
                distance = abs(nearest_player.grid_x - self.grid_x) + abs(nearest_player.grid_y - self.grid_y)
                if distance <= 4:  # Assez proche pour un piège
                    # Vérifier si le joueur est dans un espace restreint
                    open_tiles_around_player = self.count_open_tiles_around(nearest_player.grid_x,
                                                                            nearest_player.grid_y, game)
                    if open_tiles_around_player <= 2:  # Joueur avec peu d'options de fuite
                        strategy_scores["trap"] += 60

        # Score pour l'échappement - priorité absolue si en danger immédiat
        if in_danger:
            strategy_scores["escape"] = 100
        else:
            # Même sans danger immédiat, vérifier le niveau de danger à proximité
            adjacent_danger = 0
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = self.grid_x + dx, self.grid_y + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    if self.is_tile_in_danger(nx, ny, game):
                        adjacent_danger += 1

            # Si plusieurs cases adjacentes sont dangereuses, envisager l'évacuation
            if adjacent_danger >= 2:
                strategy_scores["escape"] = 80

        # Choisir la stratégie avec le score le plus élevé
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        self.strategy_mode = best_strategy

    def are_specific_powerups_available(self, game, powerup_type):
        """Vérifie si des power-ups spécifiques sont disponibles et accessibles"""
        for x, y in self.known_powerups:
            if game.grid[y][x] == powerup_type:
                # Vérifier si le power-up est accessible
                path = self.find_path_to_position(x, y, game)
                if path:
                    return True
        return False

    def is_player_cornered(self, player, game):
        """Vérifie si un joueur est coincé dans un espace restreint"""
        open_directions = 0
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = player.grid_x + dx, player.grid_y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if game.grid[ny][nx] == TileType.EMPTY:
                    open_directions += 1

        # Si le joueur a moins de 2 directions ouvertes, il est considéré comme coincé
        return open_directions < 2

    def count_open_tiles_around(self, x, y, game):
        """Compte le nombre de cases libres autour d'une position"""
        count = 0
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if game.grid[ny][nx] == TileType.EMPTY:
                    count += 1
        return count

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

            # Trouver l'IA la plus proche ou la plus vulnérable
            best_target = None
            best_score = -float('inf')

            for ai in living_ai:
                distance = abs(ai.grid_x - self.grid_x) + abs(ai.grid_y - self.grid_y)

                # Score basé sur la distance (plus proche = meilleur)
                score = 100 - distance * 5

                # Bonus si l'IA cible a moins de bombes ou moins de puissance
                if ai.max_bombs < self.max_bombs:
                    score += 15
                if ai.bomb_power < self.bomb_power:
                    score += 15
                if ai.speed < self.speed:
                    score += 10

                # Bonus si l'IA est dans un espace restreint
                open_tiles = self.count_open_tiles_around(ai.grid_x, ai.grid_y, game)
                if open_tiles <= 2:
                    score += 30

                if score > best_score:
                    best_score = score
                    best_target = ai

            return best_target

        # Trouver le joueur le plus intéressant à cibler
        best_target = None
        best_score = -float('inf')

        for player in living_players:
            distance = abs(player.grid_x - self.grid_x) + abs(player.grid_y - self.grid_y)

            # Score basé sur la distance (plus proche = meilleur)
            score = 100 - distance * 5

            # Bonus si le joueur a moins de bombes ou moins de puissance
            if player.max_bombs < self.max_bombs:
                score += 20
            if player.bomb_power < self.bomb_power:
                score += 20
            if player.speed < self.speed:
                score += 15

            # Bonus si le joueur est dans un espace restreint
            open_tiles = self.count_open_tiles_around(player.grid_x, player.grid_y, game)
            if open_tiles <= 2:
                score += 40

            # Bonus si le joueur est aligné (même ligne ou colonne)
            if player.grid_x == self.grid_x or player.grid_y == self.grid_y:
                # Vérifier si aucun obstacle entre nous
                if self.has_clear_line_of_sight(self.grid_x, self.grid_y, player.grid_x, player.grid_y, game):
                    score += 50

            if score > best_score:
                best_score = score
                best_target = player

        return best_target

    def has_clear_line_of_sight(self, x1, y1, x2, y2, game):
        """Vérifie s'il y a une ligne de vue dégagée entre deux positions"""
        # Si les positions ne sont pas alignées, pas de ligne de vue
        if x1 != x2 and y1 != y2:
            return False

        if x1 == x2:  # Même colonne
            start_y = min(y1, y2) + 1
            end_y = max(y1, y2)
            for y in range(start_y, end_y):
                if game.grid[y][x1] in [TileType.WALL, TileType.BLOCK]:
                    return False
        else:  # Même ligne
            start_x = min(x1, x2) + 1
            end_x = max(x1, x2)
            for x in range(start_x, end_x):
                if game.grid[y1][x] in [TileType.WALL, TileType.BLOCK]:
                    return False

        return True

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
        danger_level += adjacent_dangers * 2.5  # Augmenté pour plus de prudence

        # Vérifier la proximité des bombes
        for bomb in game.bombs:
            distance = abs(bomb.x - x) + abs(bomb.y - y)
            if distance <= bomb.power + 1:  # +1 pour la zone adjacente
                # Plus proche = plus dangereux, avec un facteur plus élevé
                danger_level += max(0, 6 - distance)

        return min(danger_level, 9)

    def find_safest_position(self, game, max_distance=8):
        """Trouve la position la plus sûre dans un rayon donné"""
        best_position = None
        lowest_danger = float('inf')

        # Stratégies d'évacuation améliorées
        evacuation_strategies = [
            # 1. Chercher d'abord dans les cases déjà visitées et connues comme sûres
            self.safe_tile_history,

            # 2. Chercher d'abord dans les cases plus proches
            [(self.grid_x + dx, self.grid_y + dy) for distance in range(1, 4)
             for dx, dy in [(dx, dy) for dx in range(-distance, distance + 1)
                            for dy in range(-distance, distance + 1)
                            if abs(dx) + abs(dy) == distance]],

            # 3. Chercher plus largement
            [(self.grid_x + dx, self.grid_y + dy) for distance in range(4, max_distance + 1)
             for dx, dy in [(dx, dy) for dx in range(-distance, distance + 1)
                            for dy in range(-distance, distance + 1)
                            if abs(dx) + abs(dy) == distance]]
        ]

        # Si on a une dernière position sûre connue, l'ajouter en priorité
        if self.last_safe_position:
            potential_positions = [self.last_safe_position]
            potential_positions.extend([pos for strategy in evacuation_strategies for pos in strategy])
        else:
            potential_positions = [pos for strategy in evacuation_strategies for pos in strategy]

        # Filtrer les positions pour ne conserver que celles dans la grille
        valid_positions = [(x, y) for x, y in potential_positions
                           if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT]

        # Évaluer chaque position
        for x, y in valid_positions:
            # Vérifier si c'est une position atteignable
            path = self.find_path_to_position(x, y, game)
            if path:
                # Calculer le danger à cette position
                danger = self.calculate_danger_level(x, y, game)

                # Facteur de distance: préférer les positions plus proches à danger égal
                distance_factor = 0.1 * (abs(x - self.grid_x) + abs(y - self.grid_y))

                # Score total (danger + facteur de distance)
                total_danger = danger + distance_factor

                if total_danger < lowest_danger:
                    lowest_danger = total_danger
                    best_position = (x, y)

                    # Si on trouve une position parfaitement sûre et proche, la prendre immédiatement
                    if danger == 0 and abs(x - self.grid_x) + abs(y - self.grid_y) <= 3:
                        return (x, y)

        # Si on trouve une position sûre, la mémoriser
        if best_position and self.calculate_danger_level(best_position[0], best_position[1], game) == 0:
            self.last_safe_position = best_position

        return best_position

    def can_move_to(self, grid_x, grid_y, game):
        """
        Vérifie si l'IA peut se déplacer vers une position donnée
        en tenant compte du rayon du cercle qui la représente
        et en évitant les blocages dans les angles
        """
        # Vérifier si la position est hors de la grille
        if grid_x < 0 or grid_x >= GRID_WIDTH or grid_y < 0 or grid_y >= GRID_HEIGHT:
            return False

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
        left_grid = max(0, int(left_x))
        right_grid = min(GRID_WIDTH - 1, int(right_x))
        top_grid = max(0, int(top_y))
        bottom_grid = min(GRID_HEIGHT - 1, int(bottom_y))

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

                        # Pour les obstacles rectangulaires, on calcule la distance au bord le plus proche
                        closest_x = max(check_x, min(center_x, check_x + 1))
                        closest_y = max(check_y, min(center_y, check_y + 1))

                        # Distance entre le centre du cercle et le point le plus proche du rectangle
                        distance = ((center_x - closest_x) ** 2 + (center_y - closest_y) ** 2) ** 0.5

                        # Si cette distance est inférieure au rayon, il y a collision
                        if distance < radius_in_grid:
                            return False

        # Vérifier s'il y a une bombe
        has_bomb = False
        bomb_is_own = False
        bomb_just_placed = False

        if game.grid[grid_y][grid_x] == TileType.BOMB:
            has_bomb = True
            # Vérifier si on est déjà sur une bombe (pour pouvoir en sortir)
            current_on_bomb = game.grid[self.grid_y][self.grid_x] == TileType.BOMB

            # Si on est sur une bombe, on peut se déplacer vers une autre bombe ou une case vide
            if current_on_bomb:
                return True

            # Sinon, vérifier si c'est notre bombe récemment posée
            for bomb in game.bombs:
                if bomb.x == grid_x and bomb.y == grid_y:
                    if bomb.owner == self:
                        bomb_is_own = True
                        if bomb.just_placed:
                            bomb_just_placed = True
                            break

            # Si ce n'est pas notre bombe récemment posée, on ne peut pas y aller
            if not bomb_just_placed:
                return False

        # NOUVEAU: Vérification spéciale pour les angles entre bombes et murs
        # Cela permet d'éviter les blocages dans les coins
        if has_bomb and bomb_is_own:
            # Vérifier si on essaye de sortir d'une bombe qu'on vient de poser
            # qui pourrait nous bloquer contre un mur en diagonale

            # Compter les obstacles diagonaux
            diagonal_obstacles = 0
            for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                check_x, check_y = grid_x + dx, grid_y + dy
                if 0 <= check_x < GRID_WIDTH and 0 <= check_y < GRID_HEIGHT:
                    if game.grid[check_y][check_x] in [TileType.WALL, TileType.BLOCK]:
                        diagonal_obstacles += 1

            # S'il y a des obstacles diagonaux, vérifier si on risque de se bloquer
            if diagonal_obstacles > 0:
                # Vérifier les cases adjacentes pour voir si on a une voie de sortie
                open_directions = 0
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = grid_x + dx, grid_y + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if game.grid[ny][nx] == TileType.EMPTY:
                            open_directions += 1

                # Si on a peu de directions ouvertes, c'est un risque de blocage
                if open_directions <= 1:
                    # Sortir immédiatement de la bombe
                    return True

        return True

    def find_path_to_position(self, target_x, target_y, game, max_depth=8, avoid_danger=True):
        """Trouve un chemin vers une position cible avec un évitement amélioré des dangers"""
        if target_x == self.grid_x and target_y == self.grid_y:
            return [(self.grid_x, self.grid_y)]

        # Vérifier si la cible est valide
        if not (0 <= target_x < GRID_WIDTH and 0 <= target_y < GRID_HEIGHT):
            return None

        # Si la cible est un mur ou un bloc, impossible d'y aller
        if game.grid[target_y][target_x] in [TileType.WALL, TileType.BLOCK]:
            return None

        # File pour BFS avec priorité
        # Format: (priorité, (x, y, chemin_actuel))
        from queue import PriorityQueue
        queue = PriorityQueue()
        queue.put((0, (self.grid_x, self.grid_y, [])))
        visited = set([(self.grid_x, self.grid_y)])

        while not queue.empty():
            _, (x, y, path) = queue.get()
            current_path = path + [(x, y)]

            # Limiter la profondeur de recherche
            if len(current_path) > max_depth:
                continue

            # Si on est arrivé à destination
            if x == target_x and y == target_y:
                return current_path

            # Vérifier les 4 directions
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = x + dx, y + dy

                # Vérifier si la position est valide et non visitée
                if (nx, ny) not in visited and self.can_move_to(nx, ny, game):
                    # Calculer la priorité (plus faible = meilleure)
                    # Distance restante jusqu'à la cible
                    remaining_distance = abs(nx - target_x) + abs(ny - target_y)

                    # Niveau de danger de la case
                    danger = 0
                    if avoid_danger:
                        danger = self.calculate_danger_level(nx, ny, game) * 2

                        # Si le danger est maximum et qu'on n'est pas désespéré, éviter
                        if danger >= 8 and random.random() > self.risk_tolerance:
                            continue

                    # Priorité = distance + danger + longueur du chemin
                    priority = remaining_distance + danger + len(current_path)

                    visited.add((nx, ny))
                    queue.put((priority, (nx, ny, current_path)))

        # Pas de chemin trouvé
        return None

    def find_path_to_target(self, target_x, target_y, game, max_depth=10):
        """Algorithme pathfinding amélioré avec différentes stratégies selon la personnalité"""
        # Utiliser le pathfinding de base avec des variantes selon la personnalité
        if self.path_preference == "direct":
            # Chemin direct mais avec un évitement minimal du danger
            return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=False)

        elif self.path_preference == "safe":
            # Priorité absolue à la sécurité
            return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=True)

        elif self.path_preference == "tricky":
            # Chemin imprévisible qui peut passer par des détours
            if random.random() < 0.4:  # 40% de chance de prendre un détour
                # Trouver un point intermédiaire
                intermediate_positions = []

                # Générer des positions intermédiaires potentielles
                for dx in range(-4, 5):
                    for dy in range(-4, 5):
                        if abs(dx) + abs(dy) <= 5:  # Limiter à une distance raisonnable
                            ix, iy = self.grid_x + dx, self.grid_y + dy
                            if 0 <= ix < GRID_WIDTH and 0 <= iy < GRID_HEIGHT:
                                if game.grid[iy][ix] == TileType.EMPTY:
                                    # Calculer les distances
                                    dist_from_self = abs(ix - self.grid_x) + abs(iy - self.grid_y)
                                    dist_to_target = abs(ix - target_x) + abs(iy - target_y)

                                    # Ne considérer que les points qui ne nous éloignent pas trop
                                    if dist_from_self + dist_to_target <= abs(target_x - self.grid_x) + abs(
                                            target_y - self.grid_y) + 4:
                                        intermediate_positions.append((ix, iy))

                if intermediate_positions:
                    # Choisir un point intermédiaire aléatoire parmi les candidats
                    ix, iy = random.choice(intermediate_positions)
                    path1 = self.find_path_to_position(ix, iy, game, max_depth // 2)

                    if path1:
                        # Continuer depuis ce point intermédiaire
                        path2 = self.find_path_to_position(target_x, target_y, game, max_depth // 2)
                        if path2 and len(path2) > 1:
                            return path1[:-1] + path2  # Éviter de dupliquer le point intermédiaire

            # Fallback au chemin avec évitement moyen du danger
            return self.find_path_to_position(target_x, target_y, game, max_depth, avoid_danger=(random.random() < 0.7))

        else:  # "balanced" ou autre
            # Équilibre entre sécurité et rapidité
            if random.random() < 0.7:  # 70% de priorité à la sécurité
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

    def is_safe_to_place_bomb(self, game):
        """Vérifie s'il est sûr de placer une bombe à la position actuelle"""
        # Simuler la pose d'une bombe
        danger_tiles = self.calculate_bomb_affected_tiles(self.grid_x, self.grid_y, game)

        # Vérifier si on peut s'échapper après avoir posé la bombe
        escape_path = self.find_escape_path_from_bomb(game, danger_tiles)

        # MODIFICATION: Réduire la prudence - si la position actuelle est dangereuse,
        # on devrait être plus enclin à poser une bombe
        current_danger = self.calculate_danger_level(self.grid_x, self.grid_y, game)

        # Si on est déjà en danger, plus de raisons de ne pas poser une bombe
        # tant qu'on a un chemin d'évacuation
        if current_danger > 0 and escape_path is not None:
            return True

        # MODIFICATION: Réduire les critères de sécurité
        return escape_path is not None

    def calculate_bomb_affected_tiles(self, bomb_x, bomb_y, game):
        """Calcule les cases qui seraient affectées par une bombe à la position spécifiée"""
        affected_tiles = set([(bomb_x, bomb_y)])  # La case de la bombe

        # 4 directions
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            for i in range(1, self.bomb_power + 1):
                nx, ny = bomb_x + dx * i, bomb_y + dy * i

                # Vérifier si on est dans les limites
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    affected_tiles.add((nx, ny))

                    # S'arrêter si on rencontre un mur ou un bloc
                    if game.grid[ny][nx] in [TileType.WALL, TileType.BLOCK]:
                        break
                else:
                    break

        return affected_tiles

    def place_bomb(self, game):
        """Place une bombe si possible, avec vérification de sécurité relaxée"""
        if self.active_bombs < self.max_bombs and game.grid[self.grid_y][self.grid_x] == TileType.EMPTY:
            # MODIFICATION: Réduire les contraintes pour poser une bombe
            is_safe = self.is_safe_to_place_bomb(game)

            # Prendre plus de risques selon le niveau d'agressivité
            risk_threshold = 0.7 - self.aggression_level * 0.5  # Plus agressif = moins prudent

            # MODIFICATION: Parfois placer une bombe même si ce n'est pas totalement sûr
            if self.bomb_cooldown <= 0 and (is_safe or random.random() > risk_threshold):
                game.grid[self.grid_y][self.grid_x] = TileType.BOMB
                bomb = Bomb(self.grid_x, self.grid_y, self.bomb_power, self)
                game.bombs.append(bomb)
                self.active_bombs += 1

                # Mémoriser les informations de la bombe
                self.last_bomb_position = (self.grid_x, self.grid_y)
                self.previous_bomb_positions.append((self.grid_x, self.grid_y))

                # Trouver immédiatement un chemin d'évacuation
                danger_tiles = self.calculate_bomb_affected_tiles(self.grid_x, self.grid_y, game)
                self.bomb_escape_path = self.find_escape_path_from_bomb(game, danger_tiles)

                # Préparer le cooldown pour la prochaine bombe (réduit)
                self.bomb_cooldown = random.randint(10, 20)  # Réduit pour poser plus souvent

                # Reset du compteur d'échecs
                self.failed_attack_count = 0

                return True
            else:
                # Incrémenter le compteur d'échecs si on ne peut pas poser de bombe en sécurité
                self.failed_attack_count += 1

                # MODIFICATION: Réduire le temps de récupération
                if self.failed_attack_count >= 3:
                    self.bomb_recovery_time = 30  # Réduit à 0.5 seconde à 60 FPS
                    self.failed_attack_count = 0

        return False

    def find_escape_path_from_bomb(self, game, danger_tiles):
        """Trouve un chemin d'évacuation sûr depuis la position actuelle, en évitant les cases dangereuses et les angles"""
        # NOUVEAU: Calculer en premier les directions possibles immédiates
        immediate_escapes = []

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = self.grid_x + dx, self.grid_y + dy

            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in danger_tiles:
                if game.grid[ny][nx] == TileType.EMPTY:
                    # Vérifier si cette direction nous mène dans un angle

                    # Compter les obstacles dans cette direction
                    corner_risk = 0
                    for cdx, cdy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        if cdx == -dx and cdy == -dy:  # Ne pas compter la direction d'où on vient
                            continue

                        cx, cy = nx + cdx, ny + cdy
                        if not (0 <= cx < GRID_WIDTH and 0 <= cy < GRID_HEIGHT) or \
                                game.grid[cy][cx] in [TileType.WALL, TileType.BLOCK, TileType.BOMB]:
                            corner_risk += 1

                    # Si cette direction a peu de risque d'angle, la prioriser
                    score = 3 - corner_risk  # Score de 0 à 3 (3 = meilleur)
                    immediate_escapes.append((score, (nx, ny)))

        # Si on a des sorties immédiates sans risque d'angle, les prioriser
        if immediate_escapes:
            immediate_escapes.sort(reverse=True)  # Trier par score décroissant
            best_score, best_pos = immediate_escapes[0]

            # Si on a une bonne sortie immédiate, la prendre
            if best_score >= 2:
                return [(self.grid_x, self.grid_y), best_pos]

        # Rechercher une case sûre accessible dans un rayon plus large
        for distance in range(1, self.bomb_power + 3):  # Distance suffisante pour s'échapper
            positions_to_check = []

            # Générer les positions à cette distance
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    if abs(dx) + abs(dy) == distance:  # Exactement à cette distance de Manhattan
                        tx, ty = self.grid_x + dx, self.grid_y + dy

                        if 0 <= tx < GRID_WIDTH and 0 <= ty < GRID_HEIGHT:
                            # Si la case n'est pas dans la zone de danger et est accessible
                            if (tx, ty) not in danger_tiles and game.grid[ty][tx] == TileType.EMPTY:
                                # Évaluer le risque d'être coincé dans un angle à cette position
                                corner_risk = 0
                                for cdx, cdy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                                    cx, cy = tx + cdx, ty + cdy
                                    if not (0 <= cx < GRID_WIDTH and 0 <= cy < GRID_HEIGHT) or \
                                            game.grid[cy][cx] in [TileType.WALL, TileType.BLOCK, TileType.BOMB]:
                                        corner_risk += 1

                                # Ajouter cette position avec un score
                                positions_to_check.append((corner_risk, (tx, ty)))

            # Trier les positions par risque d'angle croissant
            positions_to_check.sort()

            # Essayer de trouver un chemin vers ces positions, en commençant par les moins risquées
            for risk, (tx, ty) in positions_to_check:
                # Calculer un chemin en évitant les cases dangereuses
                path = self.find_safe_path(self.grid_x, self.grid_y, tx, ty, game, danger_tiles)
                if path and len(path) > 1:
                    return path

        # S'il n'y a pas de chemin sûr optimal, essayer de trouver n'importe quel chemin
        # même avec risque d'angle, pour éviter de rester bloqué sur la bombe
        all_possible_escapes = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = self.grid_x + dx, self.grid_y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if (nx, ny) not in danger_tiles and game.grid[ny][nx] == TileType.EMPTY:
                    # Simple priorité par distance à la bombe
                    all_possible_escapes.append([(self.grid_x, self.grid_y), (nx, ny)])

        if all_possible_escapes:
            return all_possible_escapes[0]

        return None

    def find_safe_path(self, start_x, start_y, target_x, target_y, game, danger_tiles):
        """Trouve un chemin sûr évitant les cases dangereuses"""
        from queue import PriorityQueue
        queue = PriorityQueue()
        queue.put((0, (start_x, start_y, [])))
        visited = set([(start_x, start_y)])

        max_depth = self.bomb_power + 5  # Profondeur suffisante pour s'échapper

        while not queue.empty():
            _, (x, y, path) = queue.get()
            current_path = path + [(x, y)]

            # Limiter la profondeur
            if len(current_path) > max_depth:
                continue

            # Si on a atteint la cible
            if x == target_x and y == target_y:
                return current_path

            # Explorer les 4 directions
            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nx, ny = x + dx, y + dy

                # Vérifier si la position est valide
                if (nx, ny) not in visited and self.can_move_to(nx, ny, game):
                    # Ne pas passer par les cases dangereuses
                    if (nx, ny) not in danger_tiles:
                        # Priorité = distance à la cible + longueur du chemin
                        priority = abs(nx - target_x) + abs(ny - target_y) + len(current_path)
                        visited.add((nx, ny))
                        queue.put((priority, (nx, ny, current_path)))

        return None

    def manage_bombs(self, game):
        """Gère la stratégie de bombe selon le contexte actuel avec plus d'agressivité"""
        # Réduire le cooldown des bombes
        if self.bomb_cooldown > 0 or self.bomb_recovery_time > 0:
            return False

        # Ne pas poser de bombe si on a atteint le maximum
        if self.active_bombs >= self.max_bombs:
            return False

        target_player = self.find_target_player(game)
        current_danger = self.calculate_danger_level(self.grid_x, self.grid_y, game)

        # MODIFICATION: Être plus tolérant au danger
        if current_danger >= 8:  # Augmenté de 5 à 8
            return False

        # 1. Mode offensif: poser une bombe si un joueur est à proximité (aligné)
        if target_player and (target_player.grid_x == self.grid_x or target_player.grid_y == self.grid_y):
            distance = abs(target_player.grid_x - self.grid_x) + abs(target_player.grid_y - self.grid_y)
            if distance <= self.bomb_power + 1:  # +1 pour être plus agressif
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
                    # MODIFICATION: Augmenter la probabilité de placer une bombe
                    if random.random() < (0.7 + self.aggression_level * 0.3):  # Jusqu'à 100% avec aggression max
                        return self.place_bomb(game)

        # 2. Mode destructeur: poser une bombe pour détruire des blocs et accéder à des zones
        blocks_near = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = self.grid_x + dx, self.grid_y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if game.grid[ny][nx] == TileType.BLOCK:
                    blocks_near.append((nx, ny))

        # MODIFICATION: Condition plus souple pour détruire des blocs
        if blocks_near and current_danger <= 5:  # Augmenté de 3 à 5
            # Vérifier s'il y a des power-ups derrière des blocs (si connus)
            powerup_behind_block = False
            for bx, by in blocks_near:
                # Vérifier dans la même direction mais un cran plus loin
                dx, dy = bx - self.grid_x, by - self.grid_y
                px, py = bx + dx, by + dy

                if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                    if game.grid[py][px] in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
                        powerup_behind_block = True
                        break

            # Déterminer la probabilité de poser une bombe selon la situation
            bomb_probability = 0.8  # Augmenté de 0.7 à 0.8

            if powerup_behind_block:
                bomb_probability += 0.2

            if len(blocks_near) >= 2:
                bomb_probability += 0.1

            if self.max_bombs < 2 or self.bomb_power < 3:
                bomb_probability += 0.1

            # MODIFICATION: Augmenter encore la probabilité dans certains cas
            if random.random() < 0.2:  # 20% de chances d'être plus téméraire
                bomb_probability += 0.1

            if random.random() < bomb_probability:
                return self.place_bomb(game)

        # MODIFICATION: Placement aléatoire de bombes à faible probabilité
        # pour rendre l'IA moins prévisible et plus agressive
        if self.active_bombs == 0 and random.random() < 0.1 * self.aggression_level:
            return self.place_bomb(game)

        return False

    def make_ai_decision(self, game):
        """Prend une décision pour le prochain mouvement de l'IA avec gestion améliorée des blocages"""
        # Mettre à jour les variables de temps
        self.game_time = game.game_time if hasattr(game, 'game_time') else 0

        # Décrémentation des compteurs
        if self.move_cooldown > 0:
            self.move_cooldown -= 1
            return

        # AJOUT: Détection de blocage dans les angles
        # Vérifier si l'IA semble bloquée contre un mur et une bombe
        is_corner_trapped = False

        # Vérifier si on est actuellement sur ou près d'une bombe
        on_bomb = game.grid[self.grid_y][self.grid_x] == TileType.BOMB

        # Compter les obstacles adjacents (murs, blocs, bombes)
        obstacles_adjacent = 0
        bomb_adjacent = False

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = self.grid_x + dx, self.grid_y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if game.grid[ny][nx] in [TileType.WALL, TileType.BLOCK]:
                    obstacles_adjacent += 1
                elif game.grid[ny][nx] == TileType.BOMB:
                    obstacles_adjacent += 1
                    bomb_adjacent = True

        # Si on a beaucoup d'obstacles autour et qu'on est près d'une bombe,
        # on est probablement coincé dans un angle
        if (obstacles_adjacent >= 2 and (on_bomb or bomb_adjacent)) or obstacles_adjacent >= 3:
            is_corner_trapped = True

        # Si on est coincé, priorité immédiate à l'évacuation
        if is_corner_trapped:
            # Chercher n'importe quelle direction libre
            available_moves = []
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = self.grid_x + dx, self.grid_y + dy
                if self.can_move_to(nx, ny, game) and game.grid[ny][nx] != TileType.BOMB:
                    danger = self.calculate_danger_level(nx, ny, game)
                    available_moves.append((danger, (dx, dy)))

            if available_moves:
                # Prendre la direction la moins dangereuse
                available_moves.sort()
                self.current_direction = available_moves[0][1]
                dx, dy = self.current_direction
                self.x += dx * self.speed
                self.y += dy * self.speed
                return

        # ÉTAPE 1: Vérifier si on est en danger immédiat
        current_position_dangerous = self.is_tile_in_danger(self.grid_x, self.grid_y, game)

        # Si on vient de poser une bombe et qu'on a un chemin d'évacuation, le suivre
        if self.bomb_escape_path and len(self.bomb_escape_path) > 1:
            next_x, next_y = self.bomb_escape_path[1]
            dx = 1 if next_x > self.grid_x else -1 if next_x < self.grid_x else 0
            dy = 1 if next_y > self.grid_y else -1 if next_y < self.grid_y else 0
            self.current_direction = (dx, dy)

            # Avancer dans le chemin d'évacuation
            if self.x % TILE_SIZE == TILE_SIZE // 2 and self.y % TILE_SIZE == TILE_SIZE // 2:
                self.bomb_escape_path.pop(0)

                # Si le chemin est terminé, l'effacer
                if len(self.bomb_escape_path) <= 1:
                    self.bomb_escape_path = None

            # Exécuter le mouvement
            dx, dy = self.current_direction
            self.x += dx * self.speed
            self.y += dy * self.speed
            return

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
            self.decision_cooldown = random.randint(3, 8)  # Plus réactif

            # Stratégie basée sur le mode actuel
            if self.strategy_mode == "hunt":
                self.strategies.execute_hunt_strategy(game)
            elif self.strategy_mode == "collect":
                self.strategies.execute_collect_strategy(game)
            elif self.strategy_mode == "trap":
                self.strategies.execute_trap_strategy(game)
            elif self.strategy_mode == "escape":
                # Si on était en mode échappement mais plus en danger, revenir au mode précédent
                if not current_position_dangerous:
                    self.reevaluate_strategy(game)
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
                    # MODIFICATION: Pénaliser fortement les mouvements vers les bombes
                    # sauf si c'est notre seule option
                    extra_penalty = 0
                    if game.grid[test_y][test_x] == TileType.BOMB:
                        extra_penalty = 50

                    # Calculer un score pour cette direction
                    score = 0 - extra_penalty

                    # Facteur de danger (inverser pour que moins dangereux = score plus élevé)
                    danger = self.calculate_danger_level(test_x, test_y, game)
                    score -= danger * 15  # Fortement pénaliser le danger

                    # Facteur d'objectif selon la stratégie actuelle
                    if self.strategy_mode == "hunt":
                        target = self.find_target_player(game)
                        if target:
                            # Distance au joueur (plus proche = score plus élevé)
                            distance = abs(test_x - target.grid_x) + abs(test_y - target.grid_y)
                            score += 25 - min(25, distance)

                            # Bonus pour les directions qui permettent de s'aligner avec la cible
                            if test_x == target.grid_x or test_y == target.grid_y:
                                # Vérifier s'il n'y a pas d'obstacles
                                if self.has_clear_line_of_sight(test_x, test_y, target.grid_x, target.grid_y, game):
                                    score += 30

                    elif self.strategy_mode == "collect":
                        # Proximité aux power-ups connus
                        for px, py in self.known_powerups:
                            distance = abs(test_x - px) + abs(test_y - py)
                            # Vérifier si le power-up est toujours là
                            if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                                if game.grid[py][px] in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME,
                                                         TileType.POWER_UP_SPEED]:
                                    score += 40 - min(40, distance * 2)

                                    # Bonus pour les power-ups prioritaires
                                    if (game.grid[py][
                                            px] == TileType.POWER_UP_BOMB and self.powerup_priority == "bomb") or \
                                            (game.grid[py][
                                                 px] == TileType.POWER_UP_FLAME and self.powerup_priority == "flame") or \
                                            (game.grid[py][
                                                 px] == TileType.POWER_UP_SPEED and self.powerup_priority == "speed"):
                                        score += 15

                    elif self.strategy_mode == "trap":
                        # Proximité aux blocs destructibles
                        blocks_near = 0
                        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                            bx, by = test_x + dx, test_y + dy
                            if 0 <= bx < GRID_WIDTH and 0 <= by < GRID_HEIGHT:
                                if game.grid[by][bx] == TileType.BLOCK:
                                    blocks_near += 1

                        score += blocks_near * 10

                        # Proximité aux joueurs/IA
                        for entity in game.players + game.ai_players:
                            if entity != self and entity.alive:
                                distance = abs(test_x - entity.grid_x) + abs(test_y - entity.grid_y)
                                if distance <= 3:  # Assez proche pour piéger
                                    score += 25 - distance * 5

                                    # Bonus si on peut s'aligner
                                    if test_x == entity.grid_x or test_y == entity.grid_y:
                                        score += 15

                    elif self.strategy_mode == "escape":
                        # Favoriser les directions qui s'éloignent des dangers
                        for bomb in game.bombs:
                            distance_from_bomb = abs(test_x - bomb.x) + abs(test_y - bomb.y)
                            # Plus on s'éloigne, mieux c'est
                            score += min(20, distance_from_bomb * 2)

                        # Favoriser les directions vers des cases connues comme sûres
                        if self.last_safe_position:
                            safe_x, safe_y = self.last_safe_position
                            distance_to_safe = abs(test_x - safe_x) + abs(test_y - safe_y)
                            score += 30 - min(30, distance_to_safe * 3)

                    # AJOUT: Pénaliser les directions qui nous mènent vers des angles
                    # Compter les obstacles dans cette direction
                    corner_risk = 0
                    for cdx, cdy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        cx, cy = test_x + cdx, test_y + cdy
                        if not (0 <= cx < GRID_WIDTH and 0 <= cy < GRID_HEIGHT) or \
                                game.grid[cy][cx] in [TileType.WALL, TileType.BLOCK]:
                            corner_risk += 1

                    # Pénaliser les directions qui mènent vers des angles
                    if corner_risk >= 2:
                        score -= 15 * (corner_risk - 1)

                    # Ajouter la direction avec son score
                    possible_directions.append((score, direction))

            if possible_directions:
                # Trier par score décroissant
                possible_directions.sort(reverse=True)

                # Introduire un peu d'aléatoire dans le choix
                top_n = min(2, len(possible_directions))

                # Choisir parmi les meilleures options avec un peu d'aléatoire
                # Plus grande chance de prendre la meilleure direction
                weights = [0.8, 0.2] if top_n == 2 else [1.0]
                selected_index = random.choices(range(top_n), weights=weights[:top_n])[0]
                self.current_direction = possible_directions[selected_index][1]

                # Déplacer l'IA dans la nouvelle direction
                dx, dy = self.current_direction
                self.x += dx * self.speed
                self.y += dy * self.speed
            else:
                # Aucune direction n'est possible, rester sur place
                # Mais essayer de poser une bombe si c'est sûr
                if self.active_bombs < self.max_bombs and self.is_safe_to_place_bomb(game):
                    self.place_bomb(game)


    def draw(self, screen, offset_x, offset_y):
        """Dessine l'IA sur l'écran"""
        # Dessiner le joueur (un cercle)
        x_pos = offset_x + self.x
        y_pos = offset_y + self.y
        pygame.draw.circle(screen, self.color, (x_pos, y_pos), self.radius)