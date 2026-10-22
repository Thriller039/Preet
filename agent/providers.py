"""AI providers. `openai` uses the REST API; `mock` works offline for testing."""
import base64
import json

import requests

from .config import env
from .util import run

API = "https://api.openai.com/v1"


def _headers():
    return {"Authorization": "Bearer " + env("OPENAI_API_KEY")}


def chat_json(cfg, budget, system, user):
    budget.charge(cfg["budget"]["text_usd_per_call"], "text")
    if cfg["provider"] == "mock":
        raise NotImplementedError("mock text handled by callers")
    r = requests.post(f"{API}/chat/completions", headers=_headers(), timeout=180, json={
        "model": cfg["models"]["text"], "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def make_image(cfg, budget, prompt, out_path):
    budget.charge(cfg["budget"]["image_usd_each"], "image")
    w, h = cfg.size
    if cfg["provider"] == "mock":
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x3a2a6a:s={w}x{h}", "-frames:v", "1", out_path])
        return
    size = cfg["image_size"][cfg["video"]["orientation"]]
    r = requests.post(f"{API}/images/generations", headers=_headers(), timeout=300,
                      json={"model": cfg["models"]["image"], "prompt": prompt, "size": size, "n": 1})
    r.raise_for_status()
    item = r.json()["data"][0]
    if "b64_json" in item:
        data = base64.b64decode(item["b64_json"])
    else:
        data = requests.get(item["url"], timeout=120).content
    with open(out_path, "wb") as f:
        f.write(data)


def make_speech(cfg, budget, text, voice, out_path):
    budget.charge(len(text) / 1000 * cfg["budget"]["tts_usd_per_1k_chars"], "tts")
    if cfg["provider"] == "mock":
        secs = max(1.0, len(text.split()) / 2.5)
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{secs:.2f}",
             "-c:a", "libmp3lame", out_path])
        return
    r = requests.post(f"{API}/audio/speech", headers=_headers(), timeout=180, json={
        "model": cfg["models"]["tts"], "voice": voice, "input": text, "response_format": "mp3"})
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)
