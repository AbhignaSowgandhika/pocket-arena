# Pocket Arena

A small 3-vs-3 team battle game, inspired by Pokémon Unite, written in Python with
[pygame](https://www.pygame.org). The characters and creatures are original
drawings made in **Arena Sprite Studio**.

You and two bot teammates (Blue) take on three bot rivals (Red). Defeat wild
creatures to collect energy, carry it to a red goal and score. The team with the
most points after 5 minutes wins.

## Run it on a Mac

One-time setup in **Terminal** (press ⌘ + Space, type "Terminal"):

```bash
cd ~/Desktop
git clone https://github.com/AbhignaSowgandhika/pocket-arena.git
cd pocket-arena
python3 -m pip install -r requirements.txt
```

Play:

```bash
cd ~/Desktop/pocket-arena
python3 main.py
```

Get the latest version after Claude pushes changes:

```bash
cd ~/Desktop/pocket-arena
git pull
```

Each command is explained in [NOTES.md](NOTES.md#commands-explained).

## Controls

| Key | Action |
|---|---|
| W A S D or arrow keys | Move |
| *(automatic)* | Basic attack on the nearest enemy or wild creature |
| Q | Your character's first move, aimed with the mouse |
| E | Your character's second move (unlocks at level 3) |
| Space | Score your energy while standing in a red goal |
| ← → (start screen) | Choose your character |
| Esc | Pause |

## Characters

| | Role | Q | E (level 3) | Extra |
|---|---|---|---|---|
| **Glum** | All-rounder | **Thunderbolt:** lightning strikes at your cursor | **Gloom Trail:** speed up and leave slowing purple puddles | |
| **Beat** | Attacker | **Heart Toss:** a heart that breaks on hit and steals 8 energy | **Pulse Rush:** dash, then move faster for 2 s | Fastest, but fragile |
| **Potas** | Defender | **Vine Lash:** a vine in a straight line that hits and slows | **Root Guard:** take 40% less damage and thorns hurt nearby enemies | **Camouflage:** stand still to turn invisible |

## How to play

* **Energy:** Defeat **Sunshine** creatures for energy (12 each) and **Moonshine**
  creatures to heal (+40% HP). You can carry up to 50.
* **Scoring:** Stand in a red goal and press Space. Scoring takes longer the more
  energy you carry, and taking damage or moving cancels it.
* **Goals:** Each goal breaks after taking 80 points. The inner goal near the base
  is locked until one of that team's outer goals breaks.
* **Bushes:** Hide in the tall grass. Enemies can't see you unless they come close
  or you attack.
* **Knockouts:** If you're defeated you drop half your energy, and you respawn at
  your base after a few seconds.
* **Final stretch:** Points count double in the last minute.

## Project layout

```
main.py              start here: the game loop (keyboard -> rules -> drawing)
arena/
  settings.py        every tunable number (match length, stats, colors)
  world.py           the map: walls, bushes, goals, path finding
  entities.py        characters, wild creatures, orbs, puddles
  abilities.py       special moves for each character
  ai.py              how the bots decide what to do
  game.py            the rules: damage, scoring, leveling, respawning
  render.py          drawing everything, including the HUD
  sprites.py         turns the drawings into images
assets/sprites/      the drawings from Arena Sprite Studio (as text)
studio/              Arena Sprite Studio itself: open sprite_studio.html to draw
tools/
  simulate.py        play many matches with no window (balance testing)
  screenshots.py     play one match with no window and save pictures
```

* [NOTES.md](NOTES.md): progress log, decisions and plans
* [LEARNING.md](LEARNING.md): a guided tour of how the code works
