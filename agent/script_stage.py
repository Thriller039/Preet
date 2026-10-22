"""Idea + script + scene stages."""
from pathlib import Path

from .config import ROOT
from .providers import chat_json
from .schema import safety_check, validate_script, validate_metadata
from .util import read_json

SYSTEM = """You are a professional anime writer for a YouTube channel. Return JSON only:
{"title": str, "synopsis": str, "episode_summary": str,
 "characters": [{"name": str, "appearance": str (fixed, detailed visual description), "voice_gender": "male|female|neutral"}],
 "scenes": [{"visual_prompt": str, "narration": str, "dialogue": [{"character": str, "line": str}],
             "mood": "calm|epic|sad|tense|happy|mysterious", "sfx": [str]}]}
Keep it family-friendly. Every scene's visual_prompt must restate the appearance of characters present."""


def bible_and_history(cfg):
    b = ROOT / cfg["story_bible"]
    bible = b.read_text() if b.exists() else "Original anime short stories."
    history = read_json(ROOT / cfg["history_file"], [])
    return bible, history


def mock_script(cfg):
    n = cfg["video"]["scenes"]
    return {"title": "The Lantern Fox", "synopsis": "A girl and a fox spirit find a hidden shrine.",
            "episode_summary": "Mika meets Kitsu.",
            "characters": [{"name": "Mika", "appearance": "girl with short silver hair, red scarf", "voice_gender": "female"},
                           {"name": "Kitsu", "appearance": "small white fox spirit, glowing blue lantern", "voice_gender": "neutral"}],
            "scenes": [{"visual_prompt": f"Mika and Kitsu walking in a misty forest, scene {i + 1}",
                        "narration": "Deep in the forest, a quiet light guided the way.",
                        "dialogue": [{"character": "Mika", "line": "Do you see that glow?"}],
                        "mood": "mysterious", "sfx": ["wind"]} for i in range(n)]}


def make_script(cfg, budget):
    if cfg["provider"] == "mock":
        script = mock_script(cfg)
    else:
        bible, history = bible_and_history(cfg)
        recent = [h.get("episode_summary", h.get("title")) for h in history[-10:]]
        user = (f"Channel: {cfg['channel']['name']}. Language: {cfg['channel']['language']}.\n"
                f"Style: {cfg['channel']['style']}.\nStory bible:\n{bible}\n"
                f"Previous episodes (continue the story, do not repeat): {recent}\n"
                f"Write the next episode: {cfg['video']['scenes']} scenes, about "
                f"{cfg['video']['target_seconds']} seconds when narrated.")
        script = chat_json(cfg, budget, SYSTEM, user)
    validate_script(script)
    safety_check(script)
    return script


META_SYSTEM = ('Return JSON only: {"title": str (<=100 chars, catchy), "description": str, '
               '"hashtags": [str]}. Write for YouTube SEO.')


def make_metadata(cfg, budget, script):
    if cfg["provider"] == "mock":
        meta = {"title": script["title"], "description": script["synopsis"],
                "hashtags": ["anime", "shorts", "aiart"]}
    else:
        meta = chat_json(cfg, budget, META_SYSTEM,
                         f"Language: {cfg['channel']['language']}. Episode: {script['title']} - "
                         f"{script['synopsis']}\n" + "\n".join(s["narration"] for s in script["scenes"]))
    return validate_metadata(meta)
