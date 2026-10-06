"""
simulate.py - play whole matches with no window, as fast as possible.

Every character (including "You") is controlled by the bot AI. Useful for
checking that nothing crashes and that the teams are roughly balanced.

    python3 tools/simulate.py            # 10 matches
    python3 tools/simulate.py 50         # 50 matches
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from arena import settings as S          # noqa: E402
from arena.ai import Brain               # noqa: E402
from arena.game import Game              # noqa: E402
from arena.sprites import load_all       # noqa: E402


def play_match(seed, dt=1 / 30):
    random.seed(seed)
    game = Game(load_all())
    game.state = "playing"
    pilot = Brain("bottom")              # a bot that plays for "You"
    while game.state == "playing":
        game.update(dt, pilot.update(game.player, game, dt))
    return game


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    wins = {S.BLUE: 0, S.RED: 0, None: 0}
    totals = {S.BLUE: 0, S.RED: 0}
    started = time.time()
    for seed in range(n):
        g = play_match(seed)
        wins[g.winner()] += 1
        for t in totals:
            totals[t] += g.scores[t]
        broken = sum(goal.broken for goal in g.world.goals)
        levels = [u.level for u in g.units]
        kos = sum(u.kos for u in g.units)
        print(f"match {seed:3d}: Blue {g.scores[S.BLUE]:4d} - Red {g.scores[S.RED]:4d}"
              f" | goals broken {broken} | KOs {kos:2d} | levels {levels}")
    print(f"\nBlue wins {wins[S.BLUE]}, Red wins {wins[S.RED]}, draws {wins[None]}"
          f" | average score Blue {totals[S.BLUE] / n:.0f}, Red {totals[S.RED] / n:.0f}"
          f" | {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
