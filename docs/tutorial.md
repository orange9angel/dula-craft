# Tutorial: how the demo film was made

[Watch the film](https://orange9angel.github.io/dula-craft/watch.html). It's 15 seconds long: a snail afraid of the rain learns that wet ground is slippery, and slides off happily.

An AI agent made it using only this repository. This page shows what it did at each step, with the real prompts. You don't have to run any of this by hand: **telling your agent "make me an animated short" does all of it.** Read on to see how it works, or to direct your agent better.

All the settings are in [`examples/rainy-slide`](../examples/rainy-slide), ready to copy.

**What it took:** about 40 minutes, 16 generated images and about a minute of generated audio.

## 1. Start with one sentence

The whole story fits in [`story.md`](../examples/rainy-slide/story.md):

> A little snail called Aman, afraid of rain, is told by a frog that wet ground is the best for sliding, and "flies" in the rain for the first time.

Then it became four beats: the fear, the frog's idea, the discovery, and the payoff.

**Decide who faces where right now.** This film's rule was "the snail always faces and travels right, and the frog faces left". Images are generated one at a time, so without a rule like this, two characters in a conversation easily end up back to back.

## 2. Design the characters

Each character gets one line in `config/anchors.tsv`. Be specific about shapes and proportions:

```
snail	A tiny original baby snail character seen from the side, facing screen right. Soft chubby rounded slug body in warm cream yellow, one big round spiral shell on its back in teal green...
```

```bash
python $S/paint.py anchors config/anchors.tsv
```

`$S` is the `scripts` folder of the `dula-flat-cel` skill. Every later drawing uses this design as its reference, so this is the step to get right.

## 3. Draw the poses

Next come the backgrounds (`plates.tsv`) and one line for each pose (`cels.tsv`). Describe the feeling and the body:

```
snail_fear	snail	Facing screen right. Scared: soft body squashed low and pulled half back under the shell, head tucked, eye stalks bent...
```

To keep an action or a place continuous, name what to follow in the last column:

```
snail_zoom_b	snail	...the next drawing of a bouncing slide...	snail_zoom_a
wet	...now soaking wet and shiny...	path
```

This film has just six poses. That's why it's cheap, and why limited animation works: one good drawing, held, says a lot.

```bash
python $S/paint.py plates config/plates.tsv
python $S/paint.py cels config/cels.tsv
python $S/prep_cels.py --bases-only
```

Then open `build/check_alpha.png` to check the cutouts on bright magenta.

## 4. Make the mouths

For each drawing that talks, the mouth is edited and everything else stays put (`variants.tsv`):

```
snail_fear_m1	snail_fear	Change only the mouth to open, a small rounded scared open mouth with dark inside.
```

```bash
python $S/paint.py variants config/variants.tsv
python $S/prep_cels.py
```

`prep_cels.py` flattens the colors and locks each variant to its base. In this film, the mouth drawings differ from their bases only around the mouth, so the body doesn't flicker when mouths swap.

## 5. Give them voices

Each character gets a description of their voice itself, and each line a note on how to say it (`film.json`):

```json
"snail": {"desc": "A child of about six, thin soft voice, slightly tight throat, light breath, a little slow, timid"}
```

```json
{"id": "l01", "who": "snail", "text": "要下雨了……我最怕雨了！", "delivery": "Trembling, tight voice, a hint of tears on the last three words"}
```

The film's lines are in Chinese ("It's going to rain... I'm so scared of rain!"), and were directed in Chinese. Direction here is shown in English, which is how the example is written. Lines can be in any language the voice service supports.

```bash
python <dula-voice folder>/scripts/speak.py --dry-run    # See the prompts. Costs nothing
python <dula-voice folder>/scripts/speak.py
python <dula-voice folder>/scripts/speak.py --sound "steady light rain on grass" --seconds 15 --out audio/sfx/rain.wav
```

This uses your own [voice key](configuration.md#voices). Your own recordings work too: just put them in `audio/voice/`.

## 6. Direct the shots

`config/film.json` is the shot list. Here's the payoff shot, shortened:

```json
{
  "id": "S4",
  "plate": {"key": "wet", "height": 1400, "x": [1050, 390], "y": 1290},
  "hold": 4,
  "lines": ["l04", "l05"],
  "fade_out": 0.6,
  "actors": [
    {"who": "snail", "cels": ["snail_zoom_a", "snail_zoom_b"], "cx": [-300, 1950], "t0": 0, "t1": 4.3,
     "ground": 1045, "height": 300, "bob": 10},
    {"overlay": true, "cels": ["rain_a", "rain_b", "rain_c"]}
  ]
}
```

Four simple tricks make it feel alive:

| Trick | Setting | Effect |
|---|---|---|
| Camera pan | `x` from 1050 to 390 on the plate | The world moves past |
| Travel | `cx` from off-screen left to off-screen right | The snail crosses the frame |
| Swapping drawings | Two `cels`, with `hold: 4` | A bouncing slide |
| Rain | `make_rain.py`, then an `overlay` | The whole scene feels wet |

For every setting, see the [film.json reference](../skills/dula-flat-cel/references/film-json.md).

## 7. Render and check

```bash
python $S/make_rain.py
python $S/build_film.py
python $S/render.py --stills 1,5.6,9,14     # Look at these first
python $S/render.py --range 0,8 -o output/test.mp4
python $S/render.py
python $S/check_mouths.py
```

`build_film.py` refuses to continue if a visible character talks but has no mouth to move. `check_mouths.py` then reads what was actually shown. On this film, it flagged a line where the mouth moved only once, because one loud word set the scale for the whole line. Adding `"mouth_open_at": 0.25` to that line fixed it.

## What could be better

The demo is a first attempt, shown as it came out, so you can see what to expect:

- **The first three shots barely move.** A camera move or an extra drawing would help.
- **The neck in the third shot is too long.** Check proportions in every pose, and redraw what's off.
- **The two backgrounds don't quite look like one place.** The film was made before plates could follow each other. The example's settings use this, so yours should match better.
- **There's no music.** Add a track you have the rights to with `bgm`.

The example folder also has these newer settings, so rebuilding it will differ from the demo: rain as an overlay, audible ambience, a fade-out at the end and better mouths on quiet words. Images and voices are generated fresh each time, so your film will be its own version in any case.

## Make it your own

Keep the steps, and change the story. To start from this example:

1. Say to your agent: "Make a short film like `examples/rainy-slide`, but about a cat who is afraid of the dark."
2. Approve the character designs when it shows you.
3. Watch the test, say what you'd change, and let it finish.

Please use your own original characters. See [Licensing and rights](licenses.md).
