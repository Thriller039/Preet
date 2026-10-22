"""Anime image generation: one image per scene with fixed character descriptions."""
from pathlib import Path

from .providers import make_image


def scene_prompt(cfg, script, scene):
    chars = "; ".join(f"{c['name']}: {c['appearance']}" for c in script["characters"])
    return (f"{cfg['channel']['style']}. Anime illustration, no text, no watermark. "
            f"Characters: {chars}. Scene: {scene['visual_prompt']}")


def generate_images(cfg, budget, script, workdir: Path):
    paths = []
    for i, sc in enumerate(script["scenes"]):
        out = workdir / f"scene_{i:02d}.png"
        if not out.exists():  # resume support
            make_image(cfg, budget, scene_prompt(cfg, script, sc), out)
        paths.append(str(out))
    return paths
