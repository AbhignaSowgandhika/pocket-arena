"""
screenshots.py - runs a real match with no visible window and saves pictures.

GitHub runs this automatically after every change (see .github/workflows),
so we can check the game still starts, plays and draws properly.

    python3 tools/screenshots.py            # saves PNGs into screenshots/
"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")     # no window needed
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pygame                                          # noqa: E402

from arena import settings as S                        # noqa: E402
from arena.ai import Brain                             # noqa: E402
from arena.game import Game                            # noqa: E402
from arena.render import Renderer                      # noqa: E402
from arena.sprites import SpriteBank, load_all         # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")


def main():
    random.seed(3)
    os.makedirs(OUT, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    sprites = load_all()
    game = Game(sprites)
    renderer = Renderer(screen, SpriteBank(sprites))
    dt = 1 / 30

    renderer.draw(game, dt)
    pygame.image.save(screen, os.path.join(OUT, "01_start_screen.png"))

    game.state = "playing"
    pilot = Brain("bottom")
    shots = {3: "02_first_seconds", 45: "03_lane", 120: "04_mid_match", 200: "05_later", 265: "06_final_stretch"}
    frame, saved = 0, set()
    while game.state == "playing":
        game.update(dt, pilot.update(game.player, game, dt))
        renderer.draw(game, dt)
        frame += 1
        elapsed = int(frame * dt)
        if elapsed in shots and elapsed not in saved:
            saved.add(elapsed)
            pygame.image.save(screen, os.path.join(OUT, shots[elapsed] + ".png"))
    renderer.draw(game, dt)
    pygame.image.save(screen, os.path.join(OUT, "07_results.png"))
    game.state = "paused"
    renderer.draw(game, dt)
    pygame.image.save(screen, os.path.join(OUT, "08_paused.png"))
    print("final score", game.scores, "- screenshots saved to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
