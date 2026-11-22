"""Smoke tests for the story, look, light, action, SVG and director skills. Needs numpy, pillow, opencv, ffmpeg.

Inputs are synthetic fixtures. The SVG test is skipped when Playwright or a browser is not installed; the cold
reader is tested with a stand-in command instead of a real model.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SKILLS = Path(__file__).resolve().parents[1] / "skills"


def script(skill, name):
    return SKILLS / skill / "scripts" / name


def load(path, mode=None):
    with Image.open(path) as im:
        return np.asarray(im.convert(mode) if mode else im).copy()


def run(path, *args, cwd=None, ok=True):
    done = subprocess.run([sys.executable, str(path), *map(str, args)], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if ok and done.returncode:
        raise AssertionError(f"{path.name} failed:\n{done.stdout}\n{done.stderr}")
    return done


class Help(unittest.TestCase):
    def test_entry_points_print_help(self):
        for skill, name in [("dula-director-pass", "review_tile.py"), ("dula-story-design", "blind_pitch.py"),
                            ("dula-look-key", "lookkey.py"), ("dula-look-key", "lock_frames.py"),
                            ("dula-look-key", "make_layer.py"), ("dula-action-staging", "stage.py"),
                            ("dula-flat-cinema", "light_cels.py"), ("dula-flat-cinema", "render_fx.py"),
                            ("dula-svg-cel", "svgcel.py")]:
            with self.subTest(script=name):
                done = run(script(skill, name), "--help")
                self.assertGreater(len(done.stdout.strip()), 40)

    def test_every_skill_has_frontmatter_with_prefix(self):
        for d in SKILLS.iterdir():
            if not (d / "SKILL.md").exists():
                continue
            head = (d / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
            self.assertIn(f"name: {d.name}", head)
            self.assertTrue(d.name.startswith("dula-"))
            for link in __import__("re").findall(r"\]\((\.\./[^)#]+)", (d / "SKILL.md").read_text(encoding="utf-8")):
                self.assertTrue((d / link).resolve().exists(), f"{d.name}: broken link {link}")


class DirectorTile(unittest.TestCase):
    def test_tile_from_test_video(self):
        with tempfile.TemporaryDirectory() as td:
            v = Path(td) / "film.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=6",
                            "-pix_fmt", "yuv420p", str(v)], check=True)
            sec = Path(td) / "sections.json"
            sec.write_text(json.dumps({"sections": [{"t0": 0, "t1": 3, "part": "intro"},
                                                    {"t0": 3, "t1": 6, "part": "verse"}]}), encoding="utf-8")
            run(script("dula-director-pass", "review_tile.py"), v, "--every", 2, "--sections", sec, "--cols", 3)
            with Image.open(Path(td) / "film_tile.png") as tile:
                self.assertEqual(tile.size, (960, 196))


class LockFrames(unittest.TestCase):
    def test_only_the_changed_region_survives(self):
        with tempfile.TemporaryDirectory() as td:
            keys = Path(td) / "assets" / "keys"
            keys.mkdir(parents=True)
            (Path(td) / "assets" / "flat").mkdir()
            rng = np.random.default_rng(1)
            base = (rng.random((360, 640, 3)) * 60 + 100).astype(np.uint8)
            var = np.clip(base.astype(int) + rng.integers(-6, 7, base.shape), 0, 255).astype(np.uint8)  # "boiling"
            var[120:260, 260:380] = (30, 40, 200)  # the character really changed here
            Image.fromarray(base).save(keys / "base.png")
            Image.fromarray(var).save(keys / "pose.png")
            run(script("dula-look-key", "lock_frames.py"), "base", "pose", cwd=td)
            locked = load(keys / "pose.png", "RGB")
            self.assertTrue(np.array_equal(locked[:60, :200], base[:60, :200]), "background should be the base")
            self.assertLess(np.abs(locked[180, 320].astype(int) - (30, 40, 200)).max(), 8, "change should be kept")
            run(script("dula-look-key", "make_layer.py"), "base", "pose", cwd=td)
            layer = load(Path(td) / "assets" / "flat" / "pose_L.png")
            self.assertEqual(layer.shape[2], 4)
            self.assertGreater(layer[180, 320, 3], 200)
            self.assertEqual(layer[60, 100, 3], 0)


class ColdRead(unittest.TestCase):
    def test_prompt_reaches_the_reader(self):
        with tempfile.TemporaryDirectory() as td:
            echo = Path(td) / "echo.py"
            echo.write_text("import sys\nt = sys.stdin.read()\nprint('READ', len(t), 'Hook' in t, 'Dutch' in t)\n",
                            encoding="utf-8")
            pitches = Path(td) / "pitches.md"
            pitches.write_text("## One\nHook: a\nTurn: b\nEnding: c\n", encoding="utf-8")
            cmd = f'"{sys.executable}" "{echo}"'
            run(script("dula-story-design", "blind_pitch.py"), pitches, "--lang", "Dutch", "--cmd", cmd)
            out = (Path(td) / "pitches_pitch_coldread.md").read_text(encoding="utf-8")
            self.assertIn("READ", out)
            self.assertIn("True True", out)


class ActionStaging(unittest.TestCase):
    def test_two_beat_move_renders(self):
        with tempfile.TemporaryDirectory() as td:
            img = Image.new("RGB", (320, 240), (40, 40, 60))
            d = ImageDraw.Draw(img)
            d.ellipse((120, 60, 200, 180), fill=(230, 60, 40))
            img.save(Path(td) / "k1.png")
            sheet = {"fps": 24, "size": [320, 240], "beats": [
                {"image": "k1.png", "frames": 6, "push": [1.0, 1.05], "lines": {"center": [0.5, 0.5], "count": 20}},
                {"image": "k1.png", "frames": 4, "impact": {"dark": [10, 0, 0], "light": [230, 20, 20],
                                                            "threshold": 100}, "shake": {"amp": 6}}]}
            (Path(td) / "move.json").write_text(json.dumps(sheet), encoding="utf-8")
            run(script("dula-action-staging", "stage.py"), Path(td) / "move.json", "-o", Path(td) / "clip.mp4")
            n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v",
                                "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(Path(td) / "clip.mp4")],
                               capture_output=True, text=True).stdout.strip()
            self.assertEqual(int(n), 10)


class Perspective(unittest.TestCase):
    def test_camera_projects_consistently(self):
        sys.path.insert(0, str(SKILLS / "dula-svg-cel" / "scripts"))
        from persp import Camera
        cam = Camera()
        near, far = cam.scale(800, 0, 400), cam.scale(800, 0, -400)
        self.assertGreater(near, far, "nearer points must be drawn larger")
        x, y = cam.xy(800, 0, 0)
        fx, fz = cam.floor_at(x, y)
        self.assertAlmostEqual(fx, 800, delta=1)
        self.assertAlmostEqual(fz, 0, delta=1)


class SvgCel(unittest.TestCase):
    def test_switch_states_render(self):
        try:
            import playwright  # noqa: F401
        except ImportError:
            self.skipTest("Playwright is not installed")
        with tempfile.TemporaryDirectory() as td:
            svg = Path(td) / "scene.svg"
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180">'
                           '<rect width="320" height="180" fill="#223"/><g id="hero"><g data-switch="hero.pose">'
                           '<g data-state="a"><circle cx="100" cy="90" r="40" fill="#e43"/></g>'
                           '<g data-state="b"><circle cx="220" cy="90" r="40" fill="#e43"/></g></g></g></svg>',
                           encoding="utf-8")
            done = run(script("dula-svg-cel", "svgcel.py"), "states", svg, ok=False)
            if done.returncode:
                self.skipTest("no browser for Playwright: " + done.stderr[-200:])
            self.assertIn("hero.pose", done.stdout)
            out = Path(td) / "b.png"
            run(script("dula-svg-cel", "svgcel.py"), "still", svg, "-o", out, "--set", "hero.pose=b", "--size", "320x180")
            px = load(out, "RGB")
            self.assertGreater(px[90, 220, 0], 180)
            self.assertLess(px[90, 100, 0], 100)


if __name__ == "__main__":
    unittest.main()
