---
name: dula-voice
description: Voice every line of an animated short with the person's own Volcano Engine Seed-Audio key, keeping each character's voice consistent. Also generates ambience and sound effects. Use for character voices, dialogue audio, voice acting, ambience and sound effects.
---

# Voices

Script paths are relative to this SKILL.md, and `speak.py` runs from the film folder. This step is optional: recordings or audio from any other tool also work. Put them at `audio/voice/<line id>.wav`, or set `file` on the line.

Talk to the person in their own language.

## Set up the key (once)

Costs go on the person's own account. Ask them to run this **in their own terminal**:

```bash
python <dula-start folder>/scripts/configure.py
```

In Claude Code, they can type `! python <path>/configure.py`.

**Never ask for the key in the conversation, and never read or print `~/.dula-craft/config.env`.** To check whether one is set, use `configure.py --status`. If someone pastes a key into the conversation, tell them to revoke it in the console and create a new one.

## Design the voices

Add `voices` at the top level of `config/film.json`:

```json
"voices": {
  "mochi": {"desc": "A boy of about eight, bright and lively, quick pace, light breath"},
  "gran": {"desc": "A woman of seventy, warm and slightly husky, slow, very clear diction"}
}
```

Lines can have a `delivery`:

```json
{"id": "l03", "who": "mochi", "text": "R-really?", "delivery": "Surprised and delighted, a tremble on the first word, rising at the end"}
```

Optional voice fields: `lang` sets the language (by default, the language of the line); `speaker` sets an official Volcano voice ID; `reference` points to reference audio the person has the rights to use.

Write `desc` and `delivery` in English, or in the language of the lines. Describe **the voice itself**: age, tension, breath, pace and weight. "Happy" alone won't change a voice. Don't write "sounds like a certain actor or character", and don't choose voices that imitate well-known characters or real people. Voices carry likeness and copyright risks too.

## Generate

```bash
python <this folder>/scripts/speak.py --dry-run   # See the prompts without spending anything
python <this folder>/scripts/speak.py
```

Each character's first line becomes the voice reference for their later lines, so **listen to the first line first**. If it's not right, change `desc` and redo it. After changing a first line, use `--only` to redo that character's later lines so they follow the new voice.

When you change a line or a voice and run it again, only what changed is regenerated.

## Ambience and sound effects

```bash
python <this folder>/scripts/speak.py --sound "A quiet old room, a bird far away now and then" --seconds 10 --out audio/sfx/room.wav
```

**Always give `--seconds`.** Billing follows the length, and without it a clip can run 30 seconds or more. It's approximate, and very short requests tend to come back longer. Generated clips are often quiet, so give story sounds a `level_db` in film.json (see the film.json reference).

Generate one thing at a time. Don't ask one prompt for dialogue, effects and music together, or you can't adjust levels separately and the mouths will be wrong.

## Check the result

- Listen if you can. If you can't, tell the person "this audio hasn't been checked by ear".
- Things you can do yourself: check that lengths make sense (5 seconds for a short line is a problem). If a transcription tool such as Whisper is available, compare its text against the script. Very quiet words may be missing, which is a sign to redo them.
- `delivery` is a request, not an exact control. Pause lengths in particular aren't reliable, so shorten the line or regenerate if the pacing is wrong.
- The same prompt gives a different result each time, so regenerate on errors.

## Common problems

| Symptom | Fix |
|---|---|
| `Key rejected, or Audio Generation 1.0 is not enabled` | Check the service is enabled. The key must come from the speech console, and Ark keys don't work |
| A word is misread | Regenerate, or reword the line |
| Lines don't sound like one person | Make sure the first line is right, then redo the later ones with `--only`, or set a `speaker` |
| The end of a line is cut off | Ask for a slower `delivery`, or regenerate |
