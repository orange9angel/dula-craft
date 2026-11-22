---
name: dula-action-staging
description: Stage anime-style special moves and action climaxes (stance hold, charge, named-technique shout, release, impact frame, aftermath) from a few approved key drawings with code effects - camera push and shake, flash, colour bloom, radiating speed lines, cosmic or flat backgrounds, silhouette aura, afterimages, two-colour impact frames - and reuse the result as a bank sequence. Use for fights, transformations and special moves in flat 2D cel films.
---

# Action staging (technique sequences)

Talk to the person in their language. The bar is the limited-animation staging of classic TV action series:
held key drawings made dramatic by camera, light and effects, not feature-film full animation.
Never warp a drawing: rigid placement, camera and overlays only. Every beat holds one
approved key drawing; motion between keys comes from 3-5 drawn poses, not interpolation.

```bash
python scripts/stage.py move.json -o clip.mp4 [--frames-dir DIR]
```

The beat-sheet schema is in the script docstring. Paths in the JSON are relative to the JSON file.

## The standard technique rhythm (24 fps)

| Beat | Length | Picture | Effects |
|---|---|---|---|
| 1 Stance | 24-48 f | stance or glare drawing | slow push 1.0 -> 1.08, bloom pulse on the glow colour |
| 2 Charge | 24-36 f | same or charge drawing (transparent cel) | background swap (cosmos/solid), aura on the cel, speed lines |
| 3 Name | 18-30 f | extreme close of the face | push in, bloom; voice line = the technique name |
| 4 Release | 2-4 drawings x 2-3 f | release poses | afterimage on a transparent cel, speed lines, shake |
| 5 Black beat | 6-12 f | black | silence in the mix |
| 6 Impact | 8-16 f | impact drawing | impact (two colours), radial lines over it, flash 2 f, decaying shake |
| 7 Aftermath | 36-72 f | wide result | slow pull or hold, particles from the film renderer |

Rules learned on the first test:
- Speed lines go behind a transparent cel and on top of an opaque frame (the script does this).
- Impact frames: a median filter before the threshold avoids grain; choose the threshold per drawing
  (90-120) and inspect the frame.
- Effects that are deliberate (afterimage, flash) are fine; accidental ghosting between key drawings is not.
- A finished move is a bank: keep its JSON and drawings; later episodes re-render it with new background colours.

## Checks before showing anyone
Extract frames at the beat boundaries and inspect them; confirm the glow colour and left/right of the glowing eye
match the character sheet; listen to the black beat (true silence) and the hit sound on the impact frame.
