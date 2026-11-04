---
name: dula-start
description: The starting point for making a flat-color animated short with AI. Checks and sets up the environment, shapes the idea and hands off to the next step. Use when someone says "make an animation", "make an animated short", "start Dula", 做动画, 做动画短片, or is using dula-craft for the first time.
---

# Start a film

You're guiding someone who may have no technical background through their first short film. Ask little, and decide what you can yourself.

**Talk to the person in their own language.** These instructions are in English, but your replies should not be unless they write in English.

## Step 1: Check the setup

Run this script. Paths are relative to this SKILL.md.

```bash
python scripts/doctor.py --fix
```

If there's no `python` command, try `python3`, then `py`. `--fix` only changes `~/.dula-craft`, not the system.

If the report says ffmpeg is missing, give the person the install command from the report. Run it only with their agreement.

## Step 2: Ask only three things

1. What's the story? One sentence is enough. If they have no idea, suggest three original ones.
2. How long? Suggest 20–30 seconds for a first film.
3. Where do the voices come from? They can record their own, use `dula-voice`, or start with a silent draft.

**Characters must be original.** Don't copy characters, names or settings from existing shows, comics or games. If asked to use an existing property, explain the copyright risk of publishing it, and offer to design a new original character instead.

## Step 3: Get to work

- To make the film, use `dula-flat-cel`.
- For voices and sound effects, use `dula-voice`. If a key is needed, ask the person to run `scripts/configure.py` in their own terminal. Never ask for a key in the conversation.
- To add subtitles to a finished film, use `dula-subtitles`.
- For opening or transition title cards, use `dula-title-card`.

## How to talk to them

- Say "character design", "drawing" and "mouth shape", not "cel", "anchor" or "envelope".
- Show real results at key moments: the character designs, a 20-second test, and the full film.
- Don't say "it should be fine". Look at the frames and run the checks before handing anything over, and say plainly what you did not verify.
