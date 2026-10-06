"""
render.py - draws the game. It READS the Game object but never changes it.

Layers, from back to front:
    1. the map (grass, paths, walls, bushes) - painted once at startup
    2. zones on the ground (goals, bases, puddles, thunderbolt warnings)
    3. things on the map, sorted top-to-bottom so lower things overlap higher ones
    4. effects and floating numbers
    5. health bars and name tags
    6. the HUD (score, timer, minimap, your stats, ability buttons)
    7. menus (start screen, pause, results)

The camera is just an offset: a thing at map position (x, y) is drawn at
screen position (x - camera.x, y - camera.y).
"""
import math
import random

import pygame
from pygame.math import Vector2 as V

from . import settings as S
from .settings import BLUE, RED, SCREEN_W, SCREEN_H, WORLD_W, WORLD_H, xp_to_next

FONT_NAMES = "avenirnext,avenir,helveticaneue,helvetica,arial"

# palette for the map
GRASS_A = (86, 160, 92)
GRASS_B = (78, 150, 86)
GRASS_DOT = (104, 178, 104)
PATH = (196, 176, 128)
PATH_EDGE = (170, 150, 104)
STONE = (120, 126, 140)
STONE_TOP = (160, 166, 180)
STONE_SIDE = (82, 86, 100)
BUSH = (40, 104, 56)
BUSH_LIGHT = (58, 130, 70)
PANEL = (18, 22, 34)
PANEL_EDGE = (60, 70, 96)
MUTED = (170, 178, 196)


