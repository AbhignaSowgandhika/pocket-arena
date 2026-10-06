"""
Pocket Arena - start the game from here:

    python3 main.py

This file is the "game loop". About 60 times per second it:
    1. reads the keyboard and mouse,
    2. turns them into Controls and hands them to the Game (the rules),
    3. asks the Renderer to draw the new picture,
    4. shows that picture on screen.
"""
import sys

import pygame
from pygame.math import Vector2 as V

from arena import settings as S
from arena.entities import Controls
from arena.game import Game
from arena.render import Renderer
from arena.sprites import SpriteBank, load_all


def read_controls(keys, pressed, renderer):
    """Turn this frame's keyboard and mouse into Controls for your character."""
    move = V(0, 0)
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        move.x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        move.x += 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        move.y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        move.y += 1
    mouse_on_map = V(pygame.mouse.get_pos()) + renderer.camera
    return Controls(move=move, aim=mouse_on_map,
                    q=pygame.K_q in pressed,
                    e=pygame.K_e in pressed,
                    score=pygame.K_SPACE in pressed)


def main():
    pygame.init()
    pygame.display.set_caption(S.TITLE)
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H), pygame.SCALED)
    clock = pygame.time.Clock()

    sprites = load_all()
    game = Game(sprites)
    renderer = Renderer(screen, SpriteBank(sprites))

    while True:
        dt = min(clock.tick(S.FPS) / 1000, 0.05)   # seconds since last frame (capped)

        pressed = set()                            # keys pressed down THIS frame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type != pygame.KEYDOWN:
                continue
            pressed.add(event.key)
            if game.state == "intro":
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    game.state = "playing"
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                    step = 1 if event.key in (pygame.K_RIGHT, pygame.K_d) else -1
                    chars = game.characters
                    game.player_sprite = chars[(chars.index(game.player_sprite) + step) % len(chars)]
                    game.reset()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif game.state == "playing" and event.key == pygame.K_ESCAPE:
                game.state = "paused"
            elif game.state == "paused":
                if event.key == pygame.K_ESCAPE:
                    game.state = "playing"
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
            elif game.state == "over":
                if event.key == pygame.K_r:
                    game.reset()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        controls = read_controls(pygame.key.get_pressed(), pressed, renderer)
        game.update(dt, controls)
        renderer.draw(game, dt)
        pygame.display.flip()


if __name__ == "__main__":
    main()
