# Sound design for a story scene

## Sound script

Write one table per scene before commissioning takes. Name the location, its acoustic character,
the scene's dramatic turn and its time range in the cut. Use one row per change the audience should hear.
Include the sound that arrives from the previous scene and the sound that carries into the next.

| Picture time and action | Continuous stereo layers and transition | Shot distance, voice and room | Walla, reaction and material Foley | Score entrance, ride, release or silence |
|---|---|---|---|---|
| Opening wide, before the door opens | Ventilation, a roomful of voices, a distant fan. Bring the room in 0.6 s before the edit | Wide, short reflections off tile | Unintelligible talk from the waiting group | Lead motif finishes before the first word |
| Cut closer as the handle sticks | Keep the air running. Ease the crowd down | Close, same tile return. Second speaker interrupts | Handle rattles, then settles. A cast member catches their breath | Leave the failed pull and reaction clear |
| Exit to the yard | Carry the tile room 0.5 s past the picture cut as outside air rises | Voice recedes into the doorway | One distant laugh follows the release | Resume the motif after speech, carry the final note into the yard |

Use two or three layers that identify near, middle and distant activity. Start a busy bed around
15-18 dB below active dialogue. In a hush, withdraw individual layers and preserve the air.
Keep the same bed clock across shots in one place. At a change of location try a 0.5-1 s sound
bridge. Reserve a hard acoustic cut for a change the audience should feel.

Match the density of walla to the people present. Use the cast voice for an identifiable laugh,
gasp or effort. Place it at what provokes it, sometimes across another speaker's last syllable.
Keep clean takes for mouth timing. Retain a lead breath when it carries an acting choice.
Send voices and Foley in the same location to the same room response. A wide shot loses some
bass and air and gains reflected sound. A close shot brings back consonants and softens the bed.
Vary Foley with force, material and distance. Include the smaller rebound or settling noise.

Spot a small ensemble and a recurring phrase for the lead. A 20-40 s cue gives the editor room
to pick an entrance, ride the level and land on a held note. Cut a hole for the gag and mark the
return. Keep the entire score phrase, including its pre-lap and decay, between lines. Only an
explicitly scripted, low sustained pad may carry beneath speech. Check the words in the mix.

## Render the sound timeline

Run the scripts from the voice skill with Python and the toolkit's NumPy and SciPy dependencies.
Source paths in this example are relative to the JSON file. Times are seconds on the picture timeline.

```json
{
  "duration": 12,
  "rooms": {"hall": 0.38, "yard": 0.16},
  "beds": [
    {"cut": 0, "layers": [{"file": "air.wav", "gain_db": -16}, {"file": "walla.wav", "gain_db": -24}]},
    {"cut": 7, "prelap": 0.6, "tail": 0.4, "layers": [{"file": "yard.wav", "gain_db": -18}]}
  ],
  "dialogue": [{"file": "line.wav", "at": 2, "location": "hall", "perspective": "close"}],
  "effects": [{"file": "handle.wav", "at": 6, "location": "hall", "perspective": "medium"}],
  "music": [{"file": "motif.wav", "in": 8, "out": 11, "prelap": 0.5, "tail": 0.7,
             "source_start": 3, "gain_db": -12}]
}
```

```bash
python scripts/scene_mix.py sound.json build/scene-take-01
```

- **Beds.** Supply stereo, seam-edited loops or stems long enough to cover the placement. Each layer
  runs from its entrance and repeats at its own length. The first bed starts at zero. Each later
  picture cut owns an equal-power crossfade from `cut - prelap` to `cut + tail`. A single handle
  makes a J- or L-cut. Leave same-location shot changes off this list so their layers keep playing.
- **Dialogue and effects.** Supply trimmed, edge-faded mono or stereo WAVs. The preset is `close`,
  `medium` (default) or `wide`. The room value is its decay in seconds (0.025-3). Every send in the
  named location uses the same generated stereo impulse. Leave end handles in the timeline to capture
  the decay. Place identifiable speaking reactions on the dialogue track to reserve their time.
- **Music.** The source excerpt begins at `source_start` (default zero) when the pre-lap begins.
  Supply audio for the full interval through `out + tail`. The gain ramps up over the pre-lap
  and down over the tail. Edit internal level rides into the source. The mixer flags overlap with
  any trimmed dialogue clip, including overlap from either music handle. Adjacent boundaries may
  touch. For a written sustained pad use `"kind": "pad"` and give its purpose in `pad_reason`.
- **Output.** The new take directory contains aligned float WAVs named `mix`, `bed`, `dialogue`,
  `effects` and `music`. The default rate is 48000 Hz. Set `rate` to change it. Gains are relative
  to the source files. A common gain leaves sample headroom when the sum peaks above 0.89. Check
  true peak on the encode. For the flat-cel renderer, run `build_film.py` first, use its sheet times
  for the sound timeline, then copy the complete cut's `mix.wav` to `build/mix.wav` before rendering.
  When rebuilding timing, repeat the sound step.

## Review the encoded scene

Give a listener or an audio model the full decoded scene, with both sides of its joins. Ask for times
and audible details. Does the location stay continuous across cuts and between words? Does it have
depth? Where does a sound feel thin, pasted in or stop-start? Where is the music too much or too little?
Does the gag have space, and can the listener follow the quietest words? Record the reviewer, cut
version and findings. Use individual stems to locate a problem, then listen through the repaired scene.

Choose a comparable scene from the last accepted film (similar space, amount of speech and dramatic
function). In each directory put the decoded scene in `mix.wav` and the corresponding, time-aligned
post-gain stems in `bed.wav` and `dialogue.wav`. Trim all three to the same picture boundaries and
sample rate within each scene. The two scenes may have different durations. Keep both version IDs and
time ranges with the report.

```bash
python scripts/scene_review.py candidate-scene accepted-scene --report comparison.json
```

| Report field | Measurement | What to check at a flagged difference |
|---|---|---|
| `loudness_range_lu` | FFmpeg loudnorm input LRA over the full mix, in LU | Was a quiet beat flattened or a level change exaggerated? Short scenes give few three-second windows. |
| `bed_dialogue_db` | Bed-to-dialogue energy in the same active 250 ms windows, averaged across channels. Speech must be within 30 dB of the loudest dialogue window and at least -70 dBFS RMS. | Is the location audible through the conversation? Does it mask soft words? |
| `spectral_tilt_db` | High-band power (2-8 kHz) relative to low-band power (125 Hz-1 kHz) in the full mix. Both scenes use their common available bandwidth. | Has the room lost body, or has a bright layer moved too far forward? |

The JSON gives both readings, signed candidate-minus-reference differences, tolerances and pass/fail.
The starting tolerances are 3 LU, 3 dB and 3 dB. Set `--range-lu`, `--ratio-db` and `--tilt-db`
to match the comparison chosen in the sound script. Exit 0 means all three fall within tolerance,
1 means a difference exceeded tolerance or a reading was unavailable, and 2 indicates an input
or tool error. LRA needs at least three seconds of measurable programme, and a ratio needs both
audible dialogue and bed energy in the speech windows. Record missing stems or an unavailable
accepted reference as a gap. Investigate flags in context, document intended differences and rerun
the comparison and listening review after a repair.
