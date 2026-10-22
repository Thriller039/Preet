"""FFmpeg editing: Ken Burns clips, concat, voice+music+SFX mix with ducking, subtitles, thumbnail."""
from pathlib import Path

from .util import log, run


def scene_clip(cfg, image, audio, dur, out, idx):
    w, h = cfg.size
    fps = cfg["video"]["fps"]
    frames = max(1, int(dur * fps) + 1)
    zoom = "min(zoom+0.0008,1.2)" if idx % 2 == 0 else "if(eq(on,1),1.2,max(zoom-0.0008,1.0))"
    vf = (f"scale={w * 2}:{h * 2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s={w}x{h}:fps={fps},format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-i", image, "-i", audio, "-vf", vf, "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out])


def concat_clips(clips, out, listfile):
    listfile.write_text("".join(f"file '{Path(c).resolve()}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", out])


def build_video(cfg, images, voice, workdir: Path, music, sfx, srt, out):
    clips = []
    for i, (img, sc) in enumerate(zip(images, voice["scenes"])):
        c = workdir / f"clip_{i:02d}.mp4"
        scene_clip(cfg, img, sc["audio"], sc["duration"], c, i)
        clips.append(c)
    for key in ("intro", "outro"):  # optional pre-rendered clips, same codec settings required
        extra = cfg.get(key)
        if extra and Path(extra).exists():
            clips = ([extra] + clips) if key == "intro" else (clips + [extra])
    base = workdir / "base.mp4"
    concat_clips(clips, base, workdir / "clips.txt")

    inputs, filters, labels, n = ["-i", str(base)], [], ["[0:a]"], 1
    starts, t = [], 0.0
    for sc in voice["scenes"]:
        starts.append(t)
        t += sc["duration"]
    for idx, path in sfx:
        inputs += ["-i", str(path)]
        ms = int(starts[idx] * 1000)
        filters.append(f"[{n}:a]adelay={ms}|{ms},volume=0.6[sfx{n}]")
        labels.append(f"[sfx{n}]")
        n += 1
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0[vox]")
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        filters.append(f"[{n}:a]volume=0.35[mus]")
        filters.append("[vox]asplit[voxa][voxb];[mus][voxb]sidechaincompress=threshold=0.03:ratio=8[duck];"
                       "[voxa][duck]amix=inputs=2:duration=first:normalize=0[aout]")
    else:
        filters.append("[vox]anull[aout]")
    vfilter = []
    if srt:
        style = "FontSize=18,Outline=2,MarginV=40"
        vfilter = ["-vf", f"subtitles='{Path(srt).resolve().as_posix()}':force_style='{style}'"]
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]",
         *vfilter, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
         "-shortest", out])
    return out


def make_thumbnail(cfg, image, title, out):
    w, h = 1280, 720
    base = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    safe = "".join(ch for ch in title if ch.isalnum() or ch in " -!?")[:60]
    try:
        run(["ffmpeg", "-y", "-i", image, "-vf",
             f"{base},drawtext=text='{safe}':fontcolor=white:fontsize=72:borderw=6:bordercolor=black"
             ":x=(w-text_w)/2:y=h-160", "-frames:v", "1", "-update", "1", out])
    except RuntimeError as e:
        log.warning("drawtext unavailable (%s); thumbnail without text", str(e)[:100])
        run(["ffmpeg", "-y", "-i", image, "-vf", base, "-frames:v", "1", "-update", "1", out])
