"""Pick royalty-free music/SFX from local libraries by mood tag. Files: <mood>*.mp3 etc."""
import random
from collections import Counter
from pathlib import Path

from .config import ROOT

EXTS = {".mp3", ".wav", ".ogg", ".m4a"}


def find_track(directory, tag, seed=0):
    d = ROOT / directory
    if not d.is_dir():
        return None
    files = sorted(p for p in d.iterdir() if p.suffix.lower() in EXTS)
    matches = [p for p in files if tag.lower() in p.stem.lower()] or files
    return random.Random(seed).choice(matches) if matches else None


def pick_music(cfg, script, seed=0):
    mood = Counter(s["mood"] for s in script["scenes"]).most_common(1)[0][0]
    return find_track(cfg["music_dir"], mood, seed)


def pick_sfx(cfg, script):
    """Returns [(scene_index, path)] for SFX tags that have a matching file."""
    out = []
    for i, sc in enumerate(script["scenes"]):
        for tag in sc["sfx"][:1]:
            d = ROOT / cfg["sfx_dir"]
            if d.is_dir():
                m = [p for p in sorted(d.iterdir()) if p.suffix.lower() in EXTS and tag.lower() in p.stem.lower()]
                if m:
                    out.append((i, m[0]))
    return out
