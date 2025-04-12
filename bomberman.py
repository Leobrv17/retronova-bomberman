import pygame
from player import Player
from contantes import *
import random
from explosion import Explosion

class Bomberman:
    def __init__(self, screen):
        # Initialisation de l'affichage
        self.screen=screen
        pygame.display.set_caption("Bomberman")

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
        self.players = [
            Player(1, 1, RED, pygame.K_z, pygame.K_s, pygame.K_q, pygame.K_d, pygame.K_e),
            Player(GRID_WIDTH - 2, GRID_HEIGHT - 2, BLUE, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                   pygame.K_SPACE)
        ]

        # État du jeu
        self.running = True
        self.game_over = False
        self.game_time = 0  # Temps de jeu en frames

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

        # Mise à jour des joueurs
        for player in self.players:
            if player.alive:
                player.update(self)
                # Augmenter le temps de survie pour les joueurs en vie
                player.survival_time += 1

                # Attribuer des points de survie (1 point par seconde)
                if self.game_time % FPS == 0:  # Toutes les secondes
                    player.score += 1

        # Mise à jour des bombes
        self.update_bombs()

        # Mise à jour des explosions
        self.update_explosions()

        # Vérification des conditions de fin de partie
        alive_count = sum(1 for player in self.players if player.alive)
        if alive_count <= 1:
            self.game_over = True

            # Bonus pour le gagnant
            for player in self.players:
                if player.alive:
                    player.score += 10000  # Bonus important pour avoir gagné

    # ----------------------------------------
    # MÉTHODES DE GESTION DES BOMBES ET EXPLOSIONS
    # ----------------------------------------
    def update_bombs(self):
        # Mise à jour des bombes et détection des explosions
        for bomb in self.bombs[:]:
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

        # Vérifier si des joueurs sont touchés par l'explosion
        for player in self.players:
            if player.alive and player.grid_x == x and player.grid_y == y:
                player.alive = False

                # Trouver quel joueur a posé la bombe qui a tué ce joueur
                for bomb in self.bombs:
                    if bomb.owner and bomb.owner != player:  # Ne pas attribuer de points pour suicide
                        # Points pour avoir éliminé un adversaire
                        bomb.owner.score += 5000  # Bonus important pour avoir éliminé un adversaire

    def update_explosions(self):
        # Mise à jour des explosions et suppression de celles qui sont terminées
        for explosion in self.explosions[:]:
            explosion.update()
            if explosion.is_finished():
                self.explosions.remove(explosion)

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

        # Dessiner les joueurs
        for player in self.players:
            if player.alive:
                player.draw(self.screen, self.offset_x, self.offset_y)

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

            # Afficher l'information sur les bonus et scores de chaque joueur
            player1_info = f"J1: B:{self.players[0].max_bombs} F:{self.players[0].bomb_power} S:{self.players[0].speed} Score:{self.players[0].score}"
            player2_info = f"J2: B:{self.players[1].max_bombs} F:{self.players[1].bomb_power} S:{self.players[1].speed} Score:{self.players[1].score}"

            player1_text = self.font.render(player1_info, True, RED)
            player2_text = self.font.render(player2_info, True, BLUE)

            self.screen.blit(player1_text, (10, 10))
            self.screen.blit(player2_text, (SCREEN_WIDTH - player2_text.get_width() - 10, 10))

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
        winner_index = -1
        for i, player in enumerate(self.players):
            if player.alive:
                winner_text = f"Joueur {i + 1} gagne!"
                winner_index = i

        text_surface = self.font.render(winner_text, True, WHITE)
        text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - TILE_SIZE * 2))

        # Afficher les scores finaux
        scores_text = []
        for i, player in enumerate(self.players):
            color = RED if i == 0 else BLUE
            stats = f"Joueur {i + 1}: {player.score} points"
            details = f"(Blocs: {player.blocks_destroyed}, Power-ups: {player.powerups_collected}, Temps: {player.survival_time // FPS}s)"
            scores_text.append(self.font.render(stats, True, color))
            scores_text.append(self.font.render(details, True, color))

            # Ajouter une couronne au vainqueur
            if winner_index == i:
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
