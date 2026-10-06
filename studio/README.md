# Arena Sprite Studio

The pixel-art pad used to draw every character and creature in the game.

## Two ways to use it

**1. Online, linked to Claude.** Open the studio from the Claude app at
https://claude.ai/artifact/HbcWuK8ACobksAZCiTNG6C. **Save to game** sends the
drawing straight to Claude, who adds it to `assets/sprites/`.

**2. Offline, on your Mac.** Double-click `sprite_studio.html` to open it in
your browser. **Save to game** is hidden here. Instead:

1. Draw, then give it a name, a type and a role.
2. Click **Save sprite file**. A file like `my_creature.json` lands in your Downloads folder.
3. Move that file into the game's `assets/sprites/` folder.
4. Run `python3 main.py`. New characters show up on the start screen
   (left/right arrows), and new creatures need one line in
   `arena/settings.py` (`WILD_STATS`) plus a spot on the map in
   `arena/world.py`.

**Open sprite file** loads any file from `assets/sprites/` so you can edit it.

## Tips
- Draw facing **right**. The game mirrors the drawing when the character turns left.
- Use a dark outline so the character stands out on the grass.
- Mirror mode (M) is handy for symmetrical creatures.
