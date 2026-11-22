---
name: dula-director-pass
description: Act as the film's director after every render - watch the cut as a whole, rank its weakest moments, invent picture/music devices that lift them (music-driven motion, time-stop on silence, reflections, double exposure, static-in-flow, beat-snapped cuts), implement the best few, re-render and verify. Use after each full draft of a short film or music video, when the person asks you to direct, asks how to make it better, more artistic or more in sync with the song, or before sending any version.
---

# Director pass

Viewers judge by watching. Each pass ends with a better cut, not a list of ideas. Talk to the person in their language,
and keep the story itself out of chat unless they ask for it.

## Loop (every full draft)

1. **Watch the whole cut.** `python scripts/review_tile.py <film.mp4> [--every 2] [--sections sections.json]` writes a
   contact tile labelled with time and song section. Look at the tile first as an editor: repeated framings, long stretches
   of one scene, dead air, energy that does not follow the song. Then open full frames where it matters.
2. **Score against the bar** (`references/checklist.md`): physical sense, monotony, rhythm, readability of the key moment,
   solid vs. ghost hierarchy, scale between figures, motion quality (choppy jumps, gliding walks) and every rejection the
   person has already made. Write each failure with its time.
3. **Rank by viewer impact**, not by ease. One strong fix in the most-watched moment beats five small ones.
4. **Invent devices** for the top 3-5 failures from `references/devices.md`, or new ones in the same spirit. A device must
   come from the film's own world and theme, follow the music, and be achievable with flat drawings and code compositing.
   State each as "what the viewer sees / why it serves the song".
5. **Implement, still-check, render.** Render stills at the affected times before a full render and fix what they show.
   When a repair touches only a few scenes, re-render those ranges and splice them frame-exactly (see devices).
6. **Report briefly:** what changed, as a viewer would see it, what is still weak, and the file. Log decisions in the
   film's notes, with the person's own words when they reject or praise something.
7. **Learn:** verdicts that generalise go into this skill's references or your project memory.

## Rules that held across films

- Walking is the hardest motion to get right with a few drawings: prefer static-in-flow, held poses with moving light,
  and cuts. When someone must walk, put the camera axis on the movement axis.
- Smooth beats choppy: continuous motion (streams, drifts, cross-dissolves) over position jumps.
- Several locations beat one; a single set becomes monotonous within a minute.
- Hierarchy of matter: ghosts and translucent colour for most things; a solid object appears once, at the binding moment.
- Scale and placement must be physically plausible: a person further back is smaller, feet stand on walkable ground,
  nothing blocks a path people use.
- Abstract is fine, but the core event must read on one viewing (cause before effect).
- Don't over-explain in pictures; one memorable image per section.

## Hand-offs

Story problems -> [story-design](../dula-story-design/SKILL.md). Light and atmosphere -> [flat-cinema](../dula-flat-cinema/SKILL.md).
Drawings, motion and mouths -> [dula-flat-cel](../dula-flat-cel/SKILL.md). Voices and sound -> [dula-voice](../dula-voice/SKILL.md).
Lyrics and captions -> [dula-subtitles](../dula-subtitles/SKILL.md).
