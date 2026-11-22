---
name: dula-flat-cinema
description: "Give flat 2D cel films a cinematic look in flat language: scene-lit characters (ambient colour, hard rim on the light side, flat cast and contact shadows), floor light pools, light beams, drifting dust, lamp glow, foreground parallax layers and per-film signature effects, all in code on top of the dula-flat-cel renderer. Use when characters look pasted on a background, a scene needs mood from light, or a shot needs life without character motion."
---

# Flat cinema

Talk to the person in their language. This skill keeps flat cels and builds a cinematic style in
flat language, instead of switching to a painterly look. The three problems it answers:

1. **Characters pasted on the background.** Light the drawing with the scene: `light_cels.py`.
2. **Weak character motion.** Let the environment move: dust, flicker, beams, parallax layers,
   slow camera; keep characters still or nearly still in the mood shots.
3. **Shading consistency.** Never paint light into each drawing. Light is computed from the
   silhouette, so every pose and every mouth/blink state of a drawing gets identical light.

Style rule: light, shadow and air are **hard-edged flat shapes** like the drawings (bands, pools,
polygons, dots). The only soft element is a lamp or sun glow. No gradients across characters.

## Lit cels

`scripts/light_cels.py --rigs config/lights.json --all-used config/film.json` writes
`assets/flat/<cel>@<rig>.png` for every `name@rig` that film.json uses (all states of the drawing).
A rig sets `ambient` (multiply), `rim` (direction towards the light, colour, width, opacity) and
`shadow` (flat cast shadow on the floor plus a contact ellipse). One rig per lighting situation,
not per shot. Outlines are never painted over.

Measured on a night office scene: ambient alone removed most of the pasted look; the rim reads at
close and medium sizes and vanishes in wides; cast shadows anchor feet.

## Atmosphere

`scripts/render_fx.py` replaces render.py (same sheet, audit log and audio) and draws
`config/fx.json` effects per shot id: `shafts`, `dust`, `glow`, `misprint`, `layer`, `vignette`,
`grade`. `"under": true` draws an effect between the plate and the actors (floor light pools,
ground fog); everything else goes on top. Everything moves on twos.

Lessons from the first test:
- Place glows and beams from the lamp positions measured in the rendered frame, not guessed.
  Plate scale and pan move them.
- Wide beams at 0.10 opacity turned the whole frame grey and flatter than no effect. Beams stay
  narrow and at about 0.04-0.06; pools on the floor carry most of the light.
- Floor pools on top of actors cut across legs: use `under`.
- A whole-frame `grade` changes an accepted palette: show a side-by-side sample before using it.

## Checks

Render a still with and without fx (`--no-fx`) and compare side by side; look at contact crops
(feet, rims) at native size; measure flicker in a test clip (lamp region frame-to-frame change).
Effects that make the frame greyer or busier than the plain one are removed, not kept for effort.