class Renderer:
    def __init__(self, screen, bank):
        self.screen = screen
        self.bank = bank
        self.fonts = {}
        self.text_cache = {}
        self.camera = V(0, 0)
        self.clock = 0.0
        self.zones = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self.background = None
        self.minimap_base = None
        self.minimap_size = (248, 142)
        self.tops = {}            # screen y of the top of each character's drawing

    # ------------------------------------------------------------ utilities --
    def font(self, size, bold=True):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
        return self.fonts[key]

    def text_surface(self, text, size, color, bold=True):
        key = (text, size, color, bold)
        surf = self.text_cache.get(key)
        if surf is None:
            if len(self.text_cache) > 600:
                self.text_cache.clear()
            surf = self.font(size, bold).render(text, True, color)
            self.text_cache[key] = surf
        return surf

    def text(self, text, pos, size=20, color=S.WHITE, anchor="center", bold=True, shadow=True, surface=None):
        surface = surface or self.screen
        img = self.text_surface(text, size, color, bold)
        rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
        if shadow:
            surface.blit(self.text_surface(text, size, (0, 0, 0), bold), rect.move(1, 2))
        surface.blit(img, rect)
        return rect

    def to_screen(self, p):
        return (int(p[0] - self.camera.x), int(p[1] - self.camera.y))

    def on_screen(self, p, margin=120):
        x, y = p[0] - self.camera.x, p[1] - self.camera.y
        return -margin < x < SCREEN_W + margin and -margin < y < SCREEN_H + margin

    def panel(self, rect, alpha=215, radius=12, edge=True):
        r = pygame.Rect(rect)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*PANEL, alpha), s.get_rect(), border_radius=radius)
        if edge:
            pygame.draw.rect(s, (*PANEL_EDGE, 255), s.get_rect(), 2, border_radius=radius)
        self.screen.blit(s, r.topleft)
        return r

    def bar(self, x, y, w, h, frac, color, back=(30, 34, 46), radius=3):
        pygame.draw.rect(self.screen, back, (x, y, w, h), border_radius=radius)
        fw = int(w * max(0.0, min(1.0, frac)))
        if fw > 0:
            pygame.draw.rect(self.screen, color, (x, y, fw, h), border_radius=radius)

    # ---------------------------------------------------- the map (painted once)
    def build_background(self, world):
        bg = pygame.Surface((WORLD_W, WORLD_H)).convert()
        rng = random.Random(7)
        tile = 80
        for ty in range(0, WORLD_H, tile):
            for tx in range(0, WORLD_W, tile):
                color = GRASS_A if (tx // tile + ty // tile) % 2 else GRASS_B
                pygame.draw.rect(bg, color, (tx, ty, tile, tile))
        for _ in range(5000):
            x, y = rng.randrange(WORLD_W), rng.randrange(WORLD_H)
            pygame.draw.line(bg, GRASS_DOT, (x, y), (x + rng.choice((-2, 2)), y - 4), 2)

        # dirt paths: the two lanes, the middle crossing and the bases
        mid = WORLD_H // 2
        for y in (250, WORLD_H - 250):
            pygame.draw.rect(bg, PATH_EDGE, (180, y - 66, WORLD_W - 360, 132), border_radius=60)
            pygame.draw.rect(bg, PATH, (190, y - 58, WORLD_W - 380, 116), border_radius=56)
        for x in (270, WORLD_W - 270):
            pygame.draw.rect(bg, PATH_EDGE, (x - 66, 190, 132, WORLD_H - 380), border_radius=60)
            pygame.draw.rect(bg, PATH, (x - 58, 198, 116, WORLD_H - 396), border_radius=56)
        pygame.draw.rect(bg, PATH_EDGE, (540, mid - 46, WORLD_W - 1080, 92), border_radius=46)
        pygame.draw.rect(bg, PATH, (548, mid - 38, WORLD_W - 1096, 76), border_radius=38)
        for team, p in world.bases.items():
            pygame.draw.circle(bg, STONE_SIDE, p, S.BASE_RADIUS + 10)
            pygame.draw.circle(bg, STONE, p, S.BASE_RADIUS)
            for i in range(10):
                a = i / 10 * math.tau
                pygame.draw.line(bg, STONE_SIDE, p, p + V(math.cos(a), math.sin(a)) * S.BASE_RADIUS, 2)
            pygame.draw.circle(bg, S.TEAM_DARK[team], p, 44)
            pygame.draw.circle(bg, S.TEAM_COLOR[team], p, 44, 6)

        # bushes: tall grass you can hide in
        for b in world.bushes:
            pygame.draw.rect(bg, BUSH, (b.x, b.y, b.w, b.h), border_radius=26)
            for _ in range(int(b.w * b.h / 160)):
                x = rng.uniform(b.x + 8, b.right - 8)
                y = rng.uniform(b.y + 10, b.bottom - 4)
                pygame.draw.line(bg, BUSH_LIGHT, (x, y), (x + rng.uniform(-5, 5), y - rng.uniform(8, 16)), 3)

        # walls: a top face and a darker front face give a bit of depth
        for w in world.walls:
            pygame.draw.rect(bg, (40, 70, 44), (w.x + 6, w.y + 10, w.w, w.h), border_radius=10)
            pygame.draw.rect(bg, STONE_SIDE, (w.x, w.y, w.w, w.h), border_radius=10)
            pygame.draw.rect(bg, STONE_TOP, (w.x, w.y, w.w, w.h - 14), border_radius=10)
            for _ in range(int(w.w * w.h / 1400)):
                x, y = rng.uniform(w.x + 8, w.right - 16), rng.uniform(w.y + 6, w.bottom - 26)
                pygame.draw.rect(bg, STONE, (x, y, rng.randint(10, 22), 6), border_radius=3)
        self.background = bg
        mw, mh = self.minimap_size
        self.minimap_base = pygame.transform.smoothscale(bg, (mw, mh))

    # ----------------------------------------------------------- per frame --
    def draw(self, game, dt):
        self.clock += dt
        if self.background is None:
            self.build_background(game.world)
        self.update_camera(game, dt)

        self.screen.blit(self.background, (0, 0), area=pygame.Rect(int(self.camera.x), int(self.camera.y), SCREEN_W, SCREEN_H))
        self.draw_zones(game)
        self.draw_things(game)
        self.draw_effects(game)
        self.draw_overheads(game)
        self.draw_hud(game)

        if game.state == "intro":
            self.draw_intro(game)
        elif game.state == "paused":
            self.draw_paused()
        elif game.state == "over":
            self.draw_results(game)

    def update_camera(self, game, dt):
        target = game.player.pos - V(SCREEN_W / 2, SCREEN_H / 2 + 40)
        target.x = max(0, min(WORLD_W - SCREEN_W, target.x))
        target.y = max(0, min(WORLD_H - SCREEN_H, target.y))
        if game.state == "intro" or self.camera.distance_to(target) > 600:
            self.camera = target                 # jump (start of match, respawn)
        else:
            self.camera += (target - self.camera) * min(1.0, 8 * dt)

    # ------------------------------------------------------- ground layer --
    def draw_zones(self, game):
        z = self.zones
        z.fill((0, 0, 0, 0))
        world = game.world
        for team, p in world.bases.items():
            if self.on_screen(p, 200):
                pygame.draw.circle(z, (*S.TEAM_COLOR[team], 50), self.to_screen(p), S.BASE_RADIUS)
        for p in game.puddles:
            if self.on_screen(p.pos):
                a = int(150 * min(1.0, p.life / 0.6))
                pygame.draw.circle(z, (*S.GLOOM, a), self.to_screen(p.pos), int(p.radius))
        for s in game.strikes:
            if self.on_screen(s.pos):
                progress = 1 - s.timer / s.delay
                pygame.draw.circle(z, (255, 255, 255, int(40 + 90 * progress)), self.to_screen(s.pos), int(s.radius))
        self.screen.blit(z, (0, 0))

        for s in game.strikes:
            if self.on_screen(s.pos):
                pygame.draw.circle(self.screen, S.WHITE, self.to_screen(s.pos), int(s.radius), 3)

        for g in world.goals:
            if self.on_screen(g.pos, 160):
                self.draw_goal(game, g)

    def draw_goal(self, game, g):
        c = self.to_screen(g.pos)
        R = S.GOAL_RADIUS
        is_open = game.world.goal_is_open(g)
        color = S.TEAM_COLOR[g.team] if not g.broken else (110, 110, 120)
        if g.inner and not is_open and not g.broken:
            color = tuple(int(v * 0.55) for v in S.TEAM_COLOR[g.team])
        disc = pygame.Surface((R * 2 + 4, R * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(disc, (*color, 70), (R + 2, R + 2), R)
        self.screen.blit(disc, (c[0] - R - 2, c[1] - R - 2))
        pygame.draw.circle(self.screen, S.TEAM_DARK[g.team] if not g.broken else (70, 70, 80), c, R, 6)
        if not g.broken:
            frac = g.remaining / g.capacity
            rect = pygame.Rect(c[0] - R, c[1] - R, 2 * R, 2 * R)
            if frac > 0:
                pygame.draw.arc(self.screen, color, rect, math.pi / 2, math.pi / 2 + math.tau * frac, 6)
        # the post in the middle
        pygame.draw.circle(self.screen, (40, 44, 58), c, 26)
        pygame.draw.circle(self.screen, color, c, 26, 4)
        if g.broken:
            self.text("X", c, 26, (150, 150, 160))
        elif g.inner and not is_open:
            self.draw_lock(c)
        else:
            self.text(str(g.remaining), c, 22, S.WHITE)

    def draw_lock(self, c):
        x, y = c
        pygame.draw.rect(self.screen, (220, 220, 230), (x - 9, y - 2, 18, 14), border_radius=3)
        pygame.draw.arc(self.screen, (220, 220, 230), (x - 7, y - 14, 14, 18), 0, math.pi, 3)

    # -------------------------------------------------------- things layer --
    def draw_things(self, game):
        items = []
        for o in game.orbs:
            items.append((o.pos.y, "orb", o))
        for w in game.wilds:
            if w.alive:
                items.append((w.pos.y, "wild", w))
        for u in game.units:
            if u.alive and game.can_see(game.player.team, u):
                items.append((u.pos.y, "unit", u))
        for p in game.projectiles:
            items.append((p.pos.y + 30, "heart", p))
        items.sort(key=lambda t: t[0])
        for _, kind, obj in items:
            if not self.on_screen(obj.pos):
                continue
            if kind == "orb":
                self.draw_orb(obj)
            elif kind == "wild":
                self.draw_wild(obj)
            elif kind == "heart":
                self.draw_heart(self.to_screen(obj.pos), 13 + 2 * math.sin(obj.spin * 20), lift=26)
            else:
                self.draw_unit(game, obj)

    def draw_orb(self, o):
        c = self.to_screen(o.pos)
        pulse = 2 * math.sin(self.clock * 6 + o.pos.x)
        pygame.draw.circle(self.screen, S.ENERGY_DARK, (c[0], c[1] + 3), 10)
        pygame.draw.circle(self.screen, S.ENERGY, c, int(9 + pulse))
        pygame.draw.circle(self.screen, (255, 250, 220), (c[0] - 3, c[1] - 3), 3)

    def draw_heart(self, c, size, lift=0, color=(232, 64, 98), surface=None):
        """A heart shape: two circles on top of an upside-down triangle."""
        surface = surface or self.screen
        x, y = c[0], c[1] - lift
        r = size * 0.55
        if lift:
            self.shadow((x, c[1]), int(size * 2), 8)
        for dx in (-r * 0.9, r * 0.9):
            pygame.draw.circle(surface, (40, 10, 20), (int(x + dx), int(y - r * 0.3)), int(r) + 2)
        pygame.draw.polygon(surface, (40, 10, 20), [(x - size - 2, y), (x + size + 2, y), (x, y + size * 1.25 + 3)])
        for dx in (-r * 0.9, r * 0.9):
            pygame.draw.circle(surface, color, (int(x + dx), int(y - r * 0.3)), int(r))
        pygame.draw.polygon(surface, color, [(x - size, y), (x + size, y), (x, y + size * 1.25)])
        pygame.draw.circle(surface, (255, 200, 210), (int(x - r), int(y - r * 0.6)), max(2, int(r * 0.35)))

    def shadow(self, c, w, h=12):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 70), s.get_rect())
        self.screen.blit(s, (c[0] - w // 2, c[1] - h // 2))

    def blit_sprite(self, sprite_id, feet, flip=False, flash=False, alpha=255, bob=0.0, scale=S.SPRITE_SCALE):
        img = self.bank.get(sprite_id, scale, flip, flash)
        left, top, right, bottom = self.bank.bounds(sprite_id)
        if flip:
            left, right = 32 - right, 32 - left
        cx = (left + right) / 2 * scale
        x = feet[0] - cx
        y = feet[1] - bottom * scale + bob
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        self.screen.blit(img, (int(x), int(y)))
        return int(y + top * scale)          # screen y of the top of the drawing

    def draw_wild(self, w):
        c = self.to_screen(w.pos)
        bob = -abs(math.sin(w.t * 3 + w.home.x)) * 5
        glow = (255, 210, 90) if w.kind == "sunshine" else (180, 200, 255)
        self.shadow((c[0], c[1] + 4), 46)
        ring = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(ring, (*glow, 40 + int(25 * math.sin(w.t * 4))), (35, 35), 30)
        self.screen.blit(ring, (c[0] - 35, c[1] - 45 + bob))
        top = self.blit_sprite(w.kind, (c[0], c[1] + 6), flash=w.flash > 0, bob=bob, scale=2)
        if w.hp < w.max_hp:
            self.bar(c[0] - 26, top - 12, 52, 6, w.hp / w.max_hp, (255, 214, 90))

    def draw_unit(self, game, u):
        c = self.to_screen(u.pos)
        me = game.player
        bob = -abs(math.sin(u.walk_time * 10)) * 4 if u.moving else math.sin(self.clock * 2.5 + u.spawn.y) * 1.5
        ring = S.PLAYER_GREEN if u is me else S.TEAM_COLOR[u.team]
        self.shadow((c[0], c[1] + 15), 66, 18)
        pygame.draw.ellipse(self.screen, ring, (c[0] - 36, c[1] + 3, 72, 26), 3)
        if u.gloom_timer > 0:
            pygame.draw.ellipse(self.screen, S.GLOOM, (c[0] - 41, c[1], 82, 32), 3)
        if u.guard_timer > 0:
            aura = pygame.Surface((300, 300), pygame.SRCALPHA)
            pygame.draw.circle(aura, (90, 170, 70, 45), (150, 150), 150)
            for i in range(10):                      # spinning thorns
                a = self.clock * 1.5 + i * math.tau / 10
                p = (150 + math.cos(a) * 140, 150 + math.sin(a) * 140)
                pygame.draw.circle(aura, (40, 110, 40, 220), (int(p[0]), int(p[1])), 7)
            self.screen.blit(aura, (c[0] - 150, c[1] - 150))
        alpha = 150 if game.is_hidden(u) or u.bush is not None else 255
        self.tops[id(u)] = self.blit_sprite(u.sprite_id, (c[0], c[1] + 16), flip=u.facing_left,
                                  flash=u.flash > 0, alpha=alpha, bob=bob)
        if u.slow_timer > 0:
            for i in range(3):
                a = self.clock * 3 + i * 2.1
                pygame.draw.circle(self.screen, S.GLOOM, (int(c[0] + math.cos(a) * 24), int(c[1] + 10 + math.sin(a) * 6)), 4)

    # ------------------------------------------------------------ effects --
    def draw_effects(self, game):
        for e in game.effects:
            if not self.on_screen(e.pos, 400):
                continue
            k = e.life / e.max_life               # 1 -> 0 as the effect fades
            c = self.to_screen(e.pos)
            if e.kind == "zap":
                end = self.to_screen(e.extra["to"])
                pygame.draw.line(self.screen, S.WHITE, (c[0], c[1] - 20), end, 4)
                pygame.draw.line(self.screen, S.TEAM_COLOR[e.extra["team"]], (c[0], c[1] - 20), end, 2)
                pygame.draw.circle(self.screen, S.WHITE, end, int(4 + 6 * k))
            elif e.kind == "bolt":
                rng = random.Random(e.extra["seed"])
                pts, x, y = [], c[0], c[1] - 420
                while y < c[1]:
                    pts.append((x, y))
                    y += 40
                    x = c[0] + rng.randint(-26, 26)
                pts.append(c)
                pygame.draw.lines(self.screen, (200, 220, 255), False, pts, 10)
                pygame.draw.lines(self.screen, S.WHITE, False, pts, 4)
                r = int(e.extra["radius"] * (1.1 - 0.4 * k))
                pygame.draw.circle(self.screen, S.WHITE, c, r, max(1, int(8 * k)))
            elif e.kind == "ring":
                r = int(e.extra["radius"] * (1.4 - 0.6 * k))
                pygame.draw.circle(self.screen, e.extra["color"], c, r, max(1, int(6 * k)))
            elif e.kind == "vine":
                end = self.to_screen(e.extra["to"])
                grow = min(1.0, (1 - k) * 4)          # shoots out quickly, then fades
                tip = (c[0] + (end[0] - c[0]) * grow, c[1] + (end[1] - c[1]) * grow)
                pygame.draw.line(self.screen, (20, 70, 30), c, tip, 16)
                pygame.draw.line(self.screen, (120, 200, 90), c, tip, 8)
                for i in range(1, 7):
                    t = i / 7 * grow
                    px, py = c[0] + (end[0] - c[0]) * t, c[1] + (end[1] - c[1]) * t
                    side = 12 if i % 2 else -12
                    pygame.draw.ellipse(self.screen, (90, 180, 70), (px - 8 + side * 0.6, py - 6 - abs(side) * 0.3, 16, 10))
            elif e.kind == "dash":
                s = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(s, (*S.TEAM_COLOR[e.extra["team"]], int(120 * k)), (30, 30), 24)
                self.screen.blit(s, (c[0] - 30, c[1] - 40))
            elif e.kind == "burst":
                r = int(e.extra["radius"] * (1.05 - 0.25 * k))
                pygame.draw.circle(self.screen, (120, 200, 90), c, r, max(1, int(5 * k)))
            elif e.kind == "levelup":
                r = int(30 + 40 * (1 - k))
                pygame.draw.circle(self.screen, S.HEAL_GREEN, (c[0], c[1] + 8), r, max(1, int(5 * k)))
        for t in game.texts:
            if self.on_screen(t.pos):
                img = self.text_surface(t.text, t.size, t.color)
                img = img.copy()
                img.set_alpha(int(255 * min(1.0, t.life / (t.max_life * 0.5))))
                c = self.to_screen(t.pos)
                self.screen.blit(self.text_surface(t.text, t.size, (0, 0, 0)), img.get_rect(center=(c[0] + 1, c[1] + 2)))
                self.screen.blit(img, img.get_rect(center=c))

    # ------------------------------------------------ name tags and bars --
    def draw_overheads(self, game):
        me = game.player
        for u in game.units:
            if not u.alive or not game.can_see(me.team, u) or not self.on_screen(u.pos):
                continue
            c = self.to_screen(u.pos)
            top = self.tops.get(id(u), c[1] - 50)
            y = top - 16
            if u is me:
                color = S.PLAYER_GREEN
            else:
                color = S.TEAM_COLOR[u.team]
            # level box + health bar
            pygame.draw.rect(self.screen, PANEL, (c[0] - 40, y - 2, 20, 14), border_radius=3)
            self.text(str(u.level), (c[0] - 30, y + 5), 13, S.WHITE, shadow=False)
            self.bar(c[0] - 18, y, 58, 10, u.hp / u.max_hp, color, back=PANEL)
            if u is me:
                pts = [(c[0], y - 8), (c[0] - 8, y - 20), (c[0] + 8, y - 20)]
                pygame.draw.polygon(self.screen, S.PLAYER_GREEN, pts)
                pygame.draw.polygon(self.screen, PANEL, pts, 2)
            else:
                self.text(u.name, (c[0], y - 12), 14, color)
            if u.energy:
                ex, ey = c[0] + 50, y + 5
                pygame.draw.circle(self.screen, S.ENERGY_DARK, (ex, ey + 2), 12)
                pygame.draw.circle(self.screen, S.ENERGY, (ex, ey), 12)
                self.text(str(u.energy), (ex, ey + 1), 14, PANEL, shadow=False)
            if u.scoring_goal is not None:
                self.bar(c[0] - 34, c[1] + 34, 68, 8, u.score_progress / u.score_time, S.ENERGY, back=PANEL)

    # ---------------------------------------------------------------- HUD --
    def draw_hud(self, game):
        self.draw_scoreboard(game)
        self.draw_feed(game)
        self.draw_minimap(game)
        self.draw_player_card(game)
        self.draw_ability_bar(game)
        self.draw_hint(game)

    def draw_scoreboard(self, game):
        cx = SCREEN_W // 2
        self.panel((cx - 190, 10, 380, 60), radius=14)
        m, s = divmod(int(math.ceil(game.time_left)), 60)
        timer_color = S.ENERGY if game.final_stretch else S.WHITE
        self.text(f"{m}:{s:02d}", (cx, 40), 34, timer_color)
        self.text("BLUE", (cx - 150, 28), 13, MUTED, shadow=False)
        self.text(str(game.scores[BLUE]), (cx - 150, 50), 26, S.TEAM_COLOR[BLUE])
        self.text("RED", (cx + 150, 28), 13, MUTED, shadow=False)
        self.text(str(game.scores[RED]), (cx + 150, 50), 26, S.TEAM_COLOR[RED])
        if game.final_stretch and game.state == "playing":
            r = self.panel((cx - 120, 76, 240, 28), alpha=230, radius=14, edge=False)
            pygame.draw.rect(self.screen, S.ENERGY, r, 2, border_radius=14)
            self.text("FINAL STRETCH  -  POINTS x2", r.center, 15, S.ENERGY, shadow=False)

    def draw_feed(self, game):
        y = 14
        for msg, color, age in game.feed:
            alpha = 255 if age < 5 else int(255 * (6 - age))
            img = self.text_surface(msg, 16, S.WHITE)
            w = img.get_width() + 30
            s = pygame.Surface((w, 26), pygame.SRCALPHA)
            pygame.draw.rect(s, (*PANEL, int(alpha * 0.8)), s.get_rect(), border_radius=8)
            pygame.draw.circle(s, (*color, alpha), (12, 13), 5)
            img = img.copy()
            img.set_alpha(alpha)
            s.blit(img, (22, 13 - img.get_height() // 2))
            self.screen.blit(s, (14, y))
            y += 30

    def draw_minimap(self, game):
        mw, mh = self.minimap_size
        x0, y0 = SCREEN_W - mw - 14, 14
        self.panel((x0 - 6, y0 - 6, mw + 12, mh + 12), radius=10)
        self.screen.blit(self.minimap_base, (x0, y0))
        sx, sy = mw / WORLD_W, mh / WORLD_H

        def mp(p):
            return int(x0 + p[0] * sx), int(y0 + p[1] * sy)

        for g in game.world.goals:
            col = (110, 110, 120) if g.broken else S.TEAM_COLOR[g.team]
            pygame.draw.circle(self.screen, col, mp(g.pos), 6)
            pygame.draw.circle(self.screen, PANEL, mp(g.pos), 6, 2)
        for w in game.wilds:
            if w.alive:
                pygame.draw.circle(self.screen, (255, 214, 90) if w.kind == "sunshine" else (200, 215, 255), mp(w.pos), 3)
        for u in game.units:
            if not u.alive or not game.can_see(game.player.team, u):
                continue
            col = S.PLAYER_GREEN if u is game.player else S.TEAM_COLOR[u.team]
            pygame.draw.circle(self.screen, PANEL, mp(u.pos), 6)
            pygame.draw.circle(self.screen, col, mp(u.pos), 4 if u is not game.player else 5)
        cam = pygame.Rect(mp(self.camera), (int(SCREEN_W * sx), int(SCREEN_H * sy)))
        pygame.draw.rect(self.screen, S.WHITE, cam, 1)

    def draw_player_card(self, game):
        u = game.player
        x, y = 14, SCREEN_H - 124
        self.panel((x, y, 330, 110), radius=14)
        # portrait
        pygame.draw.circle(self.screen, S.TEAM_DARK[u.team], (x + 52, y + 55), 40)
        pygame.draw.circle(self.screen, S.PLAYER_GREEN, (x + 52, y + 55), 40, 3)
        img = self.bank.get(u.sprite_id, 2)
        l, t, r, b = self.bank.bounds(u.sprite_id)
        portrait = img.subsurface(pygame.Rect(l * 2, t * 2, (r - l) * 2, (b - t) * 2))
        scale = min(64 / portrait.get_width(), 64 / portrait.get_height())
        portrait = pygame.transform.scale(portrait, (int(portrait.get_width() * scale), int(portrait.get_height() * scale)))
        self.screen.blit(portrait, portrait.get_rect(center=(x + 52, y + 55)))
        # level badge
        pygame.draw.circle(self.screen, PANEL, (x + 84, y + 88), 15)
        pygame.draw.circle(self.screen, S.HEAL_GREEN, (x + 84, y + 88), 15, 2)
        self.text(str(u.level), (x + 84, y + 88), 16, S.WHITE, shadow=False)

        tx = x + 106
        name = game.sprites[u.sprite_id]["name"]
        self.text(name, (tx, y + 12), 20, S.WHITE, anchor="topleft")
        self.text(u.role, (tx + self.text_surface(name, 20, S.WHITE).get_width() + 10, y + 17), 13, MUTED,
                  anchor="topleft", shadow=False)
        # health
        self.bar(tx, y + 42, 206, 16, u.hp / u.max_hp, S.PLAYER_GREEN, radius=4)
        self.text(f"{max(0, int(u.hp))} / {u.max_hp}", (tx + 103, y + 50), 13, S.WHITE)
        # experience
        xp_frac = 1.0 if u.level >= S.MAX_LEVEL else u.xp / xp_to_next(u.level)
        self.bar(tx, y + 62, 206, 5, xp_frac, S.HEAL_GREEN, radius=2)
        # energy
        self.text("ENERGY", (tx, y + 76), 12, MUTED, anchor="topleft", shadow=False)
        self.bar(tx + 58, y + 78, 104, 12, u.energy / S.MAX_ENERGY, S.ENERGY, radius=4)
        self.text(f"{u.energy}/{S.MAX_ENERGY}", (tx + 206, y + 84), 16, S.ENERGY, anchor="midright")

    def draw_ability_bar(self, game):
        u = game.player
        slots = [("Q", u.ability("q"), "q"), ("E", u.ability("e"), "e"), ("SPACE", None, "score")]
        size, gap = 72, 14
        total = len(slots) * size + (len(slots) - 1) * gap
        x = SCREEN_W // 2 - total // 2
        y = SCREEN_H - size - 34
        for label, ability, key in slots:
            rect = pygame.Rect(x, y, size, size)
            in_goal = key == "score" and u.energy > 0 and game.enemy_goal_at(u) is not None
            self.panel(rect, alpha=235, radius=12, edge=False)
            border = S.ENERGY if in_goal else PANEL_EDGE
            if in_goal:
                glow = 3 + int(2 * math.sin(self.clock * 8))
                pygame.draw.rect(self.screen, S.ENERGY, rect.inflate(glow * 2, glow * 2), 3, border_radius=14)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=12)

            if key == "score":
                self.icon_score(rect.center, active=u.energy > 0)
                caption = "Score"
            else:
                self.draw_icon(ability.icon, rect.center)
                caption = ability.name
                locked = u.level < ability.unlock
                cd = u.cooldowns[key]
                if locked or cd > 0:
                    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                    if locked:
                        pygame.draw.rect(shade, (10, 12, 20, 200), shade.get_rect(), border_radius=12)
                    else:
                        h = int(size * cd / ability.cooldown)
                        pygame.draw.rect(shade, (10, 12, 20, 190), (0, size - h, size, h), border_radius=12)
                    self.screen.blit(shade, rect.topleft)
                    if locked:
                        self.draw_lock((rect.centerx, rect.centery - 6))
                        self.text(f"Lv {ability.unlock}", (rect.centerx, rect.centery + 20), 14, S.WHITE)
                    else:
                        self.text(f"{cd:.0f}" if cd >= 1 else f"{cd:.1f}", rect.center, 26, S.WHITE)
            # key label in the corner, name underneath
            kw = self.text_surface(label, 12, PANEL).get_width() + 10
            pygame.draw.rect(self.screen, S.WHITE, (rect.x - 4, rect.y - 8, kw, 18), border_radius=5)
            self.text(label, (rect.x - 4 + kw // 2, rect.y + 1), 12, PANEL, shadow=False)
            self.text(caption, (rect.centerx, rect.bottom + 14), 13, S.WHITE)
            x += size + gap

    def draw_icon(self, name, c):
        x, y = c
        if name == "bolt":
            pygame.draw.ellipse(self.screen, (200, 210, 230), (x - 22, y - 26, 44, 20))
            pts = [(x + 2, y - 10), (x - 10, y + 6), (x - 1, y + 6), (x - 6, y + 24), (x + 12, y + 0), (x + 3, y + 0), (x + 8, y - 10)]
            pygame.draw.polygon(self.screen, (255, 244, 170), pts)
            pygame.draw.polygon(self.screen, S.WHITE, pts, 2)
        elif name == "gloom":
            for dx, dy, r in ((-12, 8, 11), (10, 12, 9), (0, -6, 14)):
                pygame.draw.circle(self.screen, S.GLOOM, (x + dx, y + dy), r)
                pygame.draw.circle(self.screen, (180, 130, 235), (x + dx - r // 3, y + dy - r // 3), max(2, r // 4))
            pygame.draw.line(self.screen, S.WHITE, (x - 22, y + 22), (x + 22, y + 22), 2)
        elif name == "heart":
            self.draw_heart((x, y - 2), 17)
        elif name == "dash":
            for i, col in enumerate(((255, 160, 180), (240, 90, 120), (232, 64, 98))):
                ox = -14 + i * 12
                pygame.draw.polygon(self.screen, col, [(x + ox - 6, y - 14), (x + ox + 8, y), (x + ox - 6, y + 14)])
        elif name == "vine":
            pts = [(x - 24, y + 18), (x - 10, y + 4), (x + 2, y + 8), (x + 22, y - 18)]
            pygame.draw.lines(self.screen, (120, 200, 90), False, pts, 6)
            for px, py in pts[1:]:
                pygame.draw.ellipse(self.screen, (90, 180, 70), (px - 7, py - 12, 14, 9))
        elif name == "guard":
            shield = [(x, y - 22), (x + 18, y - 14), (x + 15, y + 8), (x, y + 22), (x - 15, y + 8), (x - 18, y - 14)]
            pygame.draw.polygon(self.screen, (60, 130, 60), shield)
            pygame.draw.polygon(self.screen, (150, 220, 120), shield, 3)
            pygame.draw.line(self.screen, (150, 220, 120), (x, y - 14), (x, y + 14), 3)
        else:
            pygame.draw.circle(self.screen, S.WHITE, c, 14, 3)

    def icon_score(self, c, active):
        col = S.ENERGY if active else (110, 110, 120)
        pygame.draw.circle(self.screen, col, c, 22, 4)
        pygame.draw.circle(self.screen, col, c, 10)
        pygame.draw.circle(self.screen, (255, 250, 220) if active else (150, 150, 160), (c[0] - 3, c[1] - 3), 3)

    def draw_hint(self, game):
        u = game.player
        msg, color = None, S.WHITE
        if game.state != "playing":
            return
        if not u.alive:
            msg = f"Respawning in {u.dead_timer:.1f}s"
        elif u.scoring_goal is not None:
            msg, color = "Scoring... don't move!", S.ENERGY
        elif u.energy > 0 and game.enemy_goal_at(u) is not None:
            msg, color = f"Press SPACE to score {u.energy} energy", S.ENERGY
        elif u.energy >= S.MAX_ENERGY:
            msg, color = "Energy full! Take it to a red goal", S.ENERGY
        elif u.bush is not None:
            msg, color = "Hidden in the grass", (170, 230, 170)
        elif game.is_hidden(u):
            msg, color = "Camouflaged - enemies can't see you", (170, 230, 170)
        if msg:
            img = self.text_surface(msg, 20, color)
            r = img.get_rect(center=(SCREEN_W // 2, SCREEN_H - 150))
            self.panel(r.inflate(28, 14), alpha=200, radius=12, edge=False)
            self.screen.blit(img, r)

    # ------------------------------------------------------------- menus --
    def dim(self, alpha=170):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((8, 10, 18, alpha))
        self.screen.blit(s, (0, 0))

    def draw_intro(self, game):
        self.dim(190)
        card = self.panel((SCREEN_W // 2 - 420, 60, 840, 590), alpha=245, radius=18)
        cx = card.centerx
        self.text("POCKET ARENA", (cx, card.y + 46), 44, S.WHITE)
        self.text("Collect energy. Score it in the red goals. Most points in 5 minutes wins.",
                  (cx, card.y + 88), 17, MUTED, shadow=False)

        # character picker
        sid = game.player_sprite
        d = game.sprites[sid]
        stage = pygame.Rect(cx - 90, card.y + 116, 180, 160)
        pygame.draw.rect(self.screen, (30, 50, 40), stage, border_radius=14)
        self.blit_sprite(sid, (stage.centerx, stage.bottom - 18), scale=4,
                         bob=math.sin(self.clock * 2) * 3)
        self.text(d["name"], (cx, stage.bottom + 22), 26, S.WHITE)
        self.text(d.get("role") or "All-rounder", (cx, stage.bottom + 48), 15, MUTED, shadow=False)
        if len(game.characters) > 1:
            self.text("<", (stage.x - 30, stage.centery), 40, S.WHITE)
            self.text(">", (stage.right + 30, stage.centery), 40, S.WHITE)
            self.text("Left / Right arrows: choose character", (cx, stage.bottom + 70), 13, MUTED, shadow=False)

        # controls
        kit = game.player.kit
        rows = [("W A S D", "Move  -  basic attacks happen automatically")]
        for a in kit:
            lock = f" (Level {a.unlock})" if a.unlock > 1 else ""
            rows.append((a.key.upper(), f"{a.name}{lock}: {a.blurb}"))
        if game.player.passive == "camouflage":
            rows.append(("Passive", "Camouflage: stand still to vanish from enemies"))
        rows += [("SPACE", "Score energy while standing in a red goal"), ("Esc", "Pause")]
        y = card.y + 372
        for key, what in rows:
            kw = 78
            left = cx - 380
            pygame.draw.rect(self.screen, S.WHITE, (left, y - 11, kw, 22), border_radius=5)
            self.text(key, (left + kw // 2, y), 14, PANEL, shadow=False)
            self.text(what, (left + kw + 14, y), 15, S.WHITE, anchor="midleft", shadow=False)
            y += 28
        pulse = 200 + int(55 * math.sin(self.clock * 4))
        self.text("Press ENTER to start", (cx, card.bottom - 22), 22, (pulse, pulse, 120))

    def draw_paused(self):
        self.dim(150)
        self.text("PAUSED", (SCREEN_W // 2, SCREEN_H // 2 - 20), 54, S.WHITE)
        self.text("Esc to resume  -  Q to quit", (SCREEN_W // 2, SCREEN_H // 2 + 30), 18, MUTED)

    def draw_results(self, game):
        self.dim(190)
        win = game.winner()
        card = self.panel((SCREEN_W // 2 - 300, 120, 600, 450), alpha=245, radius=18)
        cx = card.centerx
        if win is None:
            title, color = "DRAW", S.WHITE
        elif win == game.player.team:
            title, color = "VICTORY!", S.TEAM_COLOR[win]
        else:
            title, color = "DEFEAT", S.TEAM_COLOR[win]
        self.text(title, (cx, card.y + 60), 56, color)
        self.text(str(game.scores[BLUE]), (cx - 90, card.y + 140), 52, S.TEAM_COLOR[BLUE])
        self.text("-", (cx, card.y + 140), 40, MUTED)
        self.text(str(game.scores[RED]), (cx + 90, card.y + 140), 52, S.TEAM_COLOR[RED])
        u = game.player
        stats = [("Points you scored", u.points_scored), ("Opponents defeated", u.kos), ("Final level", u.level)]
        y = card.y + 220
        for label, value in stats:
            self.text(label, (cx - 170, y), 18, MUTED, anchor="midleft", shadow=False)
            self.text(str(value), (cx + 170, y), 22, S.WHITE, anchor="midright")
            y += 40
        self.text("Press R to play again  -  Esc to quit", (cx, card.bottom - 40), 20, S.ENERGY)
