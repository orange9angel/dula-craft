---
name: dula-story-design
description: Design the story, title and storyboard of a short film or music video before any drawing or music - several premises with a hook and a turn, an originality check against your earlier films, title criteria, a blind cold-reader critique by a second model, then a beat sheet and shot list ready for production. Use whenever a new film, episode or music video needs a premise, plot, title, lyrics concept or storyboard, or when the person says the story or title is weak.
---

# Story design

Short films most often fail in the story: a good setup that collapses, no highlight, a plot too simple to care about,
and a weak or derivative title is noticed at once. This skill is the story gate. It runs before look keys, drawings,
voices or music; music follows the story, never the reverse.

Talk to the person in their language. Production text (titles, lyrics, dialogue) is in the film's language.

## Gate order

0. **Genre card.** Before anything else, fill the [genre card](references/genre.md): genre and form, what the viewer
   should feel, the lead's want, obstacle, stakes, clock and the device (shown and said in the first ~40 s). Then build
   with that genre's toolkit: comedy as setup / escalation / punch units with plants and payoffs, drama with an
   established normal, a visible time line, atmosphere and rising stakes. Films of 8 minutes or more use the four-act
   plan there. Series episodes go through every step too; an episode must stand alone for a first-time viewer.
1. **Constraints.** Collect the person's standing preferences (settings, jobs or themes they exclude, audience age,
   tone) from their notes or by asking once. Write the ones that apply at the top of `story.md`.
2. **Reference split.** If the person cites an earlier film or an outside work, write two lists in `story.md`:
   - *Borrow*: the working principle only (for example "a small human moment slowly revealed by a moving medium").
   - *Avoid*: its title words, setting, weather, time of day, props, palette, lyric images and emotional arc.
   Fill *Avoid* from a ledger of your earlier films (`PAST_WORKS.md` in the project, one entry per film: title words,
   setting, palette, arc, verdict) for every earlier film of the same kind.
3. **Premises.** Draft at least five premises, each in three lines: hook (first 10 s), turn (what the viewer did not
   expect), payoff (the image the film ends on). Use [craft](references/craft.md) for the engines that work in a
   3-5 minute film or a 2-3 minute music video. Discard any premise that:
   - is a known formula with no twist ("always just missing each other", "meet-cute then parting", "underdog wins");
   - shares two or more *Avoid* items with an earlier film;
   - leaves the visual medium as decoration. The medium (ink, cut paper, translucent planes, sand) should be a story
     device: a prop, a rule of the world, or the form of the reveal.
4. **Cold read.** Run `python scripts/blind_pitch.py story/pitches.md --ledger PAST_WORKS.md --lang <language>` on the
   survivors. A second model reads each pitch cold and reports the ending it predicts after the hook, what feels
   familiar, and what it would remember a day later. Add the genre's cold-read question from the genre card (comedy:
   where did you laugh, get ahead of the joke, get bored; drama: what did the lead want, when did you worry). A premise
   whose turn it predicts, that it calls familiar, or whose want and stakes it cannot state, is rewritten or dropped.
   After each render, repeat the read on the actual cut (frames plus subtitles) as a first-time viewer. The report is mediated evidence; overrule it only with a written reason.
5. **Title.** Draft at least eight titles and pick by the [title rules](references/craft.md#titles): a concrete image or
   object from the story, curiosity without explaining the concept, easy to say or sing, no overlap with earlier
   titles' key words. For a series, use the series name plus an episode title.
6. **Pitch.** Present one recommended premise and title plus at most two alternatives, each in a short paragraph: hook,
   turn, ending image, why it is not like the earlier film. Say plainly what is still weak. Unless the person wants to
   co-design the story, keep outlines and gag lists to yourself so the finished film can still surprise them.
7. **Beat sheet** (after a premise is accepted): `story/beats.md`, one row per beat with time, what the viewer sees, the
   cause visible on screen, emotion, and music section. Every effect beat names the frame that shows its cause
   (cause before effect). For a music video, map beats to song sections first (intro / verse / pre / chorus / bridge /
   final chorus / coda) and place the turn and the reveal on musical events, not between them.
7a. **Plot spine check**: list the events in order and, for each, how it changes the lead's position toward the want.
   Any beat that changes nothing (a trait showcase, a repeated gag) is cut or folded into a beat that does.
7b. **Writers' room** (comedy), only after the spine holds: for every gag beat write three alternative gags from the comic engine, have the cold
   reader pick the one it would laugh at and say why, keep the winner. Ask the reader directly: "does any gag or
   motif feel like a lesson?" - preachy material is cut, whatever its craft.
7c. **Dialogue pass and table read**: write every spoken line with speaker, intent and subtitle translation; read
   each aloud in character (no announcing, no explaining, exposition only through a character with a reason to ask).
   For films with dialogue, generate a cheap table read (one quick take per line, any voice) and listen through it
   with an audio reviewer before any drawing: stiff, unnatural or confusing lines are rewritten now, when it is cheap.
7d. **Animatic** (films over ~3 minutes): storyboard stills timed to the table read, music cue points marked, then a
   first-time-viewer read of the animatic (want, stakes, deadline, rule, laughs, boredom). Production starts only
   when that read comes back right.
8. **Storyboard** `story/storyboard.md`: shot id, duration, framing, picture, what moves and what it causes, sound and
   music, transition. Then cold-read the storyboard (`--mode board`) for "what happened and why" before any image is
   generated; mismatches with the beat sheet are defects.
9. **Lyrics** (music video): written from the beat sheet, so each section carries its beat. Concrete images from this
   story only; run the *Avoid* list over the lyrics too.

## Abstract and non-narrative pieces

When the person asks for no concrete plot (for example colour blocks that keep the rhythm and transform to express a
mood), skip premises and plot cold reads, but keep a structure:
- **Arc of energy and colour**, mapped to song sections: for example scattered and cool -> gathering -> dance ->
  rupture -> one full-frame resolution -> calm. One climax, earned, on the biggest musical event.
- **Two or three visual motifs** that return and change (a figure that assembles from blocks, a horizon line, one colour
  that is withheld until the climax). Repetition with variation replaces plot.
- **Every cut and transformation lands on a beat**; the beat map (onsets, sections) comes from the chosen music.
- **Readable figures**: dancers, a city, waves and action are recognisable silhouettes made of blocks; pure noise is boring.
- **Title**: abstract but specific - a short phrase with an image or a sense (texture, motion, temperature), not a
  theory word; same overlap check against the ledger.

Record every verdict on premises and titles in the ledger and the film's notes, in the person's own words.

## Files

- `references/craft.md`: engines, structure, music video rules, title rules, cliché list.
- `scripts/blind_pitch.py`: cold read of pitches or storyboards by a second model (Codex by default, `--cmd` for another).
