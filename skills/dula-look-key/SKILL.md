---
name: dula-look-key
description: Make an approved look key (an integrated frame of characters inside their location) before flat 2D production, then derive empty plates, native closer plates, key-referenced cels and integrated contact shots from it, so backgrounds and characters fuse like frames of one film. Use when a film has no reference footage, when characters look pasted on or sharp against a blurry background, or when characters must sit on, lean on or touch furniture.
---

# Look key: a self-made reference film

Talk to the person in their language. A film made from separately generated plates and
cut-out characters only fuses when both share one design source. With reference footage,
plates and characters copy the same frames. An original film has none, so create that
source first: one approved frame per location in which the characters already inhabit the
room. Everything else derives from it.

## Why this exists

- Plates painted from a text-only style description, zoomed 2.4-3.9x for close shots, with
  sofa, desk and radio contacts staged as cut-outs, gave sharp characters on a blurry, busier
  background and wrong physical relationships.
- A living-room key of the same film, then a plate derived by erasing its characters, fused
  old and new cut-outs at once. The derived plate did most of the work.

## Workflow

1. **Identity anchors first.** Approve each character's reference drawing (the
   [dula-flat-cel](../dula-flat-cel/SKILL.md) design step). Specify character finish and background
   finish separately. Flat cel characters can inhabit a restrained hand-painted setting
   with material, coherent perspective, useful furniture and contact/cast shadows.
   Do not expand "flat characters" into a blanket ban on background tonal variation.
   Match their visual density and clarity at the actual camera distance, without blur.
   Use all-flat plates only when that is the chosen film direction. Avoid generic round
   eyes, perfectly symmetric poses and decorative architecture as substitutes for appeal.
2. **Location key.** One empty layout plate per location, then a key: the layout plate as
   image 1 and the anchors as later images, all main characters placed with real contact
   (seated weight, dented cushion, feet on floor, contact shadows). `lookkey.py key`.
   Show the key to the person; it is the film's look gate. Keep rejected keys.
3. **Derived plates.** `lookkey.py erase` removes the characters from the approved key,
   restoring hidden sofa and floor. Compare key and plate; the changed area should be the
   characters and their shadows, not the room. `lookkey.py closer` paints the same place
   from a nearer camera for medium and close shots, referencing the key.
4. **Cels.** Paint poses with the anchor first and the location key second (`lookkey.py cel`),
   so line weight and palette follow the key. Identity remains the anchor's job.
5. **Contact shots.** Sitting in furniture, typing on a desk, sitting on a prop, lying on a
   floor, standing behind a desk: generate the whole frame as an integrated key and make
   mouth and eye variants as local edits of that frame. Cut-outs on a derived plate are for
   figures standing or walking on open floor.
   The edit model also shifts skin tone, which flickers when states swap: lock each edit back
   to the original (colour-fit on unchanged pixels, one shared zone grown from the widest
   mouth state, fully opaque inside, nothing changed outside), leave room below a closed mouth
   for the dropped jaw, and review every mouth state zoomed in the encoded film.
6. **Checks before rendering.** `lookkey.py check film.json` reports plate zoom per shot
   (limit 2.0x of a wide fit unless a native closer plate exists) and style statistics of
   plates and cels against the key (edge density, saturation, flat-area texture). Numbers
   flag drift; still review a full frame and native contact crops for support surface,
   occlusion, shadow and eyeline, and record what you saw.

## Lock every same-camera frame to one base

Every integrated frame is a fresh painting, so brick, rust, posters and paving re-render between
two drawings of one camera; 10-40% of the frame changed at each pose swap in one test, and
viewers notice at once. After painting a same-camera group, run `scripts/lock_frames.py BASE VAR...`
(originals kept in `assets/keys/unlocked/`, masks in `build/lock/`): only the character region keeps
the variant's pixels. Prefer an empty plate as BASE. Do not warp variants (mouth patches are cut
from the unwarped frame). Small expression edits need `--min-area 0.0002`. Measure swaps in the
encoded film afterwards; the same test fell to 1-4% per swap.

Populate wide shots without cutting them: paint two drawings of the same townsfolk in a two-beat
loop, lock both to the empty base, then `scripts/make_layer.py BASE A B` makes full-frame
transparent layers that alternate as one actor over the plate, so a walking cut-out on top keeps
its continuous move.

## Rules

- No new plate set before its location key is approved. Do not reuse the key for a
  different location; make one per place.
- Never zoom a plate to fake a close shot. Paint the closer camera.
- A plate for a travel shot is ordered for the drawings you have: with side-on character drawings, ask for the road,
  path or track to run straight across the frame. A road that curves away or recedes toward a vanishing point needs
  back or three-quarter drawings of the traveller; otherwise use it only as an empty establishing image.
- A wide-fit zoom statistic is not enough: measure the raster actually sampled after atlas
  extraction, earlier downsampling and local cropping. A 195x110 crop shown at 1280x720 is
  about 6.6x, even inside a large source atlas. Reject missing native detail before encoding,
  then inspect the encoded film at 100%. A registration or codec pass does not clear blur.
- A key or derived plate replaces nothing the person rejected; keep the originals and record
  their words in the film's notes.
- Verify defining geometry before propagating a key. If frontal shading makes a feature
  ambiguous, inspect a non-frontal view: a projecting solid horn, a recessed slot and an open
  aperture are different structures even when all contain dark regions. Compare silhouette,
  base attachment, tip and occlusion; a palette match does not establish anatomy. Correct the
  key and every derived pose after such an error.
- Keys come from the film's own approved anchors. Do not use third-party footage or
  franchise frames as keys for an original film.
- When a generated wide drawing reads as a different film, compare the lit paper around the
  face, shadow grouping in the hair, broken contours and the moving background against the
  accepted close-up at playback size. A detail insert derived from the same key may serve
  the cut better.
- At a handoff between a held shot and a separately animated vehicle, carry the camera origin
  and scale across the boundary; compare stationary landmarks on the last and first frames.
