import random
from contantes import *
from bomb import Bomb


class AIStrategies:
    def __init__(self, ai_player):
        """Initialise le module de stratégies avec une référence à l'IA parent"""
        self.ai = ai_player

    def execute_hunt_strategy(self, game):
        """Exécute la stratégie de chasse: poursuivre un joueur actif avec une approche plus agressive"""
        target = self.ai.find_target_player(game)
        if not target:
            # Pas de cible, passer en mode exploration/collection
            self.execute_collect_strategy(game)
            return

        # Vérifier si on peut attaquer directement (alignement)
        can_attack = False

        # Si le joueur est aligné et à portée
        if (target.grid_x == self.ai.grid_x or target.grid_y == self.ai.grid_y):
            distance = abs(target.grid_x - self.ai.grid_x) + abs(target.grid_y - self.ai.grid_y)

            # Vérifier s'il est à portée d'explosion
            if distance <= self.ai.bomb_power + 1:  # +1 pour être plus agressif
                # Vérifier s'il n'y a pas d'obstacles
                if self.ai.has_clear_line_of_sight(self.ai.grid_x, self.ai.grid_y, target.grid_x, target.grid_y, game):
                    can_attack = True

                    # MODIFICATION: Moins de vérifications, plus de bombes
                    if self.ai.bomb_cooldown <= 0:
                        # MODIFICATION: Parfois prendre des risques pour éliminer un joueur
                        if self.ai.is_safe_to_place_bomb(game) or random.random() < self.ai.aggression_level * 0.3:
                            self.ai.place_bomb(game)

                        # Direction pour s'éloigner de la bombe après l'avoir posée
                        dx = -1 if target.grid_x > self.ai.grid_x else 1 if target.grid_x < self.ai.grid_x else 0
                        dy = -1 if target.grid_y > self.ai.grid_y else 1 if target.grid_y < self.ai.grid_y else 0

                        # S'assurer qu'on ne va pas vers un mur
                        escape_x, escape_y = self.ai.grid_x + dx, self.ai.grid_y + dy
                        if self.ai.can_move_to(escape_x, escape_y, game):
                            self.ai.current_direction = (dx, dy)
                            return

        # Si on ne peut pas attaquer directement ou on vient juste de poser une bombe,
        # essayer de se positionner stratégiquement
        if not can_attack or self.ai.bomb_cooldown > 0:
            # Trouver un chemin vers la cible ou une position stratégique
            # Déterminer les positions d'embuscade possibles
            ambush_positions = []

            # Positions adjacentes à la cible (pour se positionner et attendre)
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                ax, ay = target.grid_x + dx, target.grid_y + dy
                if 0 <= ax < GRID_WIDTH and 0 <= ay < GRID_HEIGHT:
                    if game.grid[ay][ax] == TileType.EMPTY:
                        # Calculer un score pour cette position d'embuscade
                        score = 0

                        # Favoriser les positions qui nous permettent de nous aligner avec la cible
                        if ax == target.grid_x or ay == target.grid_y:
                            score += 20

                        # Vérifier si cette position est sûre
                        danger = self.ai.calculate_danger_level(ax, ay, game)
                        score -= danger * 5

                        ambush_positions.append((score, (ax, ay)))

            if ambush_positions:
                # Trier par score décroissant
                ambush_positions.sort(reverse=True)

                # Choisir la meilleure position d'embuscade
                best_ambush = ambush_positions[0][1]

                # Trouver un chemin vers cette position
                path = self.ai.find_path_to_target(best_ambush[0], best_ambush[1], game)
                if path and len(path) > 1:
                    next_x, next_y = path[1]
                    dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                    dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                    self.ai.current_direction = (dx, dy)
                    return

            # Si aucune position d'embuscade n'est accessible, aller directement vers la cible
            path = self.ai.find_path_to_target(target.grid_x, target.grid_y, game)
            if path and len(path) > 1:
                next_x, next_y = path[1]
                dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                self.ai.current_direction = (dx, dy)
            else:
                # Pas de chemin, approche directe ou changement de stratégie
                if random.random() < 0.7:  # 70% de chance de continuer à chasser
                    dx = 1 if target.grid_x > self.ai.grid_x else -1 if target.grid_x < self.ai.grid_x else 0
                    dy = 1 if target.grid_y > self.ai.grid_y else -1 if target.grid_y < self.ai.grid_y else 0

                    # Si les deux axes sont non-nuls, en choisir un
                    if dx != 0 and dy != 0:
                        if abs(target.grid_x - self.ai.grid_x) > abs(target.grid_y - self.ai.grid_y):
                            dy = 0  # Prioriser l'axe horizontal
                        else:
                            dx = 0  # Prioriser l'axe vertical

                    self.ai.current_direction = (dx, dy)
                else:
                    # Changer temporairement de stratégie
                    self.execute_collect_strategy(game)

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

        # Analyser le comportement du joueur cible
        # Identifier les passages étroits, les culs-de-sac, etc.
        trap_opportunities = []

        # Stratégie 1: Trouver un passage étroit où le joueur doit passer
        narrow_passages = []

        # Chercher dans un rayon autour du joueur cible
        search_radius = 6
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                px, py = target.grid_x + dx, target.grid_y + dy

                if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                    # Vérifier si c'est un passage étroit (1 case de large)
                    if game.grid[py][px] == TileType.EMPTY:
                        # Compter les obstacles autour
                        obstacles = 0
                        for ndx, ndy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                            nx, ny = px + ndx, py + ndy
                            if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT) or \
                                    game.grid[ny][nx] in [TileType.WALL, TileType.BLOCK]:
                                obstacles += 1

                        # Si c'est un passage étroit (2 ou 3 obstacles autour)
                        if obstacles >= 2:
                            narrow_passages.append((px, py))

        # Stratégie 2: Anticiper le mouvement du joueur
        # Essayer de prédire où le joueur va aller
        predicted_positions = []

        # Direction actuelle du joueur (si disponible)
        player_dx, player_dy = 0, 0
        if hasattr(target, 'current_direction'):
            player_dx, player_dy = target.current_direction

        # Si on ne connaît pas la direction, essayer de l'estimer
        if player_dx == 0 and player_dy == 0 and hasattr(target, 'x') and hasattr(target, 'y'):
            # Estimer en fonction du décalage dans la case
            cell_offset_x = target.x % TILE_SIZE - TILE_SIZE // 2
            cell_offset_y = target.y % TILE_SIZE - TILE_SIZE // 2

            if abs(cell_offset_x) > abs(cell_offset_y):
                player_dx = 1 if cell_offset_x > 0 else -1 if cell_offset_x < 0 else 0
            else:
                player_dy = 1 if cell_offset_y > 0 else -1 if cell_offset_y < 0 else 0

        # Prédire les positions futures du joueur
        for i in range(1, 4):  # Anticiper jusqu'à 3 cases devant
            px, py = target.grid_x + player_dx * i, target.grid_y + player_dy * i
            if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                if game.grid[py][px] == TileType.EMPTY:
                    predicted_positions.append((px, py))
                else:
                    break  # S'arrêter si on rencontre un obstacle

        # Stratégie 3: Bloquer des issues
        # Identifier les cases adjacentes au joueur
        adjacent_positions = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            px, py = target.grid_x + dx, target.grid_y + dy
            if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                if game.grid[py][px] == TileType.EMPTY:
                    adjacent_positions.append((px, py))

        # Combiner toutes les opportunités de piège avec des scores
        for px, py in narrow_passages:
            score = 60
            dist = abs(px - self.ai.grid_x) + abs(py - self.ai.grid_y)
            if dist <= 5:  # Si on est assez proche
                trap_opportunities.append((score, "narrow", (px, py)))

        for px, py in predicted_positions:
            score = 70 - 10 * (abs(px - target.grid_x) + abs(py - target.grid_y))  # Plus proche = meilleur
            dist = abs(px - self.ai.grid_x) + abs(py - self.ai.grid_y)
            if dist <= 6:  # Si on peut y arriver rapidement
                trap_opportunities.append((score, "predict", (px, py)))

        for px, py in adjacent_positions:
            score = 50
            # Bonus si c'est la seule issue
            if len(adjacent_positions) <= 2:
                score += 30

            trap_opportunities.append((score, "block", (px, py)))

        # Trier les opportunités par score décroissant
        trap_opportunities.sort(reverse=True)

        # Essayer d'exécuter le meilleur piège
        if trap_opportunities:
            score, strategy_type, pos = trap_opportunities[0]
            px, py = pos

            # Trouver un chemin vers cette position
            path = self.ai.find_path_to_position(px, py, game)
            if path and len(path) > 1:
                next_x, next_y = path[1]
                dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                self.ai.current_direction = (dx, dy)

                # Si on est déjà à la position cible, poser une bombe
                if self.ai.grid_x == px and self.ai.grid_y == py:
                    # MODIFICATION: Plus de chances de poser une bombe
                    if self.ai.is_safe_to_place_bomb(game) or random.random() < self.ai.aggression_level * 0.4:
                        self.ai.place_bomb(game)
                        self.ai.trap_cooldown = max(10, 20 - int(
                            self.ai.aggression_level * 10))  # Réduit pour les IA agressives

                return

        # Si aucune opportunité de piège n'est viable, revenir à la chasse
        self.execute_hunt_strategy(game)

    def execute_collect_strategy(self, game):
        """Exécute la stratégie de collection: aller chercher des power-ups avec une meilleure priorisation"""
        # Vérifier s'il y a des power-ups connus
        known_targets = []

        # 1. Les power-ups connus
        if self.ai.known_powerups:
            for px, py in self.ai.known_powerups:
                # Vérifier si le power-up existe toujours
                if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                    tile_type = game.grid[py][px]
                    if tile_type in [TileType.POWER_UP_BOMB, TileType.POWER_UP_FLAME, TileType.POWER_UP_SPEED]:
                        # Calculer un score pour ce power-up
                        score = 0

                        # Distance (plus proche = meilleur)
                        distance = abs(px - self.ai.grid_x) + abs(py - self.ai.grid_y)
                        score += 100 - distance * 10

                        # Bonus pour le type préféré
                        if (tile_type == TileType.POWER_UP_BOMB and self.ai.powerup_priority == "bomb") or \
                                (tile_type == TileType.POWER_UP_FLAME and self.ai.powerup_priority == "flame") or \
                                (tile_type == TileType.POWER_UP_SPEED and self.ai.powerup_priority == "speed"):
                            score += 40

                        # Bonus pour les types dont on a le plus besoin
                        if self.ai.max_bombs < 2 and tile_type == TileType.POWER_UP_BOMB:
                            score += 50
                        elif self.ai.bomb_power < 3 and tile_type == TileType.POWER_UP_FLAME:
                            score += 40
                        elif self.ai.speed < 4 and tile_type == TileType.POWER_UP_SPEED:
                            score += 30

                        # Pénalité si le chemin est dangereux
                        path = self.ai.find_path_to_position(px, py, game)
                        if not path:
                            score -= 80  # Forte pénalité si pas de chemin
                        elif len(path) > 1:
                            next_x, next_y = path[1]
                            danger = self.ai.calculate_danger_level(next_x, next_y, game)
                            score -= danger * 8

                        known_targets.append((score, "powerup", (px, py)))

        # 2. Les blocs destructibles (pour trouver des power-ups)
        blocks_to_destroy = []

        # Rechercher des blocs à proximité
        search_radius = 5
        for dx in range(-search_radius, search_radius + 1):
            for dy in range(-search_radius, search_radius + 1):
                bx, by = self.ai.grid_x + dx, self.ai.grid_y + dy
                if 0 <= bx < GRID_WIDTH and 0 <= by < GRID_HEIGHT:
                    if game.grid[by][bx] == TileType.BLOCK:
                        # Chercher une position adjacente au bloc
                        for adj_dx, adj_dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                            ax, ay = bx + adj_dx, by + adj_dy
                            if 0 <= ax < GRID_WIDTH and 0 <= ay < GRID_HEIGHT:
                                if game.grid[ay][ax] == TileType.EMPTY:
                                    # Calculer un score pour ce bloc
                                    score = 0

                                    # Distance à la position adjacente (plus proche = meilleur)
                                    distance = abs(ax - self.ai.grid_x) + abs(ay - self.ai.grid_y)
                                    score += 80 - distance * 8

                                    # Bonus s'il y a plusieurs blocs adjacents
                                    blocks_around = 0
                                    for check_dx, check_dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                                        check_x, check_y = ax + check_dx, ay + check_dy
                                        if 0 <= check_x < GRID_WIDTH and 0 <= check_y < GRID_HEIGHT:
                                            if game.grid[check_y][check_x] == TileType.BLOCK:
                                                blocks_around += 1

                                    score += blocks_around * 10

                                    # Vérifier si on peut y accéder
                                    path = self.ai.find_path_to_position(ax, ay, game)
                                    if not path:
                                        score -= 60
                                    elif len(path) > 1:
                                        next_x, next_y = path[1]
                                        danger = self.ai.calculate_danger_level(next_x, next_y, game)
                                        score -= danger * 6

                                    blocks_to_destroy.append((score, "block", (ax, ay)))

        # Combiner et trier les cibles potentielles
        all_targets = known_targets + blocks_to_destroy

        if all_targets:
            all_targets.sort(reverse=True)
            best_score, target_type, pos = all_targets[0]

            if best_score > 0:  # S'assurer que c'est une cible viable
                tx, ty = pos

                # Pour les powerups, simplement aller vers eux
                if target_type == "powerup":
                    path = self.ai.find_path_to_position(tx, ty, game)
                    if path and len(path) > 1:
                        next_x, next_y = path[1]
                        dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                        dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                        self.ai.current_direction = (dx, dy)
                        return

                # Pour les blocs, aller à la position adjacente et poser une bombe
                elif target_type == "block":
                    path = self.ai.find_path_to_position(tx, ty, game)
                    if path and len(path) > 1:
                        next_x, next_y = path[1]
                        dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                        dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                        self.ai.current_direction = (dx, dy)

                        # Si on est déjà adjacent au bloc, poser une bombe
                        if self.ai.grid_x == tx and self.ai.grid_y == ty:
                            # MODIFICATION: Moins strict sur la sécurité pour débloquer des bonus
                            if self.ai.is_safe_to_place_bomb(
                                    game) or random.random() < 0.3 + self.ai.risk_tolerance * 0.2:
                                self.ai.place_bomb(game)
                                # Si pas sûr, fuir immédiatement
                                if not self.ai.is_safe_to_place_bomb(game):
                                    for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                                        nx, ny = self.ai.grid_x + dx, self.ai.grid_y + dy
                                        if self.ai.can_move_to(nx, ny, game):
                                            danger = self.ai.calculate_danger_level(nx, ny, game)
                                            if danger < 5:  # Chercher une direction relativement sûre
                                                self.ai.current_direction = (dx, dy)
                                                break
                        return

        # Si aucune cible intéressante n'a été trouvée, explorer aléatoirement
        # mais de manière plus intelligente

        # Chercher des zones inexplorées
        unexplored_areas = []
        explored_positions = set(self.ai.map_knowledge.keys())

        # Générer des positions potentielles dans un rayon moyen
        for distance in range(3, 8):
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    if abs(dx) + abs(dy) == distance:  # Exactement à cette distance de Manhattan
                        ex, ey = self.ai.grid_x + dx, self.ai.grid_y + dy

                        if 0 <= ex < GRID_WIDTH and 0 <= ey < GRID_HEIGHT:
                            # Si cette position n'a pas encore été explorée
                            if (ex, ey) not in explored_positions:
                                # Calculer un score d'exploration
                                score = 60 - distance * 5  # Plus proche = meilleur

                                # Vérifier si on peut y accéder
                                path = self.ai.find_path_to_position(ex, ey, game)
                                if path:
                                    unexplored_areas.append((score, (ex, ey)))

        if unexplored_areas:
            # Trier par score décroissant
            unexplored_areas.sort(reverse=True)

            # Choisir une destination avec un peu d'aléatoire
            # (pour éviter que toutes les IA aillent au même endroit)
            top_n = min(3, len(unexplored_areas))
            selected_index = random.randint(0, top_n - 1)
            score, (ex, ey) = unexplored_areas[selected_index]

            # Trouver un chemin vers cette zone
            path = self.ai.find_path_to_position(ex, ey, game)
            if path and len(path) > 1:
                next_x, next_y = path[1]
                dx = 1 if next_x > self.ai.grid_x else -1 if next_x < self.ai.grid_x else 0
                dy = 1 if next_y > self.ai.grid_y else -1 if next_y < self.ai.grid_y else 0
                self.ai.current_direction = (dx, dy)
                return

        # Si rien d'autre ne fonctionne, se déplacer aléatoirement mais de manière sécurisée
        # Évaluer toutes les directions possibles
        safe_directions = []

        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = self.ai.grid_x + dx, self.ai.grid_y + dy
            if self.ai.can_move_to(nx, ny, game):
                # Calculer le niveau de danger
                danger = self.ai.calculate_danger_level(nx, ny, game)
                safe_directions.append((danger, (dx, dy)))

        if safe_directions:
            # Trier par niveau de danger croissant
            safe_directions.sort()

            # Choisir parmi les directions les plus sûres avec un peu d'aléatoire
            top_n = min(2, len(safe_directions))
            selected_index = random.randint(0, top_n - 1)
            self.ai.current_direction = safe_directions[selected_index][1]

    def execute_escape_strategy(self, game):
        """Exécute la stratégie d'échappement: fuir le danger avec une meilleure détection des blocages en angle"""
        # NOUVEAU: Vérifier d'abord si on est coincé dans un angle
        is_cornered = False

        # Compter les obstacles adjacents
        obstacles_adjacent = 0
        bomb_adjacent = False

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = self.ai.grid_x + dx, self.ai.grid_y + dy
            if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                if game.grid[ny][nx] in [TileType.WALL, TileType.BLOCK]:
                    obstacles_adjacent += 1
                elif game.grid[ny][nx] == TileType.BOMB:
                    obstacles_adjacent += 1
                    bomb_adjacent = True

        # Si on a beaucoup d'obstacles autour et qu'on est près d'une bombe,
        # on est probablement coincé dans un angle
        on_bomb = game.grid[self.ai.grid_y][self.ai.grid_x] == TileType.BOMB
        if (obstacles_adjacent >= 2 and (on_bomb or bomb_adjacent)) or obstacles_adjacent >= 3:
            is_cornered = True

        # Si on est coincé dans un angle, priorité absolue à trouver une sortie
        if is_cornered:
            # Chercher toutes les sorties possibles, même dangereuses
            escape_options = []
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = self.ai.grid_x + dx, self.ai.grid_y + dy
                if self.ai.can_move_to(nx, ny, game):
                    # Évaluer la sécurité de cette option
                    danger = self.ai.calculate_danger_level(nx, ny, game)

                    # Pénalité pour aller vers une bombe, sauf si c'est la seule option
                    if game.grid[ny][nx] == TileType.BOMB:
                        danger += 5

                    escape_options.append((danger, (dx, dy)))

            if escape_options:
                # Prendre l'option la moins dangereuse
                escape_options.sort()
                self.ai.current_direction = escape_options[0][1]
                return True

        # Si on n'est pas dans un angle ou si aucune sortie n'a été trouvée,
        # procéder avec la stratégie d'échappement normale

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

        # Si aucun chemin sûr n'est trouvé, trier les directions par niveau de danger
        escape_directions = []

        for direction in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            test_x = self.ai.grid_x + direction[0]
            test_y = self.ai.grid_y + direction[1]

            if self.ai.can_move_to(test_x, test_y, game):
                # MODIFICATION: Pénaliser moins les directions avec des bombes en cas d'urgence
                # (parfois il faut traverser une bombe pour s'échapper d'un angle)
                bomb_penalty = 0
                if game.grid[test_y][test_x] == TileType.BOMB:
                    bomb_penalty = 30  # Réduit de 50 à 30 pour permettre le passage en cas d'urgence

                # Calculer un score d'évacuation
                escape_score = 0 - bomb_penalty

                # Niveau de danger (plus faible = meilleur)
                danger = self.ai.calculate_danger_level(test_x, test_y, game)
                escape_score -= danger * 15  # Réduit de 20 à 15

                # Distance par rapport aux bombes connues (plus loin = meilleur)
                for bomb in game.bombs:
                    distance = abs(test_x - bomb.x) + abs(test_y - bomb.y)
                    escape_score += min(30, distance * 4)

                # Vérifier si cette direction nous emmène dans un cul-de-sac
                is_dead_end = False
                exits = 0
                for ex, ey in [(test_x, test_y + 1), (test_x + 1, test_y), (test_x, test_y - 1), (test_x - 1, test_y)]:
                    if 0 <= ex < GRID_WIDTH and 0 <= ey < GRID_HEIGHT:
                        if game.grid[ey][ex] == TileType.EMPTY:
                            exits += 1

                # Pénaliser les culs-de-sac (mais moins si on est vraiment coincé)
                if exits <= 1:  # Seulement l'entrée
                    escape_score -= 40  # Réduit de 50 à 40

                # S'il y a une dernière position sûre connue, favoriser cette direction
                if self.ai.last_safe_position:
                    safe_x, safe_y = self.ai.last_safe_position
                    if direction[0] == 1 and self.ai.grid_x < safe_x:
                        escape_score += 30
                    elif direction[0] == -1 and self.ai.grid_x > safe_x:
                        escape_score += 30
                    elif direction[1] == 1 and self.ai.grid_y < safe_y:
                        escape_score += 30
                    elif direction[1] == -1 and self.ai.grid_y > safe_y:
                        escape_score += 30

                escape_directions.append((escape_score, direction))

        if escape_directions:
            # Trier par score décroissant
            escape_directions.sort(reverse=True)
            self.ai.current_direction = escape_directions[0][1]
            return True

        # Si vraiment aucune solution n'est trouvée, tenter un mouvement désespéré
        # vers n'importe quelle direction possible
        possible_moves = []

        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = self.ai.grid_x + dx, self.ai.grid_y + dy
            if self.ai.can_move_to(nx, ny, game):
                possible_moves.append((dx, dy))

        if possible_moves:
            self.ai.current_direction = random.choice(possible_moves)
            return True

        return False  # Pas de chemin trouvé

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