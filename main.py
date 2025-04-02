import pygame
import sys
from bomberman import Bomberman


def main():
    # Initialisation de pygame
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    # Écran de sélection du mode de jeu
    two_players = show_game_mode_selection(screen)

    # Créer et lancer le jeu avec le mode sélectionné
    game = Bomberman(screen, two_players)
    game.run()

    # Quitter proprement
    pygame.quit()
    sys.exit()


def show_game_mode_selection(screen):
    """Affiche un écran de sélection du mode de jeu et retourne True pour 2 joueurs, False pour 1 joueur."""
    # Obtenir les dimensions de l'écran
    screen_width, screen_height = screen.get_size()

    # Couleurs
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)

    # Créer une police
    font_large = pygame.font.SysFont('Arial', 48)
    font_medium = pygame.font.SysFont('Arial', 36)

    # Textes
    title_text = font_large.render("BOMBERMAN", True, WHITE)
    option1_text = font_medium.render("1 Joueur (vs 2 IA)", True, WHITE)
    option2_text = font_medium.render("2 Joueurs (vs 1 IA)", True, WHITE)
    instruction_text = font_medium.render("Appuyez sur 1 ou 2 pour sélectionner", True, WHITE)

    # Rectangles pour les options
    option1_rect = pygame.Rect(screen_width // 4, screen_height // 2, screen_width // 2, 50)
    option2_rect = pygame.Rect(screen_width // 4, screen_height // 2 + 100, screen_width // 2, 50)

    # Variable pour la sélection active
    selected = None

    # Boucle principale
    running = True
    while running:
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_1:
                    selected = 1
                    running = False
                elif event.key == pygame.K_2:
                    selected = 2
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if option1_rect.collidepoint(mouse_pos):
                    selected = 1
                    running = False
                elif option2_rect.collidepoint(mouse_pos):
                    selected = 2
                    running = False

        # Vérifier si la souris survole un bouton
        mouse_pos = pygame.mouse.get_pos()
        option1_color = RED if option1_rect.collidepoint(mouse_pos) else WHITE
        option2_color = BLUE if option2_rect.collidepoint(mouse_pos) else WHITE

        option1_text = font_medium.render("1 Joueur (vs 2 IA)", True, option1_color)
        option2_text = font_medium.render("2 Joueurs (vs 1 IA)", True, option2_color)

        # Dessiner l'écran
        screen.fill(BLACK)

        # Dessiner le titre
        title_rect = title_text.get_rect(center=(screen_width // 2, screen_height // 4))
        screen.blit(title_text, title_rect)

        # Dessiner les options
        pygame.draw.rect(screen, option1_color, option1_rect, 2)
        pygame.draw.rect(screen, option2_color, option2_rect, 2)

        option1_text_rect = option1_text.get_rect(center=option1_rect.center)
        option2_text_rect = option2_text.get_rect(center=option2_rect.center)

        screen.blit(option1_text, option1_text_rect)
        screen.blit(option2_text, option2_text_rect)

        # Dessiner les instructions
        instruction_rect = instruction_text.get_rect(center=(screen_width // 2, screen_height * 3 // 4))
        screen.blit(instruction_text, instruction_rect)

        # Mettre à jour l'affichage
        pygame.display.flip()

    # Retourner le choix (True pour 2 joueurs, False pour 1 joueur)
    return selected == 2


if __name__ == "__main__":
    main()