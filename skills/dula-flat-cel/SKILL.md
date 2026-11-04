---
name: dula-flat-cel
description: Make flat-color line-art animated shorts with an image model and scripts, from story, character designs, drawings and mouth variants to a finished video with sound. Needs only Python and ffmpeg. Use for animated shorts, TV cartoon style, limited animation, dialogue films, keeping a character consistent across shots, or fixing mouths out of sync and flickering drawing swaps. Also for 动画短片, 平涂动画.
---

# Flat-color animation

One drawing holds for 3–4 frames, and the performance comes from swapping drawings and mouth shapes. For simple TV cartoon designs, this is the route where image models stay most consistent. It needs neither 3D nor a video model.

The scripts are in this skill's `scripts/` folder, with paths relative to this SKILL.md. Below, `$S` means that folder. Except for `new_project.py`, **run them from the film folder**. For environment problems, use `dula-start`.

Talk to the person in their own language.

## Workflow

```bash
python $S/new_project.py my_film && cd my_film
```

### 1. Story and shots

Write `story.md`, then `config/film.json` (see the [film.json reference](references/film-json.md)). Keep a first film to 20–30 seconds. Use original characters only.

For every line, think through who says it, to whom, and who the camera shows. Jokes shouldn't rely on words the audience won't understand. Cause and effect needs drawings too (runs in → grabs → the object flies off). Don't skip it with a cut.

### 2. Character designs (the most important step)

Put each character in `config/anchors.tsv` (`name<TAB>appearance`), then run:

```bash
python $S/paint.py anchors config/anchors.tsv
```

**Open and look at every image yourself.** Then show the designs to the person and get their approval before going on. Every later drawing follows these, so a mistake here costs the most to fix. Fix the proportions in words, such as "head one third of total height, round face, small black bead eyes, red overalls".

### 3. Backgrounds and drawings

Fill in `config/plates.tsv` (`name<TAB>description`) and `config/cels.tsv` (`drawing<TAB>character<TAB>pose`). Start drawing names with the character's name, like `hero_run_a`.

```bash
python $S/paint.py plates config/plates.tsv
python $S/paint.py cels config/cels.tsv
```

Rules:

- Draw one character per image. The character design is always the first reference. Never use a rejected image as a reference.
- **Decide which way characters face first.** Images generated one at a time each pick a direction, so two people in a conversation easily end up back to back. Specify it up front, and use `flip` to fix mistakes.
- Derive action cycles from the same drawing, with the same direction and scale.
- For a change in time of day, repaint the background. Multiplying a color can't hide a blue sky.

### 4. Mouths and blinks

Every drawing that talks gets local edits of the same image. In `config/variants.tsv`:

```
hero_stand_m1	hero_stand	Change only the mouth to half open, small oval.
hero_stand_m2	hero_stand	Change only the mouth to wide open.
hero_stand_blink	hero_stand	Close both eyes as simple curved lines. Change nothing else.
```

Names: `<base>_m1` is half open, and `<base>_m2` is wide open. The base drawing itself must have a closed mouth. If it's drawn with the mouth open, make a closed variant and set all three states with `talk` in film.json.

```bash
python $S/paint.py variants config/variants.tsv
python $S/prep_cels.py
```

`prep_cels.py` presses drawings into true flat color and locks each variant to its base. Then **open `build/check_alpha.png`** and check the cutouts on magenta. Redraw any image with leftover background, missing pieces or erased eyes. If it warns about a large changed area, the model edited the body. Add a window `x,y,w,h` as column 4 of variants.tsv.

**Colors drifting?** You can add `config/palette.json` (`{"skin": [250, 220, 190]}`). Only close colors snap to it.

### 5. Sound

Choose one:

- Generate voices with `dula-voice`, using the person's own key.
- Use existing audio: put it at `audio/voice/<line id>.wav`, or set `file` on the line. mp3 and wav both work.
- Make a silent draft: give the line a `seconds` value.

Mouths are calculated from this audio, so settle the voices before making the test.

Optional: `ambience`, `bgm`, `sfx` and `songs`. Use only material the person has the rights to.

### 6. Test

```bash
python $S/build_film.py
python $S/render.py --stills 1,3,5,8,12
python $S/render.py --range 0,20 -o output/pilot.mp4
```

`build_film.py` stops with an error when a visible character talks but their mouth can't move, the easiest mistake to miss. **Look at every still before showing the test.** Don't wait until the whole film is done to show anyone.

### 7. Full film and final check

```bash
python $S/render.py
python $S/check_mouths.py
```

Confirm each of these before handing over, and say plainly if you couldn't:

- [ ] You looked at a real frame from every shot
- [ ] `check_mouths.py` reports no frozen mouths
- [ ] Each character still looks like the same person across shots (face and proportions matter more than color)
- [ ] People in a conversation face each other
- [ ] A single drawing moving across the screen has a `bob` or more drawings, or it reads as sliding
- [ ] You listened to it. If you can't listen, say the audio hasn't been checked by ear

## Pacing

Rules of thumb: shots average 3–5 seconds, characters hold each drawing for 3–4 frames (about 7 drawings a second), with frequent close-ups and exaggerated expressions. `hold` is the number of frames per drawing.

## Common problems

| Symptom | Cause and fix |
|---|---|
| Body colors flicker when mouths swap | The variant didn't go through `prep_cels.py` |
| A walk or run pulses tall and short | Don't size drawings separately. One actor shares one scale automatically. Add `align_head` too |
| A prop takes on the wrong color | A palette entry is too close. Remove it or lower `SNAP` |
| The mouth stays open during speech | Two-state mouths use a 0.5 threshold. Check whether the audio is muffled |
| Constant hiss | The ambience clip is just noise. Replace it. Gain is capped, so it won't be amplified further |
| Codex says the reference image was lost | Image generation must be its first action. `paint.py` handles this, so run it again |

## Limits

This route isn't suited to complex fights, long continuous action or realistic painting.
