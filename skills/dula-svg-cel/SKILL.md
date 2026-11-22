---
name: dula-svg-cel
description: Draw flat 2D cels directly in SVG code (props, sets, effects layers, and characters as complete key poses with mouth and eye states), then export registered transparent PNG cels or film a whole scene from a frame timeline with stepped drawing swaps, rigid placement, fades, sub-pixel camera moves and shake. Uses no image-generation quota. Use when a drawing can be authored as vector shapes, when variants must stay pixel-registered, or for a short code-drawn test shot.
---

# SVG cel (drawing in code)

Talk to the person in their language. In a first test a code-drawn copy of an approved character sheet read
as the same character apart from details. Status: experimental. Generated drawings remain the default for
character acting; this skill is for what vector drawing does well and for testing how far code-drawn
characters can go.

```bash
python scripts/svgcel.py states scene.svg                      # switch groups and their states
python scripts/svgcel.py sheet scene.svg hero.pose -o poses.png  # all states of one switch side by side
python scripts/svgcel.py still scene.svg -o cel.png --isolate hero --set hero.pose=point   # registered cel
python scripts/svgcel.py film scene.svg timeline.json -o shot.mp4 --stills 0,48,96
python scripts/svgcel.py trace scene.svg ref.png -o cmp.png --isolate hero --box 554,146,903,903 --ref-box 930,110,600,600
```

`scripts/persp.py` is a small module for wall perspective. Needs Python with Playwright (Chromium, or installed Chrome as fallback), Pillow for `sheet`, and ffmpeg.

## What to draw here, and what not
- Good fits: props, furniture, set elements, signs, title elements, effects layers (speed lines, beams,
  impact frames), simple-shaped creatures, and exact local variants (mouths, blinks) of a code-drawn design.
- Weak fits, measured on the first test: attitude and weight. The copy lost the head tilt, the S-curve of
  the body, cloth drape and the variety between repeated parts (five legs came out as one curl mirrored).
  Check these four by name on every character drawing before it is used.
- Never claim a code-drawn character matches a generated sheet without a side-by-side image.

## Trace against the reference before judging a drawing
For reference-matched work with persistent props or contact, keep real parts addressable (one group per
object, named by what it is); assemblies cannot conceal unexplained geometry. Every object needs its own
drawing criteria and current evidence, including set materials and small construction details. Material
studies are scoped experiments; added noise or more lines cannot fix structure, perspective, lighting or
finish. When a trial is wrong, verify what supports and occludes what in the reference first, draw the
complete local volume, and compare an encoded study before keeping a filter or shape change. Never force a
hand onto a surface that the reference does not show it touching.

`trace` writes three panels at one framing: reference, drawing, and the drawing's dark lines in red over the
reference. `--box` is the stage region, `--ref-box` the matching crop of the reference (same aspect ratio);
fit them on two landmarks (top of head, ground line). Read proportions and staging from the third panel:
which arm does what, where the head sits over the hips, how wide the stance is. The first use showed a pose
staged mirror-wrong (book arm and flung arm swapped, head not carried back) that side-by-side viewing of
separate pictures had missed for four versions. Run it for every pose that has a reference, before timing.
To read a coordinate off the reference: local = landmark_local + (ref_px - landmark_ref_px) * scale.

## Scene file
One SVG per shot or per set; the root `viewBox` is the stage (e.g. `0 0 1920 1080`).
- Paint order is document order: plate, back props, characters, front props, effects, overlays.
- Each mover is a wrapper group with an `id` and no `transform` of its own (the timeline writes it).
- Drawings that replace each other are siblings in a switch group; one state shows at a time:

```xml
<g id="hero">
  <g data-switch="hero.pose">
    <g data-state="stand"> ...complete drawing... </g>
    <g data-state="point"> ...complete drawing... </g>
  </g>
</g>
```

- Switches nest: put `hero.mouth` and `hero.eyes` switches inside each pose that needs them, reusing the
  same switch name; one timeline track drives every copy. A mouth set belongs to one head drawing.
