# Director devices (flat drawings + code compositing)

Each entry: what the viewer sees, when to use it, how to build it. They were developed on a music video about crowds
at a city crossing; the rhythm devices made the biggest difference there.

## Rhythm with the music

- **The crowd breathes with the song.** Background motion speed = smoothed RMS of the mix; integrate speed into a position
  curve and drive every moving layer by it, never by raw time. Quiet lines slow the city, the crest races it.
- **Time stops on silence.** Set speed to 0 across a full stop: everything freezes mid-blur and only the story object
  moves. Ramp back over about 4 s when the voice returns.
- **Beat-snapped cuts.** Snap every scene boundary to the nearest felt beat (half the detected tempo for ballads).
- **Light breathes.** +5% exposure decaying over 0.35 s on each felt beat in close-ups.
- **Instrument answers.** Onsets of a plucked lead (for example `librosa.onset.onset_detect`) flare small window or light
  planes in instrumental sections only; keep them off during singing.
- **Phrase framing.** On a recurring wide set, change the framing every 4 felt beats (wide / medium on the lead / a prop /
  low wide) with slow pushes and 0.5 s dissolves. Hold the framing still while an effect plays.

## Motion without walking

- **Static in flow.** The lead stands still; hair and scarf flutter through 3-4 drawings of the identical pose (one sheet,
  registered on the feet) cross-dissolved in a slow loop, while passers-by stream past as motion-blurred silhouettes in
  3 parallax layers (back slow and hazy, mid, near big and soft). It reads as a long exposure.
- **Close-up life.** Two hair-variant drawings cross-dissolved on a cosine loop, with big soft passers-by streaming in front.
- **Resolve from planes.** A close-up assembles from sliding translucent colour planes over about 1.2 s.

## Meaning in one image

- **The glass remembers.** A reflection in a glass wall shows the character at another age or state (pale, tinted, mirrored).
- **Double exposure.** On the key lyric, the other self's face shows faintly inside the close-up (screen blend, mirrored, 0.4 peak).
- **Mirror split.** A near-symmetric set flipped for the other timeline; two halves face each other across the frame.
- **A day in seconds.** A grade that sweeps dawn -> noon -> dusk -> night with a passing shadow band while a still figure waits.
- **Shadow is the future.** A long low-sun shadow shaped as the other self. It only reads where the ground is bright and
  the silhouettes differ clearly.
- **Ghost vs solid.** Make recurring props translucent (screen-blended, blurred); show them solid only at the binding moment.
- **Silk dust.** A prop torn away by the wind breaks into particles of its own colours (sampled from the drawing's pixels),
  swirls with short trails and re-forms as the target drawing. Hold the framing during the effect.

## Crowds that walk

- Choppy commuters have two usual causes: a "keep clear" pocket around the lead that makes figures vanish and pop back,
  and single static cels that slide (gliding feet). Remove the pocket (figures pass behind the lead) and give each person
  4 stride-phase drawings whose phase is driven by distance travelled, not time, with neighbouring phases cross-blended.
- Sparse crowds are watched one figure at a time. Long-exposure blur plus slow speed hides the legs and they read as
  floating. Use little blur, real walking speed (about 0.75 body heights per second) and a stride cycle of about
  1.05 body heights per 4 phases. A single shadow passing a window must also be a walker, not a blurred cutout.

## Checks that caught real problems

- Stills before full renders: a prop hanging below the rail it should rest on, a fragment of a neighbouring cell leaking
  from a sheet, a lead taller than nearer passers-by, a sky smudge from an oversized foreground figure.
- A contact tile every 2 s: monotony (one wide set for 70% of the film) is obvious only at tile level.
- Feet in the road: each plate has its own walkable band (for example pavement between a shelter base and the kerb).
  Measure it on the plate with a row grid and keep every crowd layer and the lead inside it; drop a foreground layer
  where there is no near ground.
- Painted steam, flame or water that never moves: every such source in the plate needs moving overlay, not just one.
- Partial repairs: re-render only the affected time ranges and splice them by frame index (trim, re-encode, keep the
  original audio); look at frames either side of every join.
