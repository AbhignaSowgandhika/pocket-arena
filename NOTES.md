# Project notes

A running record of what we're building, what we decided and why, and what's
next. Claude updates this file with every change. Newest entries are at the top
of the progress log.

**Goal:** a simple, playable Unite-style game in Python, finished by
**Thursday, Oct 8, 2026**.

---

## Plan to Thursday

| Day | You | Claude |
|---|---|---|
| **Mon, Oct 5** | Draw characters and creatures in Arena Sprite Studio ✅ | Set up repo, notes and v0.1 of the game ✅ |
| **Tue, Oct 6** | First playtest on your Mac, then tell Claude what feels off. Draw 1–2 more characters if you like. | Fix playtest issues. Add the new characters. |
| **Wed, Oct 7** | Second playtest | Per-character abilities, an ultimate move, smarter bots, sound effects (optional) |
| **Thu, Oct 8** | Final playtest | Polish, balance, final notes |

## Decisions

| Date | Decision | Why |
|---|---|---|
| Oct 5 | Start over from scratch | The first version looked too plain (just circles) and its HUD was confusing. |
| Oct 5 | Python + pygame | You want to learn Python. pygame is the most beginner-friendly game library. |
| Oct 5 | You draw the art in a browser pixel-art pad (Arena Sprite Studio) | Drawings save straight to Claude, so there are no files to download or upload. |
| Oct 5 | Claude writes the code and you read along | You chose this. LEARNING.md explains each part. |
| Oct 5 | Store drawings as text (letters = colors) instead of PNG images | You can read, compare and even edit them in GitHub, and loading them needs no extra libraries. |
| Oct 5 | Split the code into small files (rules, drawing, AI, map) | Each file has one job, so it's easier to learn from and to change. |
| Oct 5 | Separate the rules (`game.py`) from the drawing (`render.py`) | Lets us run whole matches with no window to test balance in seconds. |
| Oct 5 | A big map with a camera that follows you, plus walls, bushes and lanes | Feels much more like the real game than a single screen. |
| Oct 5 | Bots press the same "buttons" (Controls) as you | Bots can't cheat, and both follow the same rules in one place. |
| Oct 5 | Glum is the only character, so for now every character is Glum | Bots will use any new characters you draw automatically. |
| Oct 5 | Turned Glum's ability ideas into moves: Thunderbolt (Q) and Gloom Trail (E) | Taken from your description: thunderbolts from its cloud, and purple residue that slows. |
| Oct 5 | Sunshine gives energy and Moonshine heals | Matches what you wrote for each creature. |

## Characters and creatures

| Drawing | Type | In the game |
|---|---|---|
| **Glum** | Character, All-rounder | 700 HP, 46 attack. **Q Thunderbolt:** lightning lands at your mouse after 0.45s and hits everything in the circle. **E Gloom Trail** (level 3): 30% faster for 3.5s and drops puddles that slow enemies by 45% and slowly damage them. |
| **Sunshine** | Wild creature | Gives 12 energy and 45 XP. Respawns after 18s. 11 camps on the map. |
| **Moonshine** | Wild creature | Heals whoever defeats it by 40% of their max HP, plus 4 energy and 55 XP. Respawns after 24s. 2 camps, one near each base. |

To add a character, draw it in Arena Sprite Studio, press **Save to game**, and
tell Claude. Its role sets its stats; see `ROLE_STATS` in `arena/settings.py`.

## Commands explained

| Command | What it does |
|---|---|
| `cd ~/Desktop` | **c**hange **d**irectory: moves Terminal into your Desktop folder (`~` is your home folder). |
| `git clone <url>` | Downloads the whole project from GitHub into a new folder, with its history. Only needed once. |
| `cd pocket-arena` | Moves into the project folder that `git clone` created. |
| `python3 -m pip install -r requirements.txt` | `pip` is Python's package installer. `-r requirements.txt` installs everything listed in that file (just pygame). `python3 -m pip` makes sure pip installs for the same Python you'll run the game with. Only needed once. |
| `python3 main.py` | Runs the game. |
| `git pull` | Downloads the latest changes Claude pushed to GitHub. |

**If pip shows an `externally-managed-environment` error** (common with Homebrew Python):
`python3 -m pip install --user --break-system-packages -r requirements.txt`

**If Terminal says `git` or `python3` isn't found,** macOS will offer to install
"Command Line Developer Tools". Click Install and try again.

## How Claude tests changes

* `tools/simulate.py` plays several full matches with bots controlling every
  character, with no window, to check that nothing crashes and the teams are
  roughly even.
* GitHub runs `.github/workflows/check.yml` on every push. It installs pygame,
  runs the simulation, then plays a match with a hidden window and saves
  screenshots. To see them, open the repo's **Actions** tab, click the latest run,
  and look under **Artifacts**.
* What only you can check: how it **feels** to play (controls, speed,
  difficulty) and how it looks on your screen.

## Progress log

### Mon, Oct 5 – v0.1
* Started over. Moved the old version off the Desktop into `old_pocket_arena/`.
* Built **Arena Sprite Studio** (https://claude.ai/artifact/HbcWuK8ACobksAZCiTNG6C), a 32×32 pixel-art pad with mirror mode, fill,
  undo and an in-game preview. Saved drawings go straight to Claude.
* You drew **Glum**, **Sunshine** and **Moonshine**.
* Built v0.1 of the game:
  * Big map (2800×1600) with a camera that follows you, two lanes, a jungle,
    walls, bushes and a stone base for each team.
  * 6 goals: 2 outer and 1 inner per team. Inner goals unlock once an outer goal
    breaks.
  * Your drawings in the game, with walking bob, shadows, a team ring under
    each character, and a white flash when hit.
  * Glum's Thunderbolt and Gloom Trail abilities.
  * Bots that defeat wild creatures, fight, retreat to heal, find paths around
    walls and go score.
  * **New HUD:** score and timer at the top, kill feed on the left, minimap on the
    right, your character card at the bottom left (HP, XP, energy), ability
    buttons with cooldowns at the bottom, and hints like "Press SPACE to score 12
    energy".
  * Start screen with controls, pause menu and a results screen.
* Simulated 8 bot-vs-bot matches: no crashes, average score 331 to 348.

## Known issues and ideas

* Bots don't use bushes on purpose yet.
* Every character uses Glum's two moves until it gets its own (Wednesday).
* No sound yet.
* Balance numbers are first guesses and will change after you playtest.
