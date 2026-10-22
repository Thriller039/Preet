"""TTS per line with per-character voices; builds scene audio and subtitle timing."""
from pathlib import Path

from .providers import make_speech
from .util import duration, run

GENDER_VOICES = {"male": ["onyx", "echo"], "female": ["nova", "shimmer"], "neutral": ["fable", "alloy"]}


def voice_map(cfg, script):
    out, used = {"narrator": cfg["voices"]["narrator"]}, 0
    for c in script["characters"]:
        pool = GENDER_VOICES.get(c.get("voice_gender"), cfg["voices"]["pool"])
        out[c["name"]] = pool[used % len(pool)]
        used += 1
    return out


def generate_voice(cfg, budget, script, workdir: Path):
    voices = voice_map(cfg, script)
    scenes, cues, t = [], [], 0.0
    for i, sc in enumerate(script["scenes"]):
        lines = ([("narrator", sc["narration"])] if sc["narration"] else []) + \
                [(d["character"], d["line"]) for d in sc["dialogue"]]
        files = []
        for j, (who, text) in enumerate(lines):
            f = workdir / f"voice_{i:02d}_{j:02d}.mp3"
            if not f.exists():
                make_speech(cfg, budget, text, voices[who], f)
            d = duration(f)
            cues.append({"start": t, "end": t + d, "text": text})
            t += d
            files.append(f)
        scene_audio = workdir / f"scene_{i:02d}.wav"
        concat_audio(files, scene_audio, workdir / f"list_{i:02d}.txt")
        scenes.append({"audio": str(scene_audio), "duration": duration(scene_audio)})
    return {"scenes": scenes, "cues": cues}


def concat_audio(files, out, listfile):
    listfile.write_text("".join(f"file '{Path(f).resolve()}'\n" for f in files))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-ar", "44100", "-ac", "2", out])


def srt_time(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(cues, path):
    Path(path).write_text("".join(
        f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n"
        for i, c in enumerate(cues, 1)))
