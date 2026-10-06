"""
ai.py - how the bots decide what to do.

Each bot has a Brain. A few times per second the brain looks around and picks
ONE goal, checking these in order (the first one that applies wins):

    1. Low on health?            -> run home to heal
    2. Enemy in range?           -> use abilities on it
    3. Carrying enough energy?   -> walk to an enemy goal and score
    4. Enemy close by?           -> fight it
    5. Energy orbs nearby?       -> pick them up
    6. Otherwise                 -> defeat wild creatures in your lane

This "priority list" style is simple to read and to change: to make bots more
aggressive, move rule 4 above rule 3.
"""
import random

from pygame.math import Vector2 as V

from .entities import Controls
from .settings import MAX_ENERGY, GOAL_RADIUS


class Brain:
    THINK_EVERY = 0.15     # seconds between decisions (people don't react instantly either)

    def __init__(self, lane):
        self.lane = lane
        self.think_timer = random.uniform(0, self.THINK_EVERY)
        self.controls = Controls()
        self.retreating = False
        self.wild_target = None
        self.new_threshold()

    def new_threshold(self):
        """How much energy to collect before going to score (varies so bots differ)."""
        self.threshold = random.randint(14, 32)

    def update(self, unit, game, dt):
        self.think_timer -= dt
        if self.think_timer <= 0:
            self.think_timer = self.THINK_EVERY
            self.controls = self.decide(unit, game)
        return self.controls

    # ------------------------------------------------------------------------
    def decide(self, me, game):
        c = Controls()
        if not me.alive:
            return c
        if me.scoring_goal is not None:
            return c                                   # stand still while scoring

        world = game.world
        foes = [u for u in game.units if u.team != me.team and u.alive and game.can_see(me.team, u)]
        foe = min(foes, key=lambda u: u.pos.distance_to(me.pos), default=None)
        foe_dist = foe.pos.distance_to(me.pos) if foe else 1e9

        def walk_to(target, stop=8.0):
            if me.pos.distance_to(target) > stop:
                step = world.next_step(me.pos, target)
                c.move = step - me.pos

        # 1. retreat when hurt, and stay away until mostly healed
        if me.hp < me.max_hp * 0.3:
            self.retreating = True
        if self.retreating:
            walk_to(me.spawn, stop=40)
            for key in ("q", "e"):              # a dash is a great way to escape
                a = me.ability(key)
                if a and a.escape and foe_dist < 300 and game.ability_ready(me, key):
                    setattr(c, key, True)
                    c.aim = me.pos + c.move if c.move.length_squared() else V(me.spawn)
            if me.hp > me.max_hp * 0.9:
                self.retreating = False
            return c

        # 2. abilities: each move says when it's worth using (see abilities.py)
        for key in ("q", "e"):
            a = me.ability(key)
            if a and game.ability_ready(me, key) and a.bot_wants(game, me, foe, foe_dist):
                setattr(c, key, True)
                if foe is not None:
                    c.aim = foe.pos + foe_lead(foe)

        # 3. go score
        late = game.time_left < 25 and me.energy > 0
        if me.energy >= self.threshold or me.energy >= MAX_ENERGY or late:
            goals = [g for g in world.goals if g.team != me.team and world.goal_is_open(g)]
            if goals:
                goal = min(goals, key=lambda g: g.pos.distance_to(me.pos))
                if goal.pos.distance_to(me.pos) < GOAL_RADIUS * 0.55:
                    c.score = True
                    c.move = V()
                else:
                    walk_to(goal.pos)
                return c

        # 4. fight enemies that come close
        if foe and foe_dist < 330:
            if foe_dist > me.attack_range * 0.85:
                walk_to(foe.pos)
            return c

        # 5. collect loose energy
        if me.energy < MAX_ENERGY:
            orbs = [o for o in game.orbs if o.pos.distance_to(me.pos) < 380]
            if orbs:
                walk_to(min(orbs, key=lambda o: o.pos.distance_to(me.pos)).pos, stop=0)
                return c

        # 6. defeat wild creatures, preferring ones near our lane
        if self.wild_target is None or not self.wild_target.alive:
            self.wild_target = self.pick_wild(me, game)
        w = self.wild_target
        if w is not None:
            q = me.ability("q")
            if q and q.hits_wilds and game.ability_ready(me, "q") \
                    and w.pos.distance_to(me.pos) < q.ai_max and w.hp > 150:
                c.q, c.aim = True, V(w.pos)
            walk_to(w.pos, stop=me.attack_range * 0.7)
        else:
            walk_to(world.lane_anchor[self.lane](me.team), stop=60)
        return c

    def pick_wild(self, me, game):
        anchor = game.world.lane_anchor[self.lane](me.team)
        best, best_score = None, 1e18
        for w in game.wilds:
            if not w.alive:
                continue
            score = w.pos.distance_to(me.pos) + 0.6 * w.pos.distance_to(anchor)
            if w.kind == "moonshine" and me.hp < me.max_hp * 0.7:
                score *= 0.5                       # hurt? healing creatures look tastier
            score *= random.uniform(0.9, 1.1)
            if score < best_score:
                best, best_score = w, score
        return best


def foe_lead(foe):
    """Aim a little ahead of a moving enemy so slow attacks still land."""
    if foe.moving:
        return V(-40 if foe.facing_left else 40, 0)
    return V()
