"""
entities.py - the things that live on the map.

    Controls   - the "buttons" pressed this frame (by you OR by a bot)
    Unit       - a playable character (you, your allies, the rivals)
    Wild       - a wild creature that drops energy when defeated
    Orb        - loose energy lying on the ground
    Strike     - a thunderbolt that is about to land
    Puddle     - Glum's gloomy residue that slows enemies
    Effect / FloatText - short-lived visuals (sparks, numbers)

These classes only hold data and small helpers. The rules that connect them
live in game.py, and the drawing lives in render.py.
"""
from dataclasses import dataclass, field
from typing import Optional

from pygame.math import Vector2 as V

from .settings import (ROLE_STATS, HP_PER_LEVEL, ATK_PER_LEVEL, MAX_LEVEL,
                       WILD_STATS, xp_to_next)


@dataclass
class Controls:
    """What a player wants to do this frame. The keyboard fills one of these for
    you, and the AI fills one for each bot, so both follow exactly the same rules."""
    move: V = field(default_factory=V)     # direction to walk (length 0 = stand still)
    aim: Optional[V] = None                # point on the map to aim abilities at
    q: bool = False                        # use ability 1
    e: bool = False                        # use ability 2
    score: bool = False                    # start scoring in an enemy goal


class Unit:
    radius = 24

    def __init__(self, name, team, sprite_id, role, kit, spawn, is_player=False):
        self.name = name
        self.team = team
        self.sprite_id = sprite_id
        self.role = role if role in ROLE_STATS else "All-rounder"
        self.base = ROLE_STATS[self.role]
        self.kit = kit                              # list of Ability objects
        self.cooldowns = {a.key: 0.0 for a in kit}
        self.spawn = V(spawn)
        self.pos = V(spawn)
        self.is_player = is_player

        self.level = 1
        self.xp = 0
        self.energy = 0
        self.max_hp = self.atk = 0
        self.recalc()
        self.hp = self.max_hp

        self.attack_cd = 0.0
        self.dead_timer = 0.0
        self.scoring_goal = None
        self.score_progress = 0.0
        self.score_time = 1.0
        self.facing_left = team == 1
        self.moving = False
        self.walk_time = 0.0
        self.flash = 0.0           # >0 right after taking damage
        self.slow_timer = 0.0      # >0 while standing in an enemy puddle
        self.gloom_timer = 0.0     # >0 while Gloom Trail is active
        self.puddle_drop = 0.0
        self.gloom_damage = 0.0    # puddle damage saved up until it's worth showing
        self.reveal_timer = 0.0    # >0 = visible even inside a bush
        self.bush = None           # index of the bush you are standing in
        self.kos = 0
        self.points_scored = 0

    # --- stats ------------------------------------------------------------------
    @property
    def alive(self):
        return self.dead_timer <= 0

    @property
    def speed(self):
        s = self.base["speed"]
        if self.gloom_timer > 0:
            s *= 1.3
        if self.slow_timer > 0:
            s *= 0.55
        return s

    @property
    def attack_range(self):
        return self.base["range"]

    def recalc(self):
        lvl = self.level - 1
        old_max = self.max_hp
        self.max_hp = int(self.base["hp"] * (1 + HP_PER_LEVEL * lvl))
        self.atk = int(self.base["atk"] * (1 + ATK_PER_LEVEL * lvl))
        if old_max:
            self.hp += self.max_hp - old_max   # leveling up also heals the gained HP

    def gain_xp(self, amount):
        """Add XP. Returns how many levels were gained."""
        gained = 0
        if self.level >= MAX_LEVEL:
            return 0
        self.xp += amount
        while self.level < MAX_LEVEL and self.xp >= xp_to_next(self.level):
            self.xp -= xp_to_next(self.level)
            self.level += 1
            self.recalc()
            gained += 1
        if self.level >= MAX_LEVEL:
            self.xp = 0
        return gained

    def ability(self, key):
        for a in self.kit:
            if a.key == key:
                return a
        return None

    def cancel_scoring(self):
        self.scoring_goal = None
        self.score_progress = 0.0


class Wild:
    radius = 26

    def __init__(self, kind, pos):
        self.kind = kind
        self.stats = WILD_STATS[kind]
        self.home = V(pos)
        self.pos = V(pos)
        self.max_hp = self.stats["hp"]
        self.hp = self.max_hp
        self.respawn_timer = 0.0
        self.flash = 0.0
        self.calm_timer = 0.0       # counts down after being hit; heals when it reaches 0
        self.threat = None          # last unit that hit it (it shuffles away from them)
        self.t = 0.0                # animation clock

    @property
    def alive(self):
        return self.respawn_timer <= 0

    @property
    def team(self):
        return None                 # wild creatures belong to nobody


class Orb:
    radius = 10

    def __init__(self, pos, amount):
        self.pos = V(pos)
        self.amount = amount
        self.life = 25.0


class Strike:
    def __init__(self, owner, pos, delay, radius, damage):
        self.owner = owner
        self.pos = V(pos)
        self.delay = delay
        self.timer = delay
        self.radius = radius
        self.damage = damage


class Puddle:
    def __init__(self, owner, pos, life, radius, dps):
        self.owner = owner
        self.team = owner.team
        self.pos = V(pos)
        self.life = life
        self.max_life = life
        self.radius = radius
        self.dps = dps


class Effect:
    """A short visual: kind is 'zap', 'bolt', 'ring' or 'levelup'."""

    def __init__(self, kind, pos, life, **extra):
        self.kind = kind
        self.pos = V(pos)
        self.life = life
        self.max_life = life
        self.extra = extra


class FloatText:
    def __init__(self, pos, text, color, size=22, life=0.9):
        self.pos = V(pos)
        self.text = text
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
