"""
settings.py - every number that controls how the game feels.

If you want to tweak the game (longer matches, stronger attacks, faster
characters), this is the file to edit. Nothing here does any work by itself;
the other files read these values.
"""

# ----- window -----------------------------------------------------------------
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
TITLE = "Pocket Arena"

# ----- world (the whole map is bigger than the window; the camera follows you)
WORLD_W, WORLD_H = 2800, 1600

# ----- match rules ------------------------------------------------------------
MATCH_SECONDS = 5 * 60
FINAL_STRETCH = 60          # last N seconds: every point counts double
MAX_ENERGY = 50             # most energy one character can carry
MAX_LEVEL = 10
SPRITE_SCALE = 3            # 32px drawings are shown at 96px

# ----- teams ------------------------------------------------------------------
BLUE, RED = 0, 1
TEAM_NAME = {BLUE: "Blue", RED: "Red"}

# ----- roles (picked in the Sprite Studio) -> base stats ----------------------
# hp: health at level 1 | atk: basic attack damage | speed: pixels per second
# range: basic attack reach in pixels
ROLE_STATS = {
    "All-rounder": dict(hp=700, atk=46, speed=180, range=135),
    "Attacker":    dict(hp=560, atk=56, speed=192, range=170),
    "Speedster":   dict(hp=600, atk=50, speed=210, range=120),
    "Defender":    dict(hp=900, atk=42, speed=170, range=125),
    "Supporter":   dict(hp=640, atk=38, speed=178, range=150),
}
HP_PER_LEVEL = 0.12          # +12% of base HP each level
ATK_PER_LEVEL = 0.10         # +10% of base attack each level
ATTACK_COOLDOWN = 0.75       # seconds between basic attacks


def xp_to_next(level):
    """XP needed to go from `level` to `level + 1`."""
    return 80 + 45 * level


# ----- wild creatures ---------------------------------------------------------
# energy: dropped when defeated | xp: given to whoever defeats it
# heal: fraction of max HP restored for the one who defeats it
WILD_STATS = {
    "sunshine":  dict(hp=340, energy=12, xp=45, heal=0.0, respawn=18),
    "moonshine": dict(hp=420, energy=4, xp=55, heal=0.40, respawn=24),
}

# ----- goals ------------------------------------------------------------------
GOAL_RADIUS = 78
OUTER_GOAL_POINTS = 80       # an outer goal breaks after taking this many points
INNER_GOAL_POINTS = 120      # the inner goal opens once an outer goal breaks
SCORE_BASE_TIME = 0.5        # seconds to score...
SCORE_TIME_PER_ENERGY = 0.04  # ...plus this much per energy carried (50 -> 2.5 s)

# ----- respawn and healing ----------------------------------------------------
BASE_RADIUS = 130
BASE_HEAL = 0.30             # fraction of max HP per second at your base
GOAL_HEAL = 0.06             # standing in your own goal heals a little
RESPAWN_BASE = 4.0
RESPAWN_PER_LEVEL = 0.7

# ----- bushes -----------------------------------------------------------------
BUSH_REVEAL_DISTANCE = 150   # enemies this close can see into your bush
REVEAL_AFTER_ATTACK = 1.0    # attacking from a bush shows you for 1 second
CAMOUFLAGE_TIME = 1.2        # Potas vanishes after standing still this long

# ----- colors -----------------------------------------------------------------
WHITE = (245, 245, 250)
BLACK = (14, 16, 24)
INK = (24, 28, 40)
ENERGY = (255, 206, 64)
ENERGY_DARK = (186, 128, 20)
HEAL_GREEN = (110, 230, 140)
PLAYER_GREEN = (98, 222, 128)
TEAM_COLOR = {BLUE: (66, 140, 255), RED: (240, 82, 82)}
TEAM_DARK = {BLUE: (24, 60, 140), RED: (130, 30, 34)}
GLOOM = (126, 66, 190)
