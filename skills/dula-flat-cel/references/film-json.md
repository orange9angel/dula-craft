# config/film.json

All positions are output pixels. The default frame is 1440×1080 at 24 frames per second.

```json
{
  "width": 1440, "height": 1080, "fps": 24,
  "plates": {"room": "assets/plates/room.png"},
  "ambience": {"room": "audio/sfx/room_tone.wav", "rain": {"file": "audio/sfx/rain.wav", "level_db": -35}},
  "bgm": {"file": "audio/music/theme.mp3", "gain": 0.16},
  "voices": {"hero": {"desc": "A bright, quick ten-year-old voice"}},
  "lines": [
    {"id": "l01", "who": "hero", "text": "Hello!"},
    {"id": "l02", "who": "cat", "text": "Meow.", "seconds": 1.2}
  ],
  "shots": [
    {
      "id": "S1",
      "plate": {"key": "room", "height": 1080, "x": 720, "y": 1080},
      "hold": 3,
      "lines": ["l01"],
      "ambience": "room",
      "bgm": "on",
      "sfx": [{"file": "audio/sfx/door.wav", "at": 0.1, "gain": 0.5}],
      "actors": [
        {"who": "hero", "cels": ["hero_stand"], "cx": 480, "ground": 950, "height": 600,
         "blink": [0.6, 2.4], "blink_cel": "hero_stand_blink"}
      ]
    }
  ]
}
```

## Shot

| Field | Meaning |
|---|---|
| `lines` | Lines played in order. Shot length is the total line length plus padding |
| `seconds` | Minimum length. Required for shots with no lines |
| `pre`, `post` | Padding before and after lines. Defaults: 0.15 and 0.25 seconds |
| `together` | All the shot's lines start at the same time instead of one after another, for duets and choirs. Give each singer a line with `who` set, so each mouth follows its own voice. A visible actor with no line in the shot keeps its first (closed) mouth state |
| `hold` | Frames per drawing. Dialogue 3, fast action 2, slow or dreamlike 6–24 |
| `ambience` | Ambience name. Stays on until changed. `null` turns it off |
| `fade_in`, `fade_out` | Fade from or to black, in seconds. On the first and last shots, the sound fades too |
| `bgm` | `"on"` or `"off"`. Stays that way until changed |
| `sfx` | `file`, `at` (seconds into the shot), `gain`. The loudest point lands on `at` |
| `songs` | `file`, `from`, `to` (seconds within the file), `at`, `gain`. Lowered automatically during dialogue |

## Ambience levels

A plain file plays quietly at about -50 dB, right for room tone. Its gain is capped so a noisy clip can't become a constant hiss. For a sound that's part of the story, such as rain, write `{"file": "...", "level_db": -35}`. It allows more gain, so listen for hiss.

## Plate (background)

`height` is the background's scaled height, `x` is its center and `y` is its bottom edge. Use `height` to set the shot size:

| Shot size | height | y |
|---|---|---|
| Wide | 1080 | 1080 |
| Medium | 1728 | 1300 |
| Close-up | 2300 | 1500 |

Write `x` or `y` as `[start, end]` to pan. `tint: [1, 0.92, 0.84]` multiplies the color, for small adjustments only.

## Actor

| Field | Meaning |
|---|---|
| `who` | Character name, matching `who` on lines. Mouths use this |
| `cels` | Drawing names, cycled according to `hold` |
| `cx` | Horizontal center of the visible drawing. Write `[start, end]` to move, over the whole shot unless you set `t0` and `t1` |
| `ground` | Bottom of the visible drawing, where the feet are |
| `height` | Visible height of the first drawing. All drawings share this scale |
| `hold` | Frames per drawing for this actor only, overriding the shot's |
| `overlay` | `true` for a full-frame effect layer, such as rain. It needs only `cels`, and no `cx`, `ground` or `height` |
| `flip` | Mirror horizontally |
| `show` | `[start, end]` in seconds into the shot. Visible only during this time |
| `t0`, `t1`, `steps` | When a move starts and ends, and in how many steps. Fewer steps feel more hand-drawn |
| `dy` | Vertical change during a move |
| `shake` | Shake amount, for fright or shouting |
| `bob` | Up-and-down amount, for walking or joy |
| `align_head` | Align the head across a cycle so it doesn't jump |
| `blink`, `blink_cel` | Blink times in seconds into the shot, and the closed-eye drawing |
| `talk` | Mouth states `[closed, half, wide]`. If omitted, `<drawing>_m1` and `<drawing>_m2` are found automatically |
| `tint` | Color multiplier, such as dusk `[1, 0.92, 0.84]` |

Later actors draw over earlier ones. A speaker who isn't in `actors`, or who has left the frame, counts as a voice-over, and their mouth isn't checked.

An actor doesn't have to be a character. Any transparent PNG you put in `assets/flat/` works, so effects can be a few drawings cycled as an `overlay`. For rain, run `make_rain.py`, then use `{"overlay": true, "cels": ["rain_a", "rain_b", "rain_c"]}`. Check that you have the rights to anything you add.

For a two-state mouth, write `talk` as `["closed", "open", "open"]`. If several drawings have their own mouths, write `{"drawing_a": ["closed", "half", "wide"], "drawing_b": [...]}`.

## Line

Audio defaults to `audio/voice/<id>.wav`, or set `file`. With no audio, set `seconds` as a placeholder. `delivery` describes how to say the line and is used for voice generation (see `dula-voice`). For a line where the mouth deliberately doesn't move, such as one long scream, write `"mouth_ok": "one long scream, mouth stays open"`.

`mouth_open_at` lowers the opening threshold for a two-state mouth on this line, from the default 0.5, when quiet words stay closed. Try 0.25.

Lines take as long as their audio, and shots follow them. To change the length of a film, change the lines or the audio.

## Voices

`voices` is read by `dula-voice`. See that skill for its fields.