- Define a face once in `<defs>` (head, eye switch, mouth switch) and place it in each pose with `<use>`:
  hiding a state on the original hides it in every copy, so one track drives all poses and the mouth set
  stays registered to its head. A pose then is: its own leg arrangement, a group transform for the lean of
  the upper body, the head `<use>` with its own tilt, and that pose's arms.
- Shared style goes in one `<style>` block (line colour, line width, palette classes). Fix the palette and
  the line width per film and reuse the classes; do not restate colours per shape.
- Clothes are split into pieces that can be swapped per pose: each cardigan panel, each sleeve, the cuff,
  the hem. A pose picks the piece that fits its action (a lifted panel on the raised-arm side, a sleeve with
  a belly hanging under a raised arm) and shares the rest. One shared garment leaned or sheared for every
  pose reads as a board; a traced pilot key showed wide bell sleeves and a hem pulled up by the arm.
- Order inside an arm: tentacle or hand, then the prop, then the grip over the prop, then sleeve and cuff.
- Reuse with `<use>` only for things that are truly identical (desks in a row). Repeated organic parts
  (tentacles, fingers, hair locks) are drawn individually.

## Drawing method
1. Work from an approved reference (look key, model sheet). Read proportions off it in stage units before
   writing paths: head box, eye line, shoulder line, hem, ground line.
2. Block the silhouette first as closed cubic paths, back to front. Render, compare side by side with the
   reference, fix the silhouette before any detail.
3. Then faces, then cloth lines, then small props. Outline stroke about 4.5 px at 1254 px height; thin
   interior lines about 3 px.
4. Flat shadow shapes are clipped to the body shape (`clipPath` of the same outline), then the outline is
   redrawn on top.
5. A stroked centreline (dark wide stroke, then a narrower fill-colour stroke) gives tube shapes with an
   even outline; clip or mask anything drawn on them to the same centreline stroke (`<mask>` accepts
   strokes, `clipPath` does not). Unmasked detail spilled outside the outline in the first test.
6. Render after every change of substance and look at the picture; coordinates lie.

## Painted, hand-drawn look
Plain vector shapes read as clean flat design. Four additions moved a code-drawn scene toward a painted key:
- **Straight construction and surface texture**: keep walls, window frames, desks and other manufactured
  straight edges geometrically straight. Do not put the whole plate, or a listener together with its desk,
  under `wobble`/`wobbleFine`. Fixed noise can still visibly bend a straight line even when it never boils.
  Use seeded grain/mottling clipped to fills without displacement; draw organic contours intentionally.
  The displacement examples in `references/painted-look.svg` are optional stylization experiments,
  not a default treatment for architecture or reference-matched structural edges.
- **Rooms go through one camera** (`scripts/persp.py`, `Camera(pos, yaw, f, centre)`): describe the room in
  3-D (x along the back wall, y up, z toward the viewer) and project every surface with the same camera:
  `wall`, `floor`, `side`, `box` (visible faces in paint order), `floor_at` (the floor point under a screen
  point, for cast shadows and for where a figure stands). Floor tiles and ceiling grid are projected lines;
  furniture is boxes with a top, a front and a side. Hand-drawn props are placed with
  `translate(screen) scale(cam.scale(point))`. Keep the plate in a generator script, not hand-edited SVG.
  An earlier one-plane `Wall` approximation gave a room that read as frontal, with less perspective than
  the reference: only the back wall converged, the floor lines went to another point, and furniture had no
  depth.
- **Every object gets three things** (a door, a board and the character all looked unfinished without them): a cast shadow on what is behind or under it (the same shape shifted away from
  the light, 0.2 opacity), a light face and a dark face (box sides, a lit top edge, a shade strip under
  any overhang), and its small parts (door panels with a dark top-left and a light bottom-right edge,
  hinges, kick plate, handle with its own shadow, frame screws, chalk dust, a light switch).
