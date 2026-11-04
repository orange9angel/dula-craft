"""End-to-end test with placeholder drawings and test tones. Needs numpy, pillow, opencv, scipy, ffmpeg.

Everything here is a test fixture only. It exists to prove the pipeline runs, not to look good.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SKILLS = Path(__file__).resolve().parents[1] / "skills"
S = SKILLS / "dula-flat-cel" / "scripts"


def run(script, *args, cwd, ok=True):
    done = subprocess.run([sys.executable, str(S / script), *map(str, args)], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ok and done.returncode:
        raise AssertionError(f"{script} failed:\n{done.stdout}\n{done.stderr}")
    return done


def draw_cel(path, mouth=0, colour=(240, 170, 90)):
    image = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.ellipse((312, 500, 712, 1400), fill=colour, outline=(10, 10, 10), width=8)
    d.ellipse((362, 180, 662, 560), fill=(250, 225, 195), outline=(10, 10, 10), width=8)
    d.ellipse((440, 320, 470, 360), fill=(10, 10, 10))
    d.ellipse((554, 320, 584, 360), fill=(10, 10, 10))
    if mouth:
        d.ellipse((462, 410, 562, 410 + 40 * mouth), fill=(120, 20, 30), outline=(10, 10, 10), width=6)
    else:
        d.line((462, 430, 562, 430), fill=(10, 10, 10), width=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def tone(path, seconds=1.2, sr=48000):
    t = np.arange(int(seconds * sr)) / sr
    # Syllable-like bursts, so the mouth has something to follow.
    y = np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 3 * t) > 0) * 0.5
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((y * 32767).astype(np.int16).tobytes())


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dula-test-"))
        self.film = self.dir / "film"
        run("new_project.py", self.film, cwd=self.dir)
        f = self.film
        draw_cel(f / "assets/cels/hero_stand.png")
        draw_cel(f / "assets/cels/raw/hero_stand_m1.png", mouth=1)
        draw_cel(f / "assets/cels/raw/hero_stand_m2.png", mouth=2)
        (f / "config/variants.tsv").write_text(
            "hero_stand_m1\they_stand\tx\nhero_stand_m2\they_stand\tx\n".replace("hey_stand", "hero_stand"),
            encoding="utf-8")
        Image.new("RGB", (1536, 1024), (150, 190, 220)).save(f / "assets/plates/room.png")
        tone(f / "audio/voice/l01.wav")
        film = json.loads((f / "config/film.json").read_text(encoding="utf-8"))
        film["lines"][0]["text"] = "test"
        (f / "config/film.json").write_text(json.dumps(film), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_full_pipeline(self):
        f = self.film
        run("prep_cels.py", cwd=f)
        for name in ("hero_stand", "hero_stand_m1", "hero_stand_m2"):
            self.assertTrue((f / f"assets/flat/{name}.png").exists(), name)

        # Outside the mouth a variant must be pixel-identical to its base, or fills flicker.
        base = np.array(Image.open(f / "assets/flat/hero_stand.png"))
        variant = np.array(Image.open(f / "assets/flat/hero_stand_m2.png"))
        ys, _ = np.nonzero((base != variant).any(2))
        self.assertTrue(len(ys), "the variant must differ somewhere")
        self.assertGreater(ys.min(), 300)
        self.assertLess(ys.max(), 600)

        run("build_film.py", cwd=f)
        run("render.py", "--stills", "0.1,0.5", cwd=f)
        self.assertEqual(len(list((f / "build/stills").glob("*.png"))), 2)
        run("render.py", cwd=f)
        out = f / "output/film.mp4"
        self.assertTrue(out.exists())
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", str(out)],
            capture_output=True, text=True, check=True)
        streams = json.loads(probe.stdout)["streams"]
        self.assertEqual({s["codec_type"] for s in streams}, {"video", "audio"})
        self.assertEqual(next(s for s in streams if s["codec_type"] == "video")["width"], 1440)
        done = run("check_mouths.py", cwd=f)
        self.assertIn("Frozen mouths: 0", done.stdout)

        # The cel shown must really change while the line plays.
        shown = {s["cel"] for frame in json.loads((f / "build/displayed.json").read_text(encoding="utf-8"))
                 for s in frame["shown"]}
        self.assertGreater(len(shown), 1)

    def test_frozen_mouth_is_refused(self):
        f = self.film
        (f / "config/variants.tsv").write_text("", encoding="utf-8")
        run("prep_cels.py", cwd=f)
        done = run("build_film.py", cwd=f, ok=False)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Frozen mouth", done.stdout + done.stderr)

    def test_missing_voice_is_refused_and_placeholder_is_allowed(self):
        f = self.film
        run("prep_cels.py", cwd=f)
        (f / "audio/voice/l01.wav").unlink()
        done = run("build_film.py", cwd=f, ok=False)
        self.assertNotEqual(done.returncode, 0)
        film = json.loads((f / "config/film.json").read_text(encoding="utf-8"))
        film["lines"][0]["seconds"] = 1.0
        (f / "config/film.json").write_text(json.dumps(film), encoding="utf-8")
        run("build_film.py", cwd=f)
        run("render.py", cwd=f)
        self.assertTrue((f / "output/film.mp4").exists())

    def test_cycle_uses_one_scale(self):
        f = self.film
        draw_cel(f / "assets/cels/hero_b.png", colour=(90, 170, 240))
        (f / "config/variants.tsv").write_text("", encoding="utf-8")
        run("prep_cels.py", cwd=f)
        film = json.loads((f / "config/film.json").read_text(encoding="utf-8"))
        film["lines"] = []
        film["shots"][0].update(lines=[], seconds=1)
        film["shots"][0]["actors"][0].update(cels=["hero_stand", "hero_b"], align_head=True)
        (f / "config/film.json").write_text(json.dumps(film), encoding="utf-8")
        run("build_film.py", cwd=f)
        actor = json.loads((f / "build/sheet.json").read_text(encoding="utf-8"))["shots"][0]["actors"][0]
        self.assertEqual(actor["offs"]["hero_b"], [0.0, 0.0])


class FakeService(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeService.requests.append((self.headers.get("X-Api-Key"), body))
        with tempfile.TemporaryDirectory() as d:
            tone(Path(d) / "a.wav")
            audio = base64.b64encode((Path(d) / "a.wav").read_bytes()).decode()
        data = json.dumps({"code": 20000000, "audio": audio, "original_duration": 1.2}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class Voice(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dula-voice-"))
        self.home = self.dir / "home"
        self.film = self.dir / "film"
        run("new_project.py", self.film, cwd=self.dir)
        film = {"voices": {"a": {"desc": "clear"}}, "lines": [
            {"id": "l1", "who": "a", "text": "first"}, {"id": "l2", "who": "a", "text": "second"}]}
        (self.film / "config/film.json").write_text(json.dumps(film), encoding="utf-8")
        self.server = HTTPServer(("127.0.0.1", 0), FakeService)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        FakeService.requests.clear()
        self.env = {**os.environ, "DULA_CRAFT_HOME": str(self.home),
                    "DULA_SEED_AUDIO_URL": f"http://127.0.0.1:{self.server.server_port}/"}
        self.env.pop("VOLC_SPEECH_API_KEY", None)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def tool(self, path, *args, stdin=None, cwd=None):
        return subprocess.run([sys.executable, str(SKILLS / path), *args], cwd=cwd or self.dir, env=self.env, input=stdin,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def speak(self, *args):
        return self.tool("dula-voice/scripts/speak.py", *args, cwd=self.film)

    def test_missing_key_is_explained_and_spends_nothing(self):
        done = self.speak()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("configure.py", done.stderr)
        self.assertEqual(FakeService.requests, [])

    def test_key_is_saved_privately_and_never_shown(self):
        saved = "unit-test-value-123456"
        conf = "dula-start/scripts/configure.py"
        self.assertEqual(self.tool(conf, "--stdin", stdin=saved + "\n").returncode, 0)
        status = self.tool(conf, "--status")
        self.assertIn("Voice key: set", status.stdout)
        self.assertNotIn(saved, status.stdout + status.stderr)
        if os.name != "nt":
            self.assertEqual((self.home / "config.env").stat().st_mode & 0o077, 0)

        done = self.speak()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(saved, done.stdout + done.stderr)
        self.assertEqual(len(FakeService.requests), 2)
        self.assertEqual(FakeService.requests[0][0], saved)
        for record in (self.film / "audio/voice").glob("*.json"):
            self.assertNotIn(saved, record.read_text(encoding="utf-8"))

        # The first line carries the voice for the rest.
        first, second = FakeService.requests[0][1], FakeService.requests[1][1]
        self.assertNotIn("references", first)
        self.assertIn("audio_data", second["references"][0])
        self.assertIn("second", second["text_prompt"])

        # A rerun with nothing changed costs nothing.
        self.speak()
        self.assertEqual(len(FakeService.requests), 2)

        film = json.loads((self.film / "config/film.json").read_text(encoding="utf-8"))
        film["lines"][1]["text"] = "changed"
        (self.film / "config/film.json").write_text(json.dumps(film), encoding="utf-8")
        self.speak()
        self.assertEqual(len(FakeService.requests), 3)

        self.tool(conf, "--remove")
        self.assertIn("not set", self.tool(conf, "--status").stdout)

    def test_dry_run_sends_nothing(self):
        done = self.speak("--dry-run")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("first", done.stdout)
        self.assertEqual(FakeService.requests, [])


class Others(unittest.TestCase):
    def test_subtitles(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "s.json").write_text(json.dumps({"events": [
                {"start": 0.1, "end": 1, "speaker": "A", "text": "Hello", "translation": "Bonjour"}]}), encoding="utf-8")
            done = subprocess.run([sys.executable, str(SKILLS / "dula-subtitles/scripts/make_subs.py"),
                                   "--events", str(d / "s.json"), "--ass-out", str(d / "s.ass")], capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            ass = (d / "s.ass").read_text(encoding="utf-8")
            self.assertIn("Hello", ass)
            self.assertIn("Bonjour", ass)

    def test_title_card(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            font = next((p for p in ("C:/Windows/Fonts/STKAITI.TTF", "C:/Windows/Fonts/simkai.ttf",
                                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if Path(p).exists()), None)
            if not font:
                self.skipTest("no font on this machine")
            Image.new("RGB", (1280, 720), (40, 60, 80)).save(d / "bg.png")
            done = subprocess.run([sys.executable, str(SKILLS / "dula-title-card/scripts/make_title_card.py"),
                                   "--bg", str(d / "bg.png"), "--title", "AB", "--subtitle", "c", "--font", font,
                                   "--duration", "0.5", "--out-dir", str(d / "out")], capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(len(list((d / "out").glob("f_*.png"))), 12)


if __name__ == "__main__":
    unittest.main()
