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
  "mochi": {"desc": "A boy of about eight, bright and lively, quick pace, clear consonants"},
  "gran": {"desc": "A woman of seventy, warm, low register, measured pace, clear diction"}
}
```

Lines can have a `delivery`:

```json
{"id": "l03", "who": "mochi", "text": "R-really?", "delivery": "Surprised and delighted, a quick lift on the first word, rising at the end"}
```

Optional voice fields: `lang` sets the language (by default, the language of the line); `speaker` sets an official Volcano voice ID; `reference` points to reference audio the person has the rights to use.

Write `desc` and `delivery` in English, or in the language of the lines. Describe **the voice itself**: age, tension, breath, pace and weight. "Happy" alone won't change a voice. Don't write "sounds like a certain actor or character", and don't choose voices that imitate well-known characters or real people. Voices carry likeness and copyright risks too.

## Generate

```bash
python <this folder>/scripts/speak.py --dry-run   # See the prompts without spending anything
python <this folder>/scripts/speak.py
```

Each character's first line becomes the voice reference for their later lines, so **listen to the first line first**. If it's not right, change `desc` and redo it. After changing a first line, use `--only` to redo that character's later lines so they follow the new voice.

Before casting each character, play an isolated take to a listener or an audio
model. Ask what gender and age the performance suggests without revealing the
intended role. Record the impression and choose a take that matches the character
and sounds natural in the scene. An unclear or conflicting impression calls for
another audition. Catalog labels and pitch alone cannot establish this match.

When you change a line or a voice and run it again, only what changed is regenerated.

## Line hygiene

Describe age through timbre, pitch and pace, such as an older, warm, low voice with measured pacing. Reserve breathy, trembling, hoarse or raspy delivery for characters who need it. The dialogue prompt asks for clean edges with no throat clearing, coughing or breathing before or after the line.

Check **every isolated line before placing it**, including shouts and recordings from other tools. `speak.py` checks new raw takes and keeps them in `takes/` beside the working clips. Listen to each placed edit on its own, or have an audio model review that single file for breath, throat noise and crackle. Check the scene mix afterward. Regenerate with the same speaker and acting direction when unwanted noise overlaps the words.

```bash
python <this folder>/scripts/line_hygiene.py take.wav --report check.json
python <this folder>/scripts/line_hygiene.py take.wav --words words.json --fix edited.wav --report edit.json
```

Word timings are optional, in seconds from the start of the input, e.g. `[{"start":0.32,"end":0.71}]`. Without timings the script estimates boundaries from voicing and energy. Check quiet opening words, fricatives and expressive cries against the recording before using a cut. The edited copy keeps 40 ms of lead and up to 250 ms of natural decay with 8 ms fades. The command exits nonzero on any flag, including raw flags removed by the edit. Inspect `output_check` and `regenerate_if_confirmed`, then scan and listen to the exact file you will place.

## Ambience and sound effects

```bash
python <this folder>/scripts/speak.py --sound "A quiet old room, a bird far away now and then" --seconds 10 --out audio/sfx/room.wav
```

**Always give `--seconds`.** Billing follows the length, and without it a clip can run 30 seconds or more. It's approximate, and very short requests tend to come back longer. Generated clips are often quiet, so give story sounds a `level_db` in film.json (see the film.json reference).

Generate one thing at a time. Don't ask one prompt for dialogue, effects and music together, or you can't adjust levels separately and the mouths will be wrong.

Footsteps and small Foley sit under the scene unless the sound is the joke: vary every step (several samples,
small level and timing changes), match the surface and the character's size, and keep them well below dialogue.
Identical, evenly spaced, loud steps sound deliberate. Keep one ambience level per location and smooth it across
cuts; when parts of a film are mixed separately, measure the loudness of each stem over the whole film and remove
level jumps that the story does not motivate.

For a quiet story beat, keep a continuous room-tone or outdoor ambience floor.
Fade individual activity layers down or back up over at least one second as
their sources leave or return. Gating the whole ambience stem to silence makes
the location disappear. Check the isolated stem for drops greater than 6 dB
within one second and listen around each flagged time. Use `--cut SECONDS`
only for a picture cut that actually motivates a change of sound environment.

```bash
python <this folder>/scripts/ambience_check.py audio/stems/ambience.wav --report ambience.json
```

The command measures 200 ms RMS windows every 50 ms and compares levels up to
one second apart within each scene. It exits nonzero on a flagged drop or a
silent window. The report also gives the largest rise for checking a return.

Set the bed against a representative passage of active speech. Measure both
stems with the same 250 ms RMS windows. Aim for a busy street about 15–18 dB
below dialogue. A quieter beat can sit 22–25 dB below it while keeping the
location audible. Ride the crowd separately and check the underlying air as
the last voice stops.

Send the dry dialogue to a shared reflection bus for everyone in the same
space. For an open street, start with the wet return 18–22 dB below the dry bus
and about 0.4–0.6 s of decay. Let the return ring across clip boundaries. To
join two parts of a continuous scene, cut between the action frames, remove
intervening black or silence, and carry the bed and outgoing tails across the cut.

Check what the audience receives by decoding the final mix to WAV. Supply the
last audible syllable or cry of each line in seconds on that mix's timeline.

```bash
python <this folder>/scripts/ambience_check.py final_mix.wav --line-end 3.8 --line-end 8.1 --report releases.json
```

This mode checks trailing 250 ms RMS windows at 50 ms steps around each release.
It flags a loss over 20 dB between windows up to half a second apart when the
later window ends in the half-second after the line. A motivated `--cut` bounds
the measurement to the same scene. The report identifies lines ending exactly
at a cut or at the end of the recording. Listen through flagged releases and
across the join to judge whether the ambience and reflections hold together.

## Check the result

- Listen if you can. If you can't, tell the person "this audio hasn't been checked by ear".
- Things you can do yourself: check that lengths make sense (5 seconds for a short line is a problem). If a transcription tool such as Whisper is available, compare its text against the script. Very quiet words may be missing, which is a sign to redo them.
- `delivery` is a request, not an exact control. Pause lengths in particular aren't reliable, so shorten the line or regenerate if the pacing is wrong.
- The same prompt gives a different result each time, so regenerate on errors.
- Clean edits, or the film pops on headphones: give every placed clip a short fade in and out (5-10 ms for speech
  and effects, 20-30 ms for ambience and music joins), cut near zero crossings, and remove the short noise bursts
  some takes carry after the last word. Overlapping clips must not clip; keep the true peak at -1 dBTP or lower.
  Then scan the final mix for sudden sample jumps at every edit point, and compare the encoded file with the
  master around anything flagged.

## Common problems

| Symptom | Fix |
|---|---|
| `Key rejected, or Audio Generation 1.0 is not enabled` | Check the service is enabled. The key must come from the speech console, and Ark keys don't work |
| A word is misread | Regenerate, or reword the line |
| Lines don't sound like one person | Make sure the first line is right, then redo the later ones with `--only`, or set a `speaker` |
| Breath or crackle around a line | Check the isolated raw take and edited copy. Trim a separate edge sound and regenerate noise that overlaps words |
| The end of a line is cut off | Ask for a slower `delivery`, or regenerate |