- **Volume on the character**: `formShade` on each part group (head, each sleeve, each panel, dress, each
  limb, each prop) gives every part its own lit edge and core shade; `actorLook` on the whole figure adds
  the scene rim. One part's shadow on another is a copy filtered with `sil` and clipped to the shaded
  zone (the hem's shadow across the legs). Add a highlight shape on the largest round form and glints on
  glass.
- **Tapered limbs**: a closed path with an outer and an inner edge that meet in a curled tip, not a stroked
  centreline. The pale underside is a thick stroke along the outer edge clipped to the limb (`clipPath` of
  the same path), then the outline is drawn again on top.
- **S-curve**: shear the torso group about the hem (`translate(0 H) skewX(a) translate(0 -H)`) and tilt the
  head the other way. This is a choice per drawing, never animated.
- **Brush direction**: one cloud noise over everything reads as blotches. Put a streak filter on each
  material instead (`woodV`, `woodH`, `brushV`, `brushH`, `wipeH` in the reference file): turbulence with
  very different x and y frequency, tinted, clipped to the shape's own alpha. Then drop the cloud mottle to
  about 0.3.
- **Light**: two gradient washes on the plate (warm from the light side, cool shade in the far corner), a
  blurred cast shadow pushed away from the light, and `actorLook` on each character: a warm rim on the
  light side and a core shade on the far side. Cut both bands from an eroded copy of the figure, or the rim
  bleaches the outline into a pale halo.
Cost: filters make each frame slower (230 frames: about 20 s without, about 2 min with) and grain raises the
bit rate about sevenfold at the same quality setting. The noise is procedural: it gives texture, not
brush direction.

## Motion rules
- Body action is complete drawings swapped on authored frames. No limb rotation, no path morphing, no
  interpolation between poses. `move` places whole groups rigidly; `r` (rotation) is for rigid props only.
- Positions step with the drawings (`"step": 2` or `3`) when a drawing travels; smooth sliding under held
  drawings reads as skating.
- Within a held phrase add a second complete drawing on the accent (upper body rises, raised arm changes
  shape, a prop opens) rather than leaving only the mouth moving; the first test read as a picture book
  until each phrase had two or three drawings.
- A rigid settle after an in-shot drawing change (drop 9 px, overshoot -3, rest, on twos) gives weight.
- Only what has a reason to move moves. No idle fidget loops.
- Frame 0 is a full picture (no fade-in on the first shot).

## Timeline

```json
{
  "fps": 24, "frames": 240, "size": [1920, 1080], "bg": "#000",
  "switch":  {"hero.pose": [[0, "stand"], [48, "point"]], "hero.mouth": [[0, "closed"]]},
  "move":    {"chalk": {"keys": [{"f": 60, "x": 0, "y": 0}, {"f": 72, "x": 0, "y": 380, "ease": "in"}],
                        "step": 2, "pivot": [900, 400]}},
  "opacity": {"flash": [[0, 0], [99, 0], [100, 1], [104, 0]]},
  "camera":  [{"f": 0, "box": [0, 0, 1920, 1080]}, {"f": 240, "box": [120, 60, 1680, 945], "ease": "inout"}],
  "shake":   [{"f": 100, "len": 12, "amp": 14}],
  "audio":   "mix.wav"
}
```

- `switch`: `[frame, state]`; a state holds until the next key. Every switch in the scene needs a track
  (otherwise all its states would show); unknown names or states stop the render before the first frame.
- `move` keys carry `x`, `y`, `s` (scale about `pivot`), `r` (degrees about `pivot`) and an `ease` for the
  segment that ends on that key: `linear`, `in`, `out`, `inout`, `hold`.
- `camera` boxes are stage-unit view boxes with float precision; keep the stage aspect ratio.
- Identical consecutive states are drawn once, so holds cost nothing.
- `audio` is muxed as given; build the mix separately. Mouth cues from your lip-sync step become
  `hero.mouth` keys.

## Checks before showing anything
- `sheet` every switch and look at each state next to its neighbours: size, ground line, props carried.
- `--stills` at every drawing change and at the first and last frame; read them, then watch the encoded file.
- Zoom each mouth state from the encoded film.
- A test render made this way is a test, not a delivery: review it like any other shot before it goes into a film.

## Using the cels in other renderers
`still --isolate ID` writes one element on the full transparent stage, so every exported state is registered
to the same canvas. Export at a larger `--size` for close-ups instead of scaling a small PNG.
