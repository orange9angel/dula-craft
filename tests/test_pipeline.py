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


def run(script, *args, cwd, ok=True, env=None):
    done = subprocess.run([sys.executable, str(S / script), *map(str, args)], cwd=cwd, env=env,
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


class Features(unittest.TestCase):
    """What a first full film showed was missing."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dula-features-"))
        self.film = f = self.dir / "film"
        run("new_project.py", f, cwd=self.dir)
        draw_cel(f / "assets/flat/hero_a.png")
        draw_cel(f / "assets/flat/hero_a_m1.png", mouth=1)
        draw_cel(f / "assets/flat/hero_a_m2.png", mouth=2)
        draw_cel(f / "assets/flat/hero_b.png", colour=(90, 170, 240))
        Image.new("RGB", (1536, 1024), (150, 190, 220)).save(f / "assets/plates/room.png")
        tone(f / "audio/voice/l1.wav")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def build(self, shot, lines=(), **top):
        film = {"plates": {"room": "assets/plates/room.png"}, "lines": list(lines),
                "shots": [{"id": "S1", "plate": {"key": "room"}, **shot}], **top}
        (self.film / "config/film.json").write_text(json.dumps(film), encoding="utf-8")
        run("build_film.py", cwd=self.film)

    def still(self, t):
        run("render.py", "--stills", t, cwd=self.film)
        return np.array(Image.open(self.film / f"build/stills/t{float(t):07.2f}.png")).astype(int)

    def displayed(self):
        run("render.py", cwd=self.film)
        return json.loads((self.film / "build/displayed.json").read_text(encoding="utf-8"))

    def test_a_move_with_no_times_lasts_the_whole_shot(self):
        self.build({"seconds": 2, "actors": [{"cels": ["hero_a"], "cx": [200, 1200], "ground": 1000, "height": 500}]})
        changed = np.abs(self.still(0) - self.still(1.5)).mean()
        self.assertGreater(changed, 1)

    def test_an_actor_can_hold_longer_than_the_shot(self):
        self.build({"seconds": 1, "hold": 2, "actors": [
            {"cels": ["hero_a", "hero_b"], "cx": 720, "ground": 1000, "height": 500, "hold": 12}]})
        cels = [frame["shown"][0]["cel"] for frame in self.displayed()]
        self.assertEqual(cels[:12], ["hero_a"] * 12)
        self.assertEqual(cels[12:24], ["hero_b"] * 12)

    def test_a_cycle_without_mouths_is_refused(self):
        line = {"id": "l1", "who": "hero", "text": "x"}
        film = {"plates": {"room": "assets/plates/room.png"}, "lines": [line], "shots": [{
            "id": "S1", "plate": {"key": "room"}, "lines": ["l1"],
            "actors": [{"who": "hero", "cels": ["hero_b", "hero_b"], "cx": 720, "ground": 1000, "height": 500}]}]}
        (self.film / "config/film.json").write_text(json.dumps(film), encoding="utf-8")
        done = run("build_film.py", cwd=self.film, ok=False)
        self.assertNotEqual(done.returncode, 0)

    def test_mouth_check_ignores_body_swaps_and_off_frame_actors(self):
        line = {"id": "l1", "who": "hero", "text": "x", "mouth_ok": "testing the render-time check"}
        self.build({"lines": ["l1"], "actors": [
            {"who": "hero", "cels": ["hero_b", "hero_a"], "cx": 720, "ground": 1000, "height": 500,
             "talk": {"hero_a": ["hero_a", "hero_a", "hero_a"], "hero_b": ["hero_b", "hero_b", "hero_b"]}}]}, [line])
        self.displayed()
        done = run("check_mouths.py", cwd=self.film, ok=False)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("FROZEN MOUTH", done.stdout)

        self.build({"lines": ["l1"], "actors": [
            {"who": "hero", "cels": ["hero_a"], "cx": 9000, "ground": 1000, "height": 500}]}, [line])
        self.displayed()
        self.assertIn("off screen", run("check_mouths.py", cwd=self.film).stdout)

    def test_fades_reach_black_and_silence(self):
        self.build({"lines": ["l1"], "fade_in": 0.5, "fade_out": 0.5, "actors": []},
                   [{"id": "l1", "who": "nobody", "text": "x"}])
        self.assertLess(self.still(0).mean(), 2)
        self.assertGreater(self.still(0.7).mean(), 50)
        with wave.open(str(self.film / "build/mix.wav")) as f:
            pcm = np.frombuffer(f.readframes(f.getnframes()), np.int16)
        self.assertEqual(int(np.abs(pcm[-200:]).max()), 0)

    def test_an_overlay_fills_the_frame(self):
        layer = Image.new("RGBA", (720, 540), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle((300, 200, 310, 210), fill=(255, 255, 255, 255))
        layer.save(self.film / "assets/flat/rain.png")
        self.build({"seconds": 1, "actors": [{"overlay": True, "cels": ["rain"]}]})
        actor = json.loads((self.film / "build/sheet.json").read_text(encoding="utf-8"))["shots"][0]["actors"][0]
        self.assertEqual((actor["x"][0], actor["y"][0], actor["h"]), (720, 1080, 1080))

    def test_ambience_level_can_be_raised(self):
        path = self.film / "audio/sfx/rain.wav"
        tone(path, seconds=3)

        def loudness(ambience):
            self.build({"seconds": 2, "ambience": "rain", "actors": []}, ambience={"rain": ambience})
            with wave.open(str(self.film / "build/mix.wav")) as f:
                pcm = np.frombuffer(f.readframes(f.getnframes()), np.int16) / 32768
            return 20 * np.log10(np.sqrt((pcm ** 2).mean()) + 1e-9)

        quiet = loudness("audio/sfx/rain.wav")
        raised = loudness({"file": "audio/sfx/rain.wav", "level_db": -30})
        self.assertLess(quiet, -40)
        self.assertGreater(raised, -35)

    def test_paint_lists_follow_references_without_codex(self):
        f = self.film
        draw_cel(f / "assets/anchors/hero.png")
        draw_cel(f / "assets/cels/hero_run_a.png")
        (f / "config/cels.tsv").write_text("hero_run_b\thero\tnext step\thero_run_a\n", encoding="utf-8")
        Image.new("RGB", (64, 64)).save(f / "assets/plates/day.png")
        (f / "config/plates.tsv").write_text("dusk\tat dusk\tday\n", encoding="utf-8")
        env = {**os.environ, "PATH": str(self.dir)}
        run("paint.py", "cels", "config/cels.tsv", cwd=f, env=env)
        run("paint.py", "plates", "config/plates.tsv", cwd=f, env=env)
        todo = (f / "build/images_todo.md").read_text(encoding="utf-8")
        self.assertIn("assets/anchors/hero.png, assets/cels/hero_run_a.png", todo)
        self.assertIn("assets/plates/day.png", todo)
        self.assertNotEqual(run("paint.py", "cels", "config/cels.tsv", "--force", cwd=f, env=env, ok=False).returncode, 0)

    def test_bases_can_be_checked_before_variants(self):
        f = self.film
        draw_cel(f / "assets/cels/hero_c.png")
        (f / "config/variants.tsv").write_text("hero_c_m1\thero_c\tx\n", encoding="utf-8")
        run("prep_cels.py", "--bases-only", cwd=f)
        self.assertTrue((f / "build/check_alpha.png").exists())

    def test_voice_placeholder_spends_nothing(self):
        d = self.dir / "fresh"
        run("new_project.py", d, cwd=self.dir)
        env = {**os.environ, "VOLC_SPEECH_API_KEY": "x"}
        done = subprocess.run([sys.executable, str(SKILLS / "dula-voice/scripts/speak.py")], cwd=d, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("placeholder", done.stderr)


class Example(unittest.TestCase):
    """The tutorial's example must keep working, even though its images aren't stored."""

    ROOT = Path(__file__).resolve().parents[1] / "examples/rainy-slide"

    def test_every_name_in_the_shot_list_is_defined(self):
        film = json.loads((self.ROOT / "config/film.json").read_text(encoding="utf-8"))

        def names(table):
            rows = (self.ROOT / "config" / table).read_text(encoding="utf-8").splitlines()
            return [row.split("\t") for row in rows if row.strip()]

        drawings = {row[0] for row in names("cels.tsv")} | {row[0] for row in names("variants.tsv")}
        drawings |= {"rain_a", "rain_b", "rain_c"}
        plates = {row[0] for row in names("plates.tsv")}
        lines = {line["id"] for line in film["lines"]}
        whos = {row[0] for row in names("anchors.tsv")}
        self.assertEqual(set(film["voices"]), whos)
        for row in names("cels.tsv"):
            self.assertIn(row[1], whos)
            if len(row) > 3:
                self.assertIn(row[3], drawings)
        for shot in film["shots"]:
            self.assertIn(shot["plate"]["key"], plates)
            self.assertLessEqual(set(shot.get("lines", [])), lines)
            for actor in shot["actors"]:
                self.assertLessEqual(set(actor["cels"]), drawings)

    def test_rain_layers_are_transparent_and_full_frame(self):
        with tempfile.TemporaryDirectory() as d:
            run("new_project.py", Path(d) / "film", cwd=d)
            run("make_rain.py", cwd=Path(d) / "film")
            with Image.open(Path(d) / "film/assets/flat/rain_a.png") as image:
                self.assertEqual(image.size, (1440, 1080))
                alpha = np.array(image.getchannel("A"))
            self.assertGreater((alpha == 0).mean(), 0.5)
            self.assertGreater(alpha.max(), 60)


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
