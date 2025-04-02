import pygame
from player import Player
from ai_player import AIPlayer
from contantes import *
import random
from explosion import Explosion


class Bomberman:
    def __init__(self, screen, two_players=True):
        # Initialisation de l'affichage
        self.screen = screen
        pygame.display.set_caption("Bomberman")

        # Mode de jeu (True: 2 joueurs + 1 IA, False: 1 joueur + 2 IA)
        self.two_players = two_players

        # Calculer le décalage pour centrer le jeu sur l'écran
        self.offset_x = (SCREEN_WIDTH - WIDTH) // 2
        self.offset_y = (SCREEN_HEIGHT - HEIGHT) // 2

        # Initialisation des ressources
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', int(TILE_SIZE * 0.6))
        self.load_images()

        # Initialisation des éléments du jeu
        self.grid = self.create_grid()
        self.bombs = []
        self.explosions = []

        # Création des joueurs selon le mode de jeu
        self.create_players()

        # Liste combinée de toutes les entités pour simplifier le code
        self.all_entities = self.players + self.ai_players

        # État du jeu
        self.running = True
        self.game_over = False
        self.game_time = 0  # Temps de jeu en frames
        self.target_update_timer = 0  # Timer pour mettre à jour les cibles des IA

    def create_players(self):
        # Liste pour stocker tous les participants (joueurs et IA)
        self.players = []
        self.ai_players = []

        # Créer les joueurs humains
        if self.two_players:
            # Mode 2 joueurs: Joueur 1 (Rouge) et Joueur 2 (Bleu)
            self.players = [
                Player(1, 1, RED, pygame.K_z, pygame.K_s, pygame.K_q, pygame.K_d, pygame.K_e),
                Player(GRID_WIDTH - 2, GRID_HEIGHT - 2, BLUE, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                       pygame.K_SPACE)
            ]
            # Ajouter 1 IA (Violet)
            ai = AIPlayer(GRID_WIDTH // 2, GRID_HEIGHT // 2, PURPLE)
            self.ai_players.append(ai)
        else:
            # Mode 1 joueur: Seulement Joueur 1 (Rouge)
            self.players = [
                Player(1, 1, RED, pygame.K_z, pygame.K_s, pygame.K_q, pygame.K_d, pygame.K_e)
            ]
            # Ajouter 2 IA (Bleu et Violet)
            ai1 = AIPlayer(GRID_WIDTH - 2, 1, BLUE, self.players[0])  # AI 1 cible le joueur
            ai2 = AIPlayer(1, GRID_HEIGHT - 2, PURPLE, self.players[0])  # AI 2 cible aussi le joueur
            self.ai_players.extend([ai1, ai2])

    def load_images(self):
        # Créer un dictionnaire pour stocker les images
        self.images = {}

        try:
            # Charger l'image du mur indestructible
            wall_img = pygame.image.load(f"{IMAGE_PATH}wall.png").convert_alpha()
            self.images['wall'] = pygame.transform.scale(wall_img, (TILE_SIZE, TILE_SIZE))

            # Charger l'image du bloc destructible
            block_img = pygame.image.load(f"{IMAGE_PATH}block.png").convert_alpha()
            self.images['block'] = pygame.transform.scale(block_img, (TILE_SIZE, TILE_SIZE))

            # Charger l'image du sol (pelouse)
            grass_img = pygame.image.load(f"{IMAGE_PATH}grass.png").convert_alpha()
            self.images['grass'] = pygame.transform.scale(grass_img, (TILE_SIZE, TILE_SIZE))

            print("Images chargées avec succès!")

        except pygame.error as e:
            print(f"Erreur lors du chargement des images: {e}")
            print("Utilisation des formes par défaut.")
            self.images = None

    def create_grid(self):
        # Crée la grille initiale du jeu
        grid = [[TileType.EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

        # Ajoute les murs fixes (non destructibles)
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                # Bords de la grille
                if x == 0 or y == 0 or x == GRID_WIDTH - 1 or y == GRID_HEIGHT - 1:
                    grid[y][x] = TileType.WALL
                # Murs intérieurs (motif classique de Bomberman)
                elif x % 2 == 0 and y % 2 == 0:
                    grid[y][x] = TileType.WALL

        # Ajoute des blocs destructibles aléatoirement
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                if grid[y][x] == TileType.EMPTY:
                    # Laisse des espaces libres pour les joueurs dans les coins
                    if (x <= 2 and y <= 2) or (x >= GRID_WIDTH - 3 and y >= GRID_HEIGHT - 3):
                        continue
                    # 40% de chance d'ajouter un bloc destructible
                    if random.random() < 0.4:
                        grid[y][x] = TileType.BLOCK

        return grid

    # ----------------------------------------
    # MÉTHODES PRINCIPALES DU JEU
    # ----------------------------------------
    def run(self):
        # Boucle principale du jeu
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()

    def handle_events(self):
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_r:
                    # Réinitialiser avec le même mode de jeu
                    self.__init__(self.screen, self.two_players)

        # Prise en compte des entrées des joueurs
        if not self.game_over:
            keys = pygame.key.get_pressed()
            for player in self.players:
                if player.alive:
                    player.handle_input(keys, self)

    def update(self):
        if self.game_over:
            return

        # Incrémenter le temps de jeu
        self.game_time += 1

        # Mise à jour des cibles des IA périodiquement
        self.target_update_timer += 1
        if self.target_update_timer >= FPS * 2:  # Toutes les 2 secondes
            self.update_ai_targets()
            self.target_update_timer = 0

        # Mise à jour de toutes les entités (joueurs et IA)
        for entity in self.all_entities:
            if entity.alive:
                # Pour les joueurs humains
                if entity in self.players:
                    entity.update(self)
                # Pour les IA
                else:
                    entity.update(self)

                # Augmenter le temps de survie pour les entités en vie
                entity.survival_time += 1

                # Attribuer des points de survie (1 point par seconde)
                if self.game_time % FPS == 0:  # Toutes les secondes
                    entity.score += 1

        # Mise à jour des bombes
        self.update_bombs()

        # Mise à jour des explosions
        self.update_explosions()

    def update_ai_targets(self):
        """Met à jour les cibles des IA pour qu'elles attaquent les joueurs humains."""
        # S'assurer que les IA ciblent les joueurs humains vivants
        living_players = [p for p in self.players if p.alive]

        if not living_players:
            return  # Pas de joueurs humains vivants à cibler

        for ai in self.ai_players:
            if ai.alive:
                # Choisir un joueur vivant aléatoirement comme cible
                ai.target_player = random.choice(living_players)

    # ----------------------------------------
    # MÉTHODES DE GESTION DES BOMBES ET EXPLOSIONS
    # ----------------------------------------
    def update_bombs(self):
        # Mise à jour des bombes et détection des explosions
        for bomb in self.bombs[:]:
            bomb.update()  # Ajout de l'appel à update pour gérer la propriété just_placed
            bomb.timer -= 1
            if bomb.timer <= 0:
                self.explode_bomb(bomb)
                self.bombs.remove(bomb)

    def explode_bomb(self, bomb):
        x, y = bomb.x, bomb.y

        # Retirer la bombe de la grille
        if self.grid[y][x] == TileType.BOMB:
            self.grid[y][x] = TileType.EMPTY

        # Décrémenter le compteur de bombes actives du joueur
        if bomb.owner:
            bomb.owner.active_bombs -= 1

        # Créer une explosion au centre
        self.add_explosion(x, y, 2.0)  # La durée est en secondes

        # Propager l'explosion dans les 4 directions
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:  # Haut, Droite, Bas, Gauche
            for i in range(1, bomb.power + 1):
                nx, ny = x + dx * i, y + dy * i

                # Vérifier si la position est dans la grille
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    tile_type = self.grid[ny][nx]

                    if tile_type == TileType.WALL:
                        # L'explosion est bloquée par un mur fixe
                        break
                    elif tile_type == TileType.BLOCK:
                        # Le bloc est détruit
                        self.grid[ny][nx] = TileType.EMPTY

                        # Attribuer des points au propriétaire de la bombe pour avoir détruit un bloc
                        if bomb.owner:
                            bomb.owner.blocks_destroyed += 1
                            bomb.owner.score += 100  # 100 points par bloc détruit

                        # Chance de spawner un power-up
                        if random.random() < 0.3:
                            # Choisir aléatoirement un type de power-up
                            power_up_type = random.choice([
                                TileType.POWER_UP_BOMB,
                                TileType.POWER_UP_FLAME,
                                TileType.POWER_UP_SPEED
                            ])
                            self.grid[ny][nx] = power_up_type

                        # L'explosion est bloquée après avoir détruit un bloc
                        self.add_explosion(nx, ny, 2.0)
                        break
                    elif tile_type == TileType.BOMB:
                        # Déclencher une réaction en chaîne
                        for other_bomb in self.bombs[:]:
                            if other_bomb.x == nx and other_bomb.y == ny:
                                self.explode_bomb(other_bomb)
                                if other_bomb in self.bombs:
                                    self.bombs.remove(other_bomb)
                                break

                    # Ajouter une explosion à cette position
                    self.add_explosion(nx, ny, 2.0)

    def add_explosion(self, x, y, duration):
        # Ajouter une explosion à la liste
        self.explosions.append(Explosion(x, y, duration))

        # Vérifier si des entités (joueurs ou IA) sont touchées par l'explosion
        for entity in self.all_entities:
            if entity.alive and entity.grid_x == x and entity.grid_y == y:
                entity.alive = False

                # Trouver quel joueur/IA a posé la bombe qui a tué cette entité
                killer_found = False
                for bomb in self.bombs:
                    if bomb.owner and bomb.owner != entity:  # Ne pas attribuer de points pour suicide
                        # Points pour avoir éliminé un adversaire
                        bomb.owner.score += 5000  # Bonus important pour avoir éliminé un adversaire
                        killer_found = True
                        break

    def update_explosions(self):
        # Mise à jour des explosions et suppression de celles qui sont terminées
        for explosion in self.explosions[:]:
            explosion.update()
            if explosion.is_finished():
                self.explosions.remove(explosion)

        # Vérifier si la partie doit se terminer
        human_alive = sum(1 for p in self.players if p.alive)
        ai_alive = sum(1 for p in self.ai_players if p.alive)

        # Conditions de fin de partie
        if human_alive == 0:
            # Tous les joueurs humains sont morts
            self.game_over = True
        elif self.two_players and human_alive + ai_alive <= 1:
            # Mode 2 joueurs: un seul participant reste
            self.game_over = True
        elif not self.two_players and human_alive == 1 and ai_alive == 0:
            # Mode 1 joueur: le joueur est vivant et toutes les IA sont mortes
            self.game_over = True

    # ----------------------------------------
    # MÉTHODES D'AFFICHAGE
    # ----------------------------------------
    def draw(self):
        # Effacer l'écran
        self.screen.fill(BLACK)

        # Dessiner la grille
        self.draw_grid()

        # Dessiner les bombes
        for bomb in self.bombs:
            bomb.draw(self.screen, self.offset_x, self.offset_y)

        # Dessiner les explosions
        for explosion in self.explosions:
            explosion.draw(self.screen, self.offset_x, self.offset_y)

        # Dessiner toutes les entités (joueurs et IA)
        for entity in self.all_entities:
            if entity.alive:
                entity.draw(self.screen, self.offset_x, self.offset_y)

        # Afficher l'interface utilisateur
        self.draw_ui()

        # Mise à jour de l'affichage
        pygame.display.flip()

    def draw_grid(self):
        # Dessiner la grille de jeu
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = pygame.Rect(
                    self.offset_x + x * TILE_SIZE,
                    self.offset_y + y * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE
                )

                if self.grid[y][x] == TileType.EMPTY:
                    # Utiliser l'image d'herbe si disponible
                    if self.images and 'grass' in self.images:
                        self.screen.blit(self.images['grass'], rect)
                    else:
                        # Fallback: dessiner un rectangle vert
                        pygame.draw.rect(self.screen, GREEN, rect)
                elif self.grid[y][x] == TileType.WALL:
                    # Utiliser l'image du mur si elle est disponible
                    if self.images and 'wall' in self.images:
                        self.screen.blit(self.images['wall'], rect)
                    else:
                        # Fallback: dessiner un rectangle gris
                        pygame.draw.rect(self.screen, GRAY, rect)
                elif self.grid[y][x] == TileType.BLOCK:
                    # Utiliser l'image du bloc destructible si disponible
                    if self.images and 'block' in self.images:
                        self.screen.blit(self.images['block'], rect)
                    else:
                        # Fallback: dessiner un rectangle marron
                        pygame.draw.rect(self.screen, BROWN, rect)
                elif self.grid[y][x] == TileType.POWER_UP_BOMB:
                    pygame.draw.rect(self.screen, GREEN, rect)
                    pygame.draw.circle(self.screen, ORANGE, rect.center, TILE_SIZE // 3)
                elif self.grid[y][x] == TileType.POWER_UP_FLAME:
                    pygame.draw.rect(self.screen, GREEN, rect)
                    pygame.draw.circle(self.screen, RED, rect.center, TILE_SIZE // 3)
                elif self.grid[y][x] == TileType.POWER_UP_SPEED:
                    pygame.draw.rect(self.screen, GREEN, rect)
                    pygame.draw.circle(self.screen, CYAN, rect.center, TILE_SIZE // 3)

    def draw_ui(self):
        # Afficher le temps de partie en cours
        if not self.game_over:
            time_text = f"Temps: {self.game_time // FPS}s"
            time_surface = self.font.render(time_text, True, WHITE)
            time_rect = time_surface.get_rect(center=(SCREEN_WIDTH // 2, 20))
            self.screen.blit(time_surface, time_rect)

            # Afficher l'information sur les bonus et scores de chaque joueur/IA
            y_offset = 10
            x_left = 10
            x_right = SCREEN_WIDTH - 10

            # Joueur 1 (toujours présent)
            player1_info = f"J1: B:{self.players[0].max_bombs} F:{self.players[0].bomb_power} S:{self.players[0].speed} Score:{self.players[0].score}"
            player1_text = self.font.render(player1_info, True, RED)
            self.screen.blit(player1_text, (x_left, y_offset))

            # En mode 2 joueurs
            if self.two_players:
                # Joueur 2
                player2_info = f"J2: B:{self.players[1].max_bombs} F:{self.players[1].bomb_power} S:{self.players[1].speed} Score:{self.players[1].score}"
                player2_text = self.font.render(player2_info, True, BLUE)
                self.screen.blit(player2_text, (x_right - player2_text.get_width(), y_offset))

                # IA (en violet)
                ai_info = f"IA: B:{self.ai_players[0].max_bombs} F:{self.ai_players[0].bomb_power} S:{self.ai_players[0].speed} Score:{self.ai_players[0].score}"
                ai_text = self.font.render(ai_info, True, PURPLE)
                self.screen.blit(ai_text, (SCREEN_WIDTH // 2 - ai_text.get_width() // 2, y_offset + 30))
            else:
                # Mode 1 joueur: 2 IA (Bleu et Violet)
                ai1_info = f"IA1: B:{self.ai_players[0].max_bombs} F:{self.ai_players[0].bomb_power} S:{self.ai_players[0].speed} Score:{self.ai_players[0].score}"
                ai1_text = self.font.render(ai1_info, True, BLUE)
                self.screen.blit(ai1_text, (x_right - ai1_text.get_width(), y_offset))

                ai2_info = f"IA2: B:{self.ai_players[1].max_bombs} F:{self.ai_players[1].bomb_power} S:{self.ai_players[1].speed} Score:{self.ai_players[1].score}"
                ai2_text = self.font.render(ai2_info, True, PURPLE)
                self.screen.blit(ai2_text, (SCREEN_WIDTH // 2 - ai2_text.get_width() // 2, y_offset + 30))

        # Légende des bonus en bas de l'écran
        legend_font = pygame.font.SysFont('Arial', int(TILE_SIZE * 0.4))
        bomb_legend = legend_font.render("Orange = +1 Bombe", True, ORANGE)
        flame_legend = legend_font.render("Rouge = +1 Puissance", True, RED)
        speed_legend = legend_font.render("Cyan = +1 Vitesse", True, CYAN)

        self.screen.blit(bomb_legend, (10, SCREEN_HEIGHT - 30))
        self.screen.blit(flame_legend, (SCREEN_WIDTH // 2 - flame_legend.get_width() // 2, SCREEN_HEIGHT - 30))
        self.screen.blit(speed_legend, (SCREEN_WIDTH - speed_legend.get_width() - 10, SCREEN_HEIGHT - 30))

        # Afficher l'écran de fin de partie si nécessaire
        if self.game_over:
            self.draw_game_over()

    def draw_game_over(self):
        # Déterminer le vainqueur
        winner_text = "Match nul!"
        winner_type = "none"  # "player" ou "ai"
        winner_index = -1

        all_participants = []

        # Ajouter les joueurs avec leur type
        for i, player in enumerate(self.players):
            all_participants.append({"entity": player, "type": "player", "index": i, "display_index": i + 1})

        # Ajouter les IA avec leur type
        for i, ai in enumerate(self.ai_players):
            all_participants.append({"entity": ai, "type": "ai", "index": i, "display_index": i + 1})

        # Trouver le vainqueur
        for participant in all_participants:
            if participant["entity"].alive:
                if participant["type"] == "player":
                    winner_text = f"Joueur {participant['display_index']} gagne!"
                    winner_type = "player"
                else:
                    winner_text = f"IA {participant['display_index']} gagne!"
                    winner_type = "ai"
                winner_index = participant["index"]
                break

        text_surface = self.font.render(winner_text, True, WHITE)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - TILE_SIZE * 2))

        # Afficher les scores finaux
        scores_text = []

        # Scores des joueurs humains
        for i, player in enumerate(self.players):
            color = RED if i == 0 else BLUE
            stats = f"Joueur {i + 1}: {player.score} points"
            details = f"(Blocs: {player.blocks_destroyed}, Power-ups: {player.powerups_collected}, Temps: {player.survival_time // FPS}s)"
            scores_text.append(self.font.render(stats, True, color))
            scores_text.append(self.font.render(details, True, color))

            # Ajouter une couronne au vainqueur
            if winner_type == "player" and winner_index == i:
                scores_text[len(scores_text) - 2] = self.font.render(f"👑 {stats}", True, color)

        # Scores des IA
        for i, ai in enumerate(self.ai_players):
            color = BLUE if self.two_players == False and i == 0 else PURPLE
            stats = f"IA {i + 1}: {ai.score} points"
            details = f"(Blocs: {ai.blocks_destroyed}, Power-ups: {ai.powerups_collected}, Temps: {ai.survival_time // FPS}s)"
            scores_text.append(self.font.render(stats, True, color))
            scores_text.append(self.font.render(details, True, color))

            # Ajouter une couronne au vainqueur
            if winner_type == "ai" and winner_index == i:
                scores_text[len(scores_text) - 2] = self.font.render(f"👑 {stats}", True, color)

        # Positionner les textes
        score_y = SCREEN_HEIGHT // 2 - TILE_SIZE
        for text in scores_text:
            score_rect = text.get_rect(center=(SCREEN_WIDTH // 2, score_y))
            self.screen.blit(text, score_rect)
            score_y += TILE_SIZE

        restart_text = self.font.render("Appuyez sur R pour recommencer", True, WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, score_y + TILE_SIZE))

        # Texte pour quitter
        quit_text = self.font.render("Appuyez sur Échap pour quitter", True, WHITE)
        quit_rect = quit_text.get_rect(center=(SCREEN_WIDTH // 2, score_y + TILE_SIZE * 2))

        self.screen.blit(text_surface, text_rect)
        self.screen.blit(restart_text, restart_rect)
        self.screen.blit(quit_text, quit_rect)