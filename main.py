import pygame
import sys
from bomberman import Bomberman


def main():
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    game = Bomberman(screen)
    game.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()