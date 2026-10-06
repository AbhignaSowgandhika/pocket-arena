"""
abilities.py - special moves.

Every ability is a small class with the same shape:
    key        which button uses it ("q" or "e")
    name       shown in the HUD
    cooldown   seconds before it can be used again
    unlock     level needed to use it
    cast(game, unit, aim) -> True if it was used

To give a new character its own moves, write new classes here and list them
in KITS at the bottom.
"""
from pygame.math import Vector2 as V

from .entities import Strike


class Ability:
    key = "q"
    name = "Ability"
    cooldown = 5.0
    unlock = 1
    icon = "spark"
    blurb = ""

    def cast(self, game, unit, aim):
        raise NotImplementedError


class Thunderbolt(Ability):
    """Glum's cloud fires a white thunderbolt at a spot on the ground."""
    key = "q"
    name = "Thunderbolt"
    cooldown = 6.0
    unlock = 1
    icon = "bolt"
    blurb = "Strike a spot near your cursor after a short delay."
    range = 420
    radius = 90
    delay = 0.45

    def cast(self, game, unit, aim):
        target = V(aim) if aim is not None else unit.pos + V(-1 if unit.facing_left else 1, 0) * 200
        offset = target - unit.pos
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

    def cast(self, game, unit, aim):
        unit.gloom_timer = self.duration
        unit.puddle_drop = 0.0
        return True


KITS = {
    "glum": [Thunderbolt, GloomTrail],
}
DEFAULT_KIT = [Thunderbolt, GloomTrail]   # until a character gets moves of its own


def make_kit(sprite_id):
    return [cls() for cls in KITS.get(sprite_id, DEFAULT_KIT)]
