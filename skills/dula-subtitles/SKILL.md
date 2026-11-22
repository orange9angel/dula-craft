---
name: dula-subtitles
description: Make and burn in polished dual-language subtitles for a finished video, with a color for each speaker and an optional opening card. Use for adding subtitles, captions, ASS subtitle files or hardcoded subtitles to a video or animation.
---

# Dual-language subtitles

```bash
python scripts/make_subs.py --events subs.json --ass-out subs.ass \
  --video film.mp4 --out-video film_subbed.mp4
```

For just the ASS file, leave out the last two arguments. The script path is relative to this SKILL.md, and it needs only ffmpeg.

Create `subs.json`. You write the translation yourself:

```json
{
  "group": "",
  "project": "",
  "events": [
    {"start": 0.3, "end": 2.8, "speaker": "Sam", "text": "Don't leave after school.", "translation": "Ne pars pas après l'école."}
  ]
}
```

- `text` is the main line, and `translation` is the smaller second line. Leave out `translation` for one language.
- `speaker` is optional. Lines without one, such as song lyrics or narration, share one style.
- Each `speaker` gets a color automatically, in order of appearance. For video sites watched on phones, or busy pictures, add `--plain`: white text with a solid black outline for everyone.
- The subtitle canvas matches the video's frame size, so 4:3 and vertical videos keep the right size and position. Without `--video`, give `--size 1440x1080`. With one language, the line sits low at the bottom; with a translation, it moves up to make room.
- Short lines get shorter fades automatically, so they don't stay faint.
- Leave `group` and `project` empty for no opening card.
- Add `"fade": "300,500"` to an event to change its fade in and out, in milliseconds.
- Set the font with `--font`. The default depends on the system. If you see empty boxes, choose an installed font that covers the language.

## Burned in or switchable

- Add `--srt-out subs.srt` to also write an SRT file.
- On platforms with subtitle tracks, such as YouTube, upload the clean video and the SRT. Viewers can turn the subtitles off, the platform can translate them, and search can read them.
- Burn the subtitles in for platforms without subtitle tracks, and for vertical short clips that people often watch muted.

## Watch out for

- Burn subtitles only onto a clean video. Burning onto a video that already has them gives you two sets.
- In a story film, leave wordless screams, background songs and end credits without subtitles. A music video is different: the lyrics are the subtitles.
- For a music video, choose fonts that match the picture (a soft brush or serif face for a painterly film) rather than the default sans. Keep the font files in a folder and burn with `subtitles=subs.ass:fontsdir=fonts`; the ffmpeg log line `fontselect: (Name, ...) -> File` shows which font was really used.
- A variable font registers under its default instance's name (often "Light"), so a style that names the family can silently fall back to Arial. Cut a static weight with `fontTools.varLib.instancer`, give it its own family name, and use that name.
- Keep position, size and color the same across a series.
- When checking burned subtitles, put `-ss` after `-i`. Putting it first resets the subtitle timeline, so they look missing.
- Before handing over, look at a few frames to confirm subtitles appear and show no empty boxes.
