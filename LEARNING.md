# How the code works

A guided tour of Pocket Arena for someone who knows Python syntax and wants to
see how a real game fits together. Read it alongside the code. Each file also
starts with a comment explaining its job.

---

## 1. The big idea: a game is a loop

Every game, from Pong to Unite, repeats the same three steps about 60 times per second:

```
while True:
    read input       # which keys are down? where's the mouse?
    update the world # move things, apply damage, count down timers
    draw everything  # paint a new picture and show it
```

That loop is in `main.py`. Read it first. It's short.

### Why `dt` is everywhere

`dt` ("delta time") is how many seconds passed since the last frame, about
0.016 at 60 fps. Every movement and timer is multiplied by it:

```python
u.pos += direction * u.speed * dt        # speed is "pixels per SECOND"
u.cooldowns[key] -= dt                   # cooldowns count down in real seconds
```

Without `dt`, the game would run faster on a faster computer. With it, Glum
walks 180 pixels per second no matter how fast your Mac is.

---

## 2. Rules and drawing are kept apart

| File | Job | Uses pygame graphics? |
|---|---|---|
| `game.py` | **The rules:** who takes damage, who scores, who levels up | No |
| `render.py` | **The picture:** reads the game state and draws it | Yes |

`render.py` never changes the game. It only looks. This pattern is called
separating the **model** (the data and rules) from the **view** (how it's shown).

The payoff: `tools/simulate.py` runs the rules thousands of times faster than
real time, with no window at all. That's how we test balance.

---

## 3. Classes: one per kind of thing

`entities.py` defines a class for each kind of object on the map. A class is a
blueprint. `Unit` describes what every character has (health, energy, level,
position), and each character on the map is one **instance** of it:

```python
glum = Unit("You", BLUE, "glum", "All-rounder", kit, spawn=(150, 800))
glum.hp          # 700
glum.energy      # 0
```

### `@property`: values that are calculated, not stored

```python
@property
def speed(self):
    s = self.base["speed"]
    if self.gloom_timer > 0:
        s *= 1.3          # Gloom Trail makes you faster
    if self.slow_timer > 0:
        s *= 0.55         # standing in an enemy puddle slows you
    return s
```

You read it like a normal value (`u.speed`), but it's worked out fresh each
time, so it can never be out of date.

### `@dataclass`: a class that just holds data

`Controls` is a `@dataclass`. Python writes the boring `__init__` for us:

```python
@dataclass
class Controls:
    move: V = field(default_factory=V)
    aim: Optional[V] = None
    q: bool = False
    e: bool = False
    score: bool = False
```

---

## 4. You and the bots press the same buttons

This is the most important design idea in the project:

* `main.py` turns your keyboard and mouse into a `Controls` object.
* `ai.py` builds a `Controls` object for each bot.
* `game.py` handles **both** with the same function, `apply_controls`.

So a bot can't do anything you can't. It can't teleport or ignore cooldowns.
If a rule changes, it changes for everyone in one place.

---

## 5. Abilities use inheritance

`abilities.py` has a base class `Ability` and one subclass per move:

```python
class Thunderbolt(Ability):
    key = "q"
    cooldown = 6.0

    def cast(self, game, unit, aim):
        ...  # put a Strike on the ground at `aim`
        return True
```

The game doesn't need to know what an ability does. It calls `ability.cast(...)`
and starts the cooldown. This is **polymorphism**: many classes share one method
name, and each does its own thing. A new move is just a new class plus one line
in `KITS`.

Thunderbolt doesn't hurt anyone immediately. It creates a `Strike` with a
timer. Each frame the timer counts down, and at zero `game.tick_strikes` deals
the damage. The delay gives the target a chance to dodge, and gives you a
chance to see the white warning circle.

---

## 6. Vectors: positions and directions

`pygame.math.Vector2` (imported as `V`) holds an `x` and a `y` and does the math:

```python
offset = target - unit.pos       # an arrow from the unit to the target
offset.length()                  # how far away (Pythagoras)
offset.normalize()               # same direction, length 1
unit.pos.distance_to(enemy.pos)  # distance between two points
```

Almost every "is it in range?" check in the game is a `distance_to` compared
with a radius.

---

## 7. How the bots think (`ai.py`)

A **priority list**: check rules top to bottom and act on the first one that
fits.

1. Health under 30%? Go home and heal until over 90%.
2. Enemy in range? Use Thunderbolt or Gloom Trail.
3. Carrying enough energy? Walk to the nearest open red goal and score.
4. Enemy within 330 px? Fight it.
5. Energy lying nearby? Pick it up.
6. Otherwise, defeat wild creatures near your lane.

Bots only re-decide every 0.15 seconds. This is cheaper, and it feels more
human because they react a little late.

### Finding a path around walls (`world.py`)

Walking straight at a target gets bots stuck on walls. The fix:

1. Put a **waypoint** just outside each corner of every wall.
2. Connect two waypoints if a straight line between them doesn't hit a wall.
   This makes a **graph**.
3. To go somewhere, run **Dijkstra's algorithm** to find the shortest route
   through the graph, then walk to its first waypoint.

Dijkstra's algorithm uses a **priority queue** (Python's `heapq`) to always
explore the shortest path found so far. It's the same idea map apps use for
directions.

---

## 8. Bushes and "can see"

`game.can_see(team, unit)` decides whether a team can see a unit. A unit in a
bush is hidden from enemies unless one of these is true:

* an enemy is within 150 px, or in the same bush
* it attacked in the last second

Both the renderer (what you see) and the bots (what they react to) use this
same function. That's why bots can't spot you in the grass either.

---

## 9. Drawing (`render.py`)

* **The camera** is just an offset. To draw something, subtract the camera
  position from its map position.
* **The map** (grass, paths, walls, bushes) is painted once at the start onto
  one big image. Each frame we copy only the part the camera can see, which is
  fast.
* **Depth:** things are drawn sorted by their `y` position, so a character
  standing lower on the screen overlaps one behind it.
* **Transparency:** goal zones, puddles and panels use surfaces with an alpha
  channel (`pygame.SRCALPHA`). Alpha 0 is invisible and 255 is solid.
* **Caching:** building a sprite image or rendering text is slow-ish, so
  `SpriteBank` and `text_surface` keep results in a dictionary and reuse them.

---

## 10. Sprites as text (`assets/sprites/*.json`)

Your drawings are stored like this:

```json
"palette": {"a": "#1b1b26", "b": "#1f3f7a", "e": "#5b2a86"},
"rows": [
  "...........aaaaa................",
  "..........aabbbaa..aaaa.........",
```

Each letter is a color from the palette and `.` is transparent.
`sprites.py` reads this and paints one pixel per letter, then scales the image
up 3× so each pixel becomes a 3×3 block. That's what keeps the pixel-art look
sharp.

---

## 11. Things to try yourself

These are small, safe changes. Run `python3 main.py` after each one to see the
effect. You can undo any change with `git checkout -- <file>`.

1. **Longer matches:** in `arena/settings.py`, change `MATCH_SECONDS = 5 * 60` to `8 * 60`.
2. **Faster Glum:** in `ROLE_STATS`, raise `"All-rounder"`'s `speed`.
3. **Bigger thunderbolt:** in `abilities.py`, raise `Thunderbolt.radius`.
4. **Greedier bots:** in `ai.py`, change `random.randint(14, 32)` to `(30, 50)`.
   Bots will hold more energy before scoring.
5. **Read a decision:** in `ai.py`, add `print(me.name, "is retreating")` inside
   the retreat rule. Run the game and watch Terminal.
