import pygame
import sys
import random
from enum import Enum

# ----------------------------------------
# INITIALISATION ET CONSTANTES
# ----------------------------------------
# Initialisation de Pygame
pygame.init()

# Définir les chemins des images
IMAGE_PATH = "assets/"  # Dossier où vous stockerez vos images

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)


# Création de la classe Enum pour les types de cases
class TileType(Enum):
    EMPTY = 0
    WALL = 1
    BLOCK = 2
    BOMB = 3
    EXPLOSION = 4
    POWER_UP_BOMB = 5
    POWER_UP_FLAME = 6
    POWER_UP_SPEED = 7


# Constantes du jeu
FPS = 60

# Obtenir les dimensions de l'écran
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# Définir la taille du plateau avec des proportions appropriées
GRID_WIDTH = 21
GRID_HEIGHT = 17

# Calculer la taille des cases pour s'adapter à l'écran
TILE_SIZE_W = SCREEN_WIDTH // GRID_WIDTH
TILE_SIZE_H = SCREEN_HEIGHT // GRID_HEIGHT
TILE_SIZE = min(TILE_SIZE_W, TILE_SIZE_H)  # Prendre la plus petite dimension pour les cases carrées

# Recalculer les dimensions du plateau
WIDTH = TILE_SIZE * GRID_WIDTH
HEIGHT = TILE_SIZE * GRID_HEIGHT


# ----------------------------------------
# CLASSES DES ENTITÉS DU JEU
# ----------------------------------------
# Définition de la classe Player
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
        # Vérifier si la position est dans les limites
        if grid_x < 0 or grid_x >= GRID_WIDTH or grid_y < 0 or grid_y >= GRID_HEIGHT:
            return False

        # Vérifier si la case est libre
        tile_type = game.grid[grid_y][grid_x]
        if tile_type in [TileType.WALL, TileType.BLOCK]:
            return False

        # Vérifier s'il y a une bombe
        if tile_type == TileType.BOMB:
            # On autorise le joueur à marcher sur sa propre bombe qu'il vient de poser
            # mais pas sur les autres bombes
            for bomb in game.bombs:
                if bomb.x == grid_x and bomb.y == grid_y and not bomb.just_placed:
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


# Classe pour les bombes
class Bomb:
    def __init__(self, x, y, power, owner):
        self.x = x
        self.y = y
        self.power = power
        self.owner = owner
        self.timer = FPS * 3  # 3 secondes avant explosion
        self.just_placed = True
        self.radius = TILE_SIZE // 2 - 5

    def update(self):
        # La bombe n'est plus considérée comme "juste posée" après quelques frames
        if self.timer < FPS * 3 - 10:
            self.just_placed = False

    def draw(self, screen, offset_x, offset_y):
        # Dessiner la bombe (un cercle noir avec une mèche qui pulse)
        rect = pygame.Rect(
            offset_x + self.x * TILE_SIZE,
            offset_y + self.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        pulse_factor = (self.timer % 20) / 20  # Effet de pulsation
        size = int(self.radius * (0.8 + 0.2 * pulse_factor))

        pygame.draw.circle(screen, BLACK, rect.center, size)

        # Dessiner la mèche
        fuse_length = int(TILE_SIZE * 0.2 * (self.timer / (FPS * 3)))
        if fuse_length > 0:
            pygame.draw.line(screen, RED,
                             (rect.centerx, rect.centery - size // 2),
                             (rect.centerx, rect.centery - size // 2 - fuse_length),
                             3)


# Classe pour les explosions
class Explosion:
    def __init__(self, x, y, duration):
        self.x = x
        self.y = y
        self.duration = duration * FPS  # Convertir en frames
        self.timer = self.duration
        self.max_radius = TILE_SIZE // 2

    def update(self):
        self.timer -= 1

    def is_finished(self):
        return self.timer <= 0

    def draw(self, screen, offset_x, offset_y):
        # Calculer la taille de l'explosion en fonction du temps restant
        progress = self.timer / self.duration
        radius = int(self.max_radius * progress)

        # Dessiner l'explosion (cercle jaune qui rétrécit)
        rect = pygame.Rect(
            offset_x + self.x * TILE_SIZE,
            offset_y + self.y * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )
        pygame.draw.circle(screen, YELLOW, rect.center, radius)
        pygame.draw.circle(screen, RED, rect.center, radius // 2)


# ----------------------------------------
# CLASSE PRINCIPALE DU JEU
# ----------------------------------------
class Bomberman:
    def __init__(self):
        # Initialisation de l'affichage
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
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
                if event.key == pygame.K_r:
                    self.__init__()  # Redémarrer le jeu

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


# ----------------------------------------
# FONCTION PRINCIPALE
# ----------------------------------------
def main():
    game = Bomberman()
    game.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()