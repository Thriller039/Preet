"""Settings come from config.yaml; secrets only from environment variables."""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "provider": "openai",  # openai | mock (offline, no API calls)
    "channel": {"name": "My Anime Channel", "language": "English",
                "style": "cinematic anime, vibrant colors, detailed backgrounds"},
    "video": {"orientation": "landscape", "scenes": 6, "target_seconds": 120, "fps": 30},
    "models": {"text": "gpt-4o-mini", "image": "gpt-image-1", "tts": "gpt-4o-mini-tts"},
    "image_size": {"landscape": "1536x1024", "portrait": "1024x1536"},
    "voices": {"narrator": "alloy", "default": "nova", "pool": ["nova", "echo", "fable", "onyx", "shimmer"]},
    "music_dir": "assets/music",
    "sfx_dir": "assets/sfx",
    "intro": None,
    "outro": None,
    "story_bible": "data/story_bible.md",
    "history_file": "data/history.json",
    "work_dir": "work",
    "upload": {"privacy": "private", "category_id": "1", "made_for_kids": False,
               "publish_at": None, "require_approval": False},
    "budget": {"max_usd_per_video": 2.0, "text_usd_per_call": 0.01,
               "image_usd_each": 0.10, "tts_usd_per_1k_chars": 0.015},
    "retries": {"attempts": 3, "base_delay": 2.0},
    "notify": {"method": "gmail_api", "to_env": "NOTIFY_TO"},  # gmail_api | smtp | none
}


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


@dataclass
class Config:
    data: dict = field(default_factory=lambda: dict(DEFAULTS))

    def __getitem__(self, k):
        return self.data[k]

    def get(self, k, default=None):
        return self.data.get(k, default)

    @property
    def size(self):
        return (1920, 1080) if self.data["video"]["orientation"] == "landscape" else (1080, 1920)


def load_config(path=None) -> Config:
    p = Path(path or ROOT / "config.yaml")
    user = yaml.safe_load(p.read_text()) if p.exists() else {}
    return Config(_merge(DEFAULTS, user))


def env(name, required=True):
    v = os.environ.get(name)
    if required and not v:
        raise RuntimeError(f"Missing required environment variable {name}")
    return v
