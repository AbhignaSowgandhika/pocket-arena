"""
test_moves.py - checks that every character's moves hit what they should.

Each test puts an enemy next to you (to the left, right, above or below),
uses a move the way a player does (no mouse aim) and checks the enemy got hurt.
GitHub runs this on every push.

    python3 tools/test_moves.py
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pygame.math import Vector2 as V    # noqa: E402

from arena.entities import Controls      # noqa: E402
from arena.game import Game              # noqa: E402
from arena.sprites import load_all       # noqa: E402

SIDES = {"right": V(1, 0), "left": V(-1, 0), "up": V(0, -1), "down": V(0, 1)}


def setup(sprite_id, side, distance):
    random.seed(1)
    game = Game(load_all(), player_sprite=sprite_id)
    game.state = "playing"
    game.wilds = []                                    # keep the test area empty:
    game.world.walls = []                              # no creatures, walls or bushes
    game.world.bushes = []
    me = game.player
    me.pos = V(1400, 800)
    me.level = 5
    others = [u for u in game.units if u is not me]
    enemy = next(u for u in others if u.team != me.team)
    for u in others:                                   # park everyone else far away
        if u is not enemy:
            u.pos = V(100, 100) if u.team == me.team else V(2700, 100)
            game.brains[u].update = lambda *a, **k: Controls()
    game.brains[enemy].update = lambda *a, **k: Controls()   # the target stands still
    enemy.pos = me.pos + SIDES[side] * distance
    enemy.energy = 20
    me.attack_cd = 999                                 # no basic attacks, moves only
    return game, me, enemy


def run(game, frames=40):
    for _ in range(frames):
        game.update(1 / 30, Controls())


def check(sprite_id, key, side, distance=200):
    game, me, enemy = setup(sprite_id, side, distance)
    hp = enemy.hp
    game.update(1 / 30, Controls(q=key == "q", e=key == "e"))   # press the key once, aim=None
    run(game)
    ok = enemy.hp < hp
    print(f"  {'ok  ' if ok else 'FAIL'} {sprite_id:6s} {key.upper()} at an enemy to the {side:5s}"
          f" -> enemy HP {hp} -> {int(enemy.hp)}")
    return ok


def main():
    failures = 0
    for sprite_id in ("glum", "beat", "potas"):
        for side in SIDES:
            failures += not check(sprite_id, "q", side)
    failures += not check("potas", "e", "right", distance=100)   # Root Guard thorns
    failures += not check("glum", "e", "left", distance=40)      # Gloom Trail puddles
    print("all moves hit" if not failures else f"{failures} test(s) failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
