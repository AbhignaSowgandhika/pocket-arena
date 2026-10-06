"""
game.py - the rules of the game. No drawing happens here.

Game.update(dt, player_controls) moves the whole match forward by `dt`
seconds. Every frame it:

    1. asks each bot's Brain for its Controls (you supply yours)
    2. applies everyone's Controls: move, use abilities, start scoring
    3. ticks timers: cooldowns, healing, respawning, scoring progress
    4. runs automatic attacks, thunderbolts, puddles and orb pickups
    5. cleans up anything that has expired

Keeping the rules separate from the drawing means we can run thousands of
matches with no window at all to test balance (see tools/simulate.py).
"""
import random

from pygame.math import Vector2 as V

from . import settings as S
from .abilities import make_kit
from .ai import Brain
from .entities import Unit, Wild, Orb, Puddle, Effect, FloatText, Controls
from .world import World


class Game:
    def __init__(self, sprites, player_sprite=None):
        """`sprites` is the dict from sprites.load_all()."""
        self.sprites = sprites
        self.characters = [k for k, d in sprites.items() if d.get("kind") == "character"]
        if not self.characters:
            raise SystemExit("No characters found in assets/sprites. Draw one in the Sprite Studio first!")
        self.player_sprite = player_sprite if player_sprite in self.characters else self.characters[0]
        self.reset()

    # ------------------------------------------------------------------ setup --
    def reset(self):
        self.world = World()
        self.time_left = float(S.MATCH_SECONDS)
        self.scores = {S.BLUE: 0, S.RED: 0}
        self.state = "intro"            # intro -> playing <-> paused -> over
        self.units = []
        self.brains = {}
        self.wilds = [Wild(kind, pos) for kind, pos in self.world.wild_spots]
        self.orbs, self.strikes, self.puddles = [], [], []
        self.effects, self.texts = [], []
        self.feed = []                  # recent events for the kill feed: [text, color, age]

        lanes = ["top", "bottom", "jungle"]
        for team in (S.BLUE, S.RED):
            base = self.world.bases[team]
            for i in range(3):
                spawn = base + V(0, (i - 1) * 90)
                if team == S.BLUE and i == 1:
                    sprite_id, name, is_player = self.player_sprite, "You", True
                else:
                    sprite_id = random.choice(self.characters)
                    is_player = False
                    name = f"{S.TEAM_NAME[team]} {self.sprites[sprite_id]['name']}"
                role = self.sprites[sprite_id].get("role") or "All-rounder"
                u = Unit(name, team, sprite_id, role, make_kit(sprite_id), spawn, is_player)
                self.units.append(u)
                if not is_player:
                    self.brains[u] = Brain(lanes[i])
        self.player = next(u for u in self.units if u.is_player)

    @property
    def final_stretch(self):
        return self.time_left <= S.FINAL_STRETCH

    # -------------------------------------------------------------- helpers --
    def can_see(self, team, unit):
        """Can `team` see `unit`? Units hiding in a bush are invisible to enemies
        unless an enemy is close by or the hider just attacked."""
        if unit.team == team or unit.bush is None or unit.reveal_timer > 0:
            return True
        for u in self.units:
            if u.team == team and u.alive:
                if u.bush == unit.bush or u.pos.distance_to(unit.pos) < S.BUSH_REVEAL_DISTANCE:
                    return True
        return False

    def ability_ready(self, unit, key):
        a = unit.ability(key)
        return a is not None and unit.level >= a.unlock and unit.cooldowns[key] <= 0

    def enemies_of(self, unit):
        return [u for u in self.units if u.team != unit.team and u.alive]

    def text(self, pos, msg, color, size=22, life=0.9):
        self.texts.append(FloatText(pos, msg, color, size, life))

    def announce(self, msg, color):
        self.feed.append([msg, color, 0.0])
        self.feed = self.feed[-5:]

    # ------------------------------------------------------------ main loop --
    def update(self, dt, player_controls):
        if self.state != "playing":
            return
        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0:
            self.state = "over"
            return

        for u in self.units:
            controls = player_controls if u.is_player else self.brains[u].update(u, self, dt)
            self.apply_controls(u, controls or Controls(), dt)
        for u in self.units:
            self.tick_unit(u, dt)
        for w in self.wilds:
            self.tick_wild(w, dt)
        self.tick_strikes(dt)
        self.tick_puddles(dt)
        self.tick_orbs(dt)
        for item in self.effects + self.texts:
            item.life -= dt
        for t in self.texts:
            t.pos.y -= 34 * dt
        self.effects = [e for e in self.effects if e.life > 0]
        self.texts = [t for t in self.texts if t.life > 0]
        for f in self.feed:
            f[2] += dt
        self.feed = [f for f in self.feed if f[2] < 6]

    # ------------------------------------------------------------- controls --
    def apply_controls(self, u, c, dt):
        if not u.alive:
            return
        if c.q:
            self.cast(u, "q", c.aim)
        if c.e:
            self.cast(u, "e", c.aim)
        if c.score:
            self.start_scoring(u)

        u.moving = c.move.length_squared() > 0.01
        if u.moving:
            u.cancel_scoring()
            direction = c.move.normalize()
            if abs(direction.x) > 0.2:
                u.facing_left = direction.x < 0
            u.pos += direction * u.speed * dt
            self.world.collide(u.pos, u.radius)
            u.walk_time += dt
        u.bush = self.world.bush_at(u.pos)

    def cast(self, u, key, aim):
        if not self.ability_ready(u, key):
            return
        ability = u.ability(key)
        if ability.cast(self, u, aim):
            u.cooldowns[key] = ability.cooldown
            u.cancel_scoring()
            u.reveal_timer = S.REVEAL_AFTER_ATTACK

    # ---------------------------------------------------------------- units --
    def tick_unit(self, u, dt):
        if not u.alive:
            u.dead_timer -= dt
            if u.dead_timer <= 0:
                u.pos = V(u.spawn)
                u.hp = u.max_hp
                u.dead_timer = 0
                u.cancel_scoring()
            return

        for key in u.cooldowns:
            u.cooldowns[key] = max(0.0, u.cooldowns[key] - dt)
        u.attack_cd -= dt
        for name in ("flash", "slow_timer", "reveal_timer"):
            setattr(u, name, max(0.0, getattr(u, name) - dt))

        # healing at base / in your own goals
        heal = 0.0
        if u.pos.distance_to(self.world.bases[u.team]) < S.BASE_RADIUS:
            heal = S.BASE_HEAL
        elif any(g.team == u.team and not g.broken and g.contains(u.pos) for g in self.world.goals):
            heal = S.GOAL_HEAL
        u.hp = min(u.max_hp, u.hp + u.max_hp * heal * dt)

        # Gloom Trail drops a puddle every few steps
        if u.gloom_timer > 0:
            u.gloom_timer -= dt
            u.puddle_drop -= dt
            if u.puddle_drop <= 0:
                u.puddle_drop = 0.16
                self.puddles.append(Puddle(u, u.pos, life=3.0, radius=42, dps=18 + 0.25 * u.atk))

        # scoring progress
        if u.scoring_goal is not None:
            goal = u.scoring_goal
            if not self.world.goal_is_open(goal) or not goal.contains(u.pos):
                u.cancel_scoring()
            else:
                u.score_progress += dt
                if u.score_progress >= u.score_time:
                    self.finish_scoring(u)

        self.basic_attack(u)

    def basic_attack(self, u):
        if u.attack_cd > 0 or u.scoring_goal is not None:
            return
        reach = u.attack_range
        target, best = None, reach
        for e in self.enemies_of(u):               # enemy players come first
            d = e.pos.distance_to(u.pos) - e.radius
            if d < best and self.can_see(u.team, e):
                target, best = e, d
        if target is None:
            for w in self.wilds:
                d = w.pos.distance_to(u.pos) - w.radius
                if w.alive and d < best:
                    target, best = w, d
        if target is None:
            return
        u.attack_cd = S.ATTACK_COOLDOWN
        u.facing_left = target.pos.x < u.pos.x
        if u.bush is not None:
            u.reveal_timer = S.REVEAL_AFTER_ATTACK
        self.effects.append(Effect("zap", u.pos, 0.12, to=V(target.pos), team=u.team))
        self.damage(target, u.atk, u)

    def damage(self, target, amount, source):
        """Hurt a unit or a wild creature. Handles defeats and rewards."""
        if not target.alive:
            return
        amount = int(amount)
        target.hp -= amount
        target.flash = 0.12
        color = (255, 255, 255) if isinstance(target, Wild) else (255, 120, 110)
        self.text(target.pos + V(random.uniform(-10, 10), -30), str(amount), color, size=20, life=0.7)
        if isinstance(target, Wild):
            target.threat = source
            target.calm_timer = 3.0
            if target.hp <= 0:
                self.defeat_wild(target, source)
        else:
            target.cancel_scoring()
            if target.hp <= 0:
                self.defeat_unit(target, source)

    def defeat_wild(self, w, killer):
        w.respawn_timer = w.stats["respawn"]
        w.hp = 0
        self.give_energy(killer, w.stats["energy"], w.pos)
        self.give_xp(killer, w.stats["xp"])
        if w.stats["heal"]:
            amount = int(killer.max_hp * w.stats["heal"])
            killer.hp = min(killer.max_hp, killer.hp + amount)
            self.text(killer.pos + V(0, -55), f"+{amount} HP", S.HEAL_GREEN, size=24)
        self.effects.append(Effect("ring", w.pos, 0.35, color=S.ENERGY, radius=50))
        # teammates nearby get a share of the XP
        for ally in self.units:
            if ally is not killer and ally.team == killer.team and ally.alive \
                    and ally.pos.distance_to(w.pos) < 450:
                self.give_xp(ally, w.stats["xp"] * 0.4)

    def defeat_unit(self, u, killer):
        u.hp = 0
        u.dead_timer = S.RESPAWN_BASE + S.RESPAWN_PER_LEVEL * u.level
        u.cancel_scoring()
        u.gloom_timer = 0
        drop = u.energy // 2 + 2
        u.energy = 0
        while drop > 0:
            amount = min(5, drop)
            drop -= amount
            spot = u.pos + V(random.uniform(-40, 40), random.uniform(-40, 40))
            self.world.collide(spot, Orb.radius)
            self.orbs.append(Orb(spot, amount))
        if isinstance(killer, Unit):
            killer.kos += 1
            self.give_xp(killer, 60 + 20 * u.level)
            who = "You" if killer.is_player else killer.name
            whom = "you" if u.is_player else u.name
            self.announce(f"{who} defeated {whom}", S.TEAM_COLOR[killer.team])

    def give_energy(self, u, amount, where):
        take = min(amount, S.MAX_ENERGY - u.energy)
        u.energy += take
        if take:
            self.text(u.pos + V(0, -46), f"+{take}", S.ENERGY, size=24)
        if amount - take > 0:          # full? the rest falls on the ground
            self.orbs.append(Orb(where, amount - take))

    def give_xp(self, u, amount):
        if u.gain_xp(amount):
            self.effects.append(Effect("levelup", u.pos, 0.8))
            self.text(u.pos + V(0, -70), f"Level {u.level}!", S.HEAL_GREEN, size=26, life=1.2)

    # --------------------------------------------------------------- scoring --
    def enemy_goal_at(self, u):
        for g in self.world.goals:
            if g.team != u.team and g.contains(u.pos) and self.world.goal_is_open(g):
                return g
        return None

    def start_scoring(self, u):
        if u.scoring_goal is not None or u.energy <= 0:
            return
        goal = self.enemy_goal_at(u)
        if goal is None:
            return
        u.scoring_goal = goal
        u.score_progress = 0.0
        u.score_time = S.SCORE_BASE_TIME + S.SCORE_TIME_PER_ENERGY * u.energy

    def finish_scoring(self, u):
        goal = u.scoring_goal
        pts = u.energy
        mult = 2 if self.final_stretch else 1
        self.scores[u.team] += pts * mult
        u.points_scored += pts * mult
        goal.points += pts
        u.energy = 0
        u.cancel_scoring()
        self.give_xp(u, pts * 3)
        self.effects.append(Effect("ring", goal.pos, 0.5, color=S.TEAM_COLOR[u.team], radius=S.GOAL_RADIUS))
        self.text(goal.pos + V(0, -30), f"+{pts * mult}", S.TEAM_COLOR[u.team], size=40, life=1.4)
        who = "You" if u.is_player else u.name
        self.announce(f"{who} scored {pts * mult}", S.TEAM_COLOR[u.team])
        if goal.points >= goal.capacity:
            goal.broken = True
            self.announce(f"{S.TEAM_NAME[goal.team]} goal destroyed!", S.ENERGY)
            for other in self.units:            # everyone scoring here is interrupted
                if other.scoring_goal is goal:
                    other.cancel_scoring()
        if u in self.brains:
            self.brains[u].new_threshold()

    # --------------------------------------------------------- wild creatures --
    def tick_wild(self, w, dt):
        w.t += dt
        if not w.alive:
            w.respawn_timer -= dt
            if w.respawn_timer <= 0:
                w.respawn_timer = 0
                w.hp = w.max_hp
                w.pos = V(w.home)
                w.threat = None
            return
        w.flash = max(0.0, w.flash - dt)
        w.calm_timer -= dt
        if w.calm_timer <= 0:
            w.threat = None
            w.hp = min(w.max_hp, w.hp + w.max_hp * 0.25 * dt)
        # shuffle away from whoever is attacking, but never far from home
        if w.threat is not None and w.threat.alive:
            away = w.pos - w.threat.pos
            if away.length_squared() > 1:
                w.pos += away.normalize() * 45 * dt
        elif w.pos.distance_to(w.home) > 2:
            w.pos += (w.home - w.pos).normalize() * 60 * dt
        if w.pos.distance_to(w.home) > 70:
            w.pos = w.home + (w.pos - w.home).normalize() * 70
        self.world.collide(w.pos, w.radius)

    # ------------------------------------------------- strikes, puddles, orbs --
    def tick_strikes(self, dt):
        landed = []
        for s in self.strikes:
            s.timer -= dt
            if s.timer > 0:
                continue
            landed.append(s)
            self.effects.append(Effect("bolt", s.pos, 0.35, radius=s.radius, seed=random.random()))
            for e in self.enemies_of(s.owner):
                if e.pos.distance_to(s.pos) <= s.radius + e.radius:
                    self.damage(e, s.damage, s.owner)
            for w in self.wilds:
                if w.alive and w.pos.distance_to(s.pos) <= s.radius + w.radius:
                    self.damage(w, s.damage, s.owner)
        self.strikes = [s for s in self.strikes if s not in landed]

    def tick_puddles(self, dt):
        for p in self.puddles:
            p.life -= dt
        self.puddles = [p for p in self.puddles if p.life > 0]
        for e in self.units:
            if not e.alive:
                continue
            touching = [p for p in self.puddles
                        if p.team != e.team and e.pos.distance_to(p.pos) < p.radius + e.radius * 0.5]
            if not touching:
                continue
            # overlapping puddles don't stack: only the strongest one counts
            strongest = max(touching, key=lambda p: p.dps)
            e.slow_timer = max(e.slow_timer, 0.3)
            e.gloom_damage += strongest.dps * dt
            # damage is saved up and dealt in chunks so the numbers stay readable
            if e.gloom_damage >= 20:
                amount, e.gloom_damage = e.gloom_damage, 0.0
                self.damage(e, amount, strongest.owner)

    def tick_orbs(self, dt):
        for o in self.orbs:
            o.life -= dt
            for u in self.units:
                if u.alive and u.energy < S.MAX_ENERGY and u.pos.distance_to(o.pos) < u.radius + o.radius:
                    self.give_energy(u, o.amount, o.pos)
                    o.life = 0
                    break
        self.orbs = [o for o in self.orbs if o.life > 0]

    # --------------------------------------------------------------- results --
    def winner(self):
        b, r = self.scores[S.BLUE], self.scores[S.RED]
        if b == r:
            return None
        return S.BLUE if b > r else S.RED
