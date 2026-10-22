"""Stage runner with per-day workdir, checkpoints (resume), retries and cost cap."""
import datetime as dt
import logging
from pathlib import Path

from . import edit, instagram, music, notify, script_stage, visuals, voice, youtube
from .config import ROOT
from .util import Budget, read_json, retry, write_json

log = logging.getLogger("agent")


class Run:
    def __init__(self, cfg, day=None, dry_run=False, force=False):
        self.cfg, self.dry_run = cfg, dry_run
        self.day = day or dt.date.today().isoformat()
        self.dir = ROOT / cfg["work_dir"] / self.day
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / "state.json"
        self.state = {} if force else read_json(self.state_file, {})
        self.budget = Budget(cfg["budget"]["max_usd_per_video"])

    # ---- stages: each takes the run and returns a JSON-serialisable result ----
    def s_script(self):
        return script_stage.make_script(self.cfg, self.budget)

    def s_scenes(self):
        sc = self.state["script"]
        return [visuals.scene_prompt(self.cfg, sc, s) for s in sc["scenes"]]

    def s_images(self):
        return visuals.generate_images(self.cfg, self.budget, self.state["script"], self.dir)

    def s_voice(self):
        v = voice.generate_voice(self.cfg, self.budget, self.state["script"], self.dir)
        voice.write_srt(v["cues"], self.dir / "subs.srt")
        return v

    def s_music(self):
        sc = self.state["script"]
        m = music.pick_music(self.cfg, sc, seed=hash(self.day) & 0xFFFF)
        return {"music": str(m) if m else None,
                "sfx": [[i, str(p)] for i, p in music.pick_sfx(self.cfg, sc)]}

    def s_edit(self):
        mu = self.state["music"]
        out = self.dir / "final.mp4"
        edit.build_video(self.cfg, self.state["images"], self.state["voice"], self.dir, mu["music"],
                         [(i, p) for i, p in mu["sfx"]], self.dir / "subs.srt", out)
        thumb = self.dir / "thumbnail.jpg"
        edit.make_thumbnail(self.cfg, self.state["images"][0], self.state["script"]["title"], thumb)
        return {"video": str(out), "thumbnail": str(thumb)}

    def s_metadata(self):
        return script_stage.make_metadata(self.cfg, self.budget, self.state["script"])

    def s_upload(self):
        if self.dry_run:
            return {"skipped": "dry-run"}
        if self.cfg["upload"]["require_approval"] and not self.state.get("approved"):
            return {"skipped": "awaiting approval"}
        r = youtube.upload(self.cfg, self.state["metadata"], self.state["edit"]["video"],
                           self.state["edit"]["thumbnail"])
        return r

    def s_instagram(self):
        if self.dry_run or not self.cfg["instagram"]["enabled"]:
            return {"skipped": "disabled or dry-run"}
        if self.cfg["upload"]["require_approval"] and not self.state.get("approved"):
            return {"skipped": "awaiting approval"}
        if self.cfg["video"]["orientation"] != "portrait":
            return {"skipped": "Reels need video.orientation: portrait"}
        return instagram.publish_reel(self.cfg, self.state["metadata"], self.state["edit"]["video"])

    def s_notify(self):
        up, meta = self.state.get("upload", {}), self.state["metadata"]
        ig = self.state.get("instagram", {})
        if "url" in up:
            subject, body = f"Uploaded: {meta['title']}", f"Video: {up['url']}\nCost: ${self.budget.spent:.2f}"
            if ig.get("url"):
                body += f"\nInstagram: {ig['url']}"
        else:
            subject = f"Draft ready ({up.get('skipped')}): {meta['title']}"
            body = f"File: {self.state['edit']['video']}\nRun with --approve {self.day} to publish."
        if self.dry_run:
            return {"sent": False}
        return {"sent": notify.send(self.cfg, subject, body)}

    STAGES = [("script", "s_script"), ("scenes", "s_scenes"), ("images", "s_images"), ("voice", "s_voice"),
              ("music", "s_music"), ("edit", "s_edit"), ("metadata", "s_metadata"),
              ("upload", "s_upload"), ("instagram", "s_instagram"), ("notify", "s_notify")]

    def run(self, only=None):
        r = self.cfg["retries"]
        for name, method in self.STAGES:
            if only and name != only:
                continue
            if name in self.state and not (only == name):
                log.info("skip %s (checkpoint)", name)
                continue
            log.info("stage %s", name)
            self.state[name] = retry(getattr(self, method), r["attempts"], r["base_delay"])
            write_json(self.state_file, self.state)
        self._record_history()
        return self.state

    def _record_history(self):
        if "upload" not in self.state or self.dry_run:
            return
        if "skipped" in self.state["upload"]:
            return
        hp = ROOT / self.cfg["history_file"]
        hist = read_json(hp, [])
        if not any(h.get("day") == self.day for h in hist):
            s = self.state["script"]
            hist.append({"day": self.day, "title": s["title"], "episode_summary": s.get("episode_summary", ""),
                         "url": self.state["upload"].get("url")})
            write_json(hp, hist)


def run_daily(cfg, day=None, dry_run=False, force=False, approve=False, stage=None):
    run = Run(cfg, day, dry_run, force)
    try:
        if approve:
            run.state["approved"] = True
            for k in ("upload", "instagram", "notify"):
                run.state.pop(k, None)
        return run.run(stage)
    except Exception as e:  # noqa: BLE001
        log.exception("pipeline failed")
        if not dry_run:
            try:
                notify.send(cfg, f"Anime agent FAILED ({run.day})", str(e))
            except Exception:  # noqa: BLE001
                log.exception("failure notification also failed")
        raise
