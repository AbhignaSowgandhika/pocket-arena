"""
abilities.py - special moves.

Every ability is a small class with the same shape:
    key        which button uses it ("q" or "e")
    name       shown in the HUD
    cooldown   seconds before it can be used again
    unlock     level needed to use it
    cast(game, unit, aim) -> True if it was used

Bots decide when to use a move by calling `bot_wants(...)`. By default that means
"an enemy is between ai_min and ai_max pixels away", and a move can override it.

To give a character its own moves, write classes here and list them in KITS
at the bottom.
"""
from pygame.math import Vector2 as V

from .entities import Strike, Projectile, Effect


def aim_direction(unit, aim):
    """A length-1 arrow from the unit toward `aim`, or the way it last walked."""
    if aim is not None and (V(aim) - unit.pos).length_squared() > 1:
        return (V(aim) - unit.pos).normalize()
    return V(unit.move_dir)


class Ability:
    key = "q"
    name = "Ability"
    cooldown = 5.0
    unlock = 1
    icon = "spark"
    blurb = ""
    ai_min, ai_max = 0, 300     # bots use it when an enemy is this far away
    hits_wilds = False          # bots may also use it on wild creatures
    escape = False              # bots may use it to run away
    auto_target = True          # with no aim given, aim at the nearest enemy

    def cast(self, game, unit, aim):
        raise NotImplementedError

    def bot_wants(self, game, me, foe, foe_dist):
        return foe is not None and self.ai_min <= foe_dist <= self.ai_max


# ------------------------------------------------------------------- Glum --
class Thunderbolt(Ability):
    """Glum's cloud fires a white thunderbolt at a spot on the ground."""
    key = "q"
    name = "Thunderbolt"
    cooldown = 6.0
    icon = "bolt"
    blurb = "Lightning strikes the nearest enemy's spot after a short delay."
    range = 420
    radius = 90
    delay = 0.45
    ai_max = 460
    hits_wilds = True

    def cast(self, game, unit, aim):
        offset = aim_direction(unit, aim) * 220 if aim is None else V(aim) - unit.pos
        if offset.length() > self.range:          # can't strike further than `range`
            offset.scale_to_length(self.range)
        damage = 80 + 1.4 * unit.atk
        game.strikes.append(Strike(unit, unit.pos + offset, self.delay, self.radius, damage))
        return True


class GloomTrail(Ability):
    """Glum speeds up and leaves sticky purple residue that slows enemies."""
    key = "e"
    name = "Gloom Trail"
    cooldown = 11.0
    unlock = 3
    icon = "gloom"
    blurb = "Move 30% faster and leave purple puddles that slow enemies."
    duration = 3.5
    ai_max = 220

    def cast(self, game, unit, aim):
        unit.gloom_timer = self.duration
        unit.puddle_drop = 0.0
        return True


# ------------------------------------------------------------------- Beat --
class HeartToss(Ability):
    """Beat throws a heart. It breaks on the first thing it hits and drains energy."""
    key = "q"
    name = "Heart Toss"
    cooldown = 5.0
    icon = "heart"
    blurb = "Throw a heart that breaks on hit and steals up to 8 energy."
    speed = 640
    range = 540
    drain = 8
    ai_max = 500
    hits_wilds = True

    def cast(self, game, unit, aim):
        direction = aim_direction(unit, aim)
        game.projectiles.append(Projectile(
            unit, unit.pos + direction * 30, direction * self.speed,
            life=self.range / self.speed, damage=60 + 1.2 * unit.atk, drain=self.drain))
        unit.facing_left = direction.x < 0
        return True


class PulseRush(Ability):
    """Beat dashes in a burst of excitement, then stays fast for a moment."""
    key = "e"
    name = "Pulse Rush"
    cooldown = 8.0
    unlock = 3
    icon = "dash"
    blurb = "Dash the way you're walking, then move 25% faster for 2 seconds."
    distance = 260
    time = 0.2
    ai_min, ai_max = 170, 420
    escape = True
    auto_target = False         # you dash the way you're walking, so it can also escape

    def cast(self, game, unit, aim):
        direction = aim_direction(unit, aim)
        unit.dash_timer = self.time
        unit.dash_vel = direction * (self.distance / self.time)
        unit.haste_timer = 2.0
        unit.facing_left = direction.x < 0
        unit.cancel_scoring()
        return True


# ------------------------------------------------------------------ Potas --
class VineLash(Ability):
    """Potas shoots a vine out in a straight line, hitting and slowing everything on it."""
    key = "q"
    name = "Vine Lash"
    cooldown = 6.0
    icon = "vine"
    blurb = "Shoot a vine in a line that hits and slows everything it touches."
    length = 320
    width = 34
    ai_max = 330
    hits_wilds = True

    def cast(self, game, unit, aim):
        direction = aim_direction(unit, aim)
        start = V(unit.pos)
        end = start + direction * self.length
        game.effects.append(Effect("vine", start, 0.35, to=end))
        targets = game.enemies_of(unit) + [w for w in game.wilds if w.alive]
        for t in targets:
            if distance_to_segment(t.pos, start, end) <= self.width + t.radius:
                game.damage(t, 55 + 1.1 * unit.atk, unit)
                if hasattr(t, "slow_timer"):
                    t.slow_timer = max(t.slow_timer, 1.2)
        unit.facing_left = direction.x < 0
        return True


class RootGuard(Ability):
    """Potas plants its roots: tougher and thorny, perfect for guarding a goal."""
    key = "e"
    name = "Root Guard"
    cooldown = 12.0
    unlock = 3
    icon = "guard"
    blurb = "Take 40% less damage and hurt + slow enemies around you for 4 seconds."
    duration = 4.0
    radius = 150
    ai_max = 150

    def cast(self, game, unit, aim):
        unit.guard_timer = self.duration
        unit.guard_tick = 0.0
        return True

    def bot_wants(self, game, me, foe, foe_dist):
        # also use it to stop enemies scoring in one of our goals
        for u in game.enemies_of(me):
            g = u.scoring_goal
            if g is not None and g.team == me.team and u.pos.distance_to(me.pos) < self.radius:
                return True
        return super().bot_wants(game, me, foe, foe_dist)


def distance_to_segment(p, a, b):
    """Shortest distance from point p to the line segment a-b."""
    ab = b - a
    if ab.length_squared() == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, ((p - a).x * ab.x + (p - a).y * ab.y) / ab.length_squared()))
    return p.distance_to(a + ab * t)


KITS = {
    "glum": [Thunderbolt, GloomTrail],
    "beat": [HeartToss, PulseRush],
    "potas": [VineLash, RootGuard],
}
DEFAULT_KIT = [Thunderbolt, GloomTrail]   # for new drawings until they get their own moves

# Passive traits: always on, no button needed.
PASSIVES = {
    "potas": "camouflage",   # standing still makes Potas invisible to enemies
}


def make_kit(sprite_id):
    return [cls() for cls in KITS.get(sprite_id, DEFAULT_KIT)]
