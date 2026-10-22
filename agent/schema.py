"""Validation of the LLM script JSON and YouTube metadata limits."""

class ValidationError(ValueError):
    pass


BLOCKED = ("gore", "sexual", "nude", "suicide", "self-harm", "hate speech")


def validate_script(s: dict) -> dict:
    if not isinstance(s, dict):
        raise ValidationError("script must be an object")
    for k in ("title", "synopsis", "characters", "scenes"):
        if k not in s:
            raise ValidationError(f"missing '{k}'")
    if not s["scenes"]:
        raise ValidationError("no scenes")
    names = set()
    for c in s["characters"]:
        if not c.get("name") or not c.get("appearance"):
            raise ValidationError("character needs name and appearance")
        names.add(c["name"])
    for i, sc in enumerate(s["scenes"]):
        if not sc.get("visual_prompt"):
            raise ValidationError(f"scene {i} missing visual_prompt")
        if not sc.get("narration") and not sc.get("dialogue"):
            raise ValidationError(f"scene {i} has no narration or dialogue")
        sc.setdefault("mood", "calm")
        sc.setdefault("sfx", [])
        sc.setdefault("narration", "")
        sc.setdefault("dialogue", [])
        for d in sc["dialogue"]:
            if d.get("character") not in names or not d.get("line"):
                raise ValidationError(f"scene {i}: bad dialogue entry {d}")
    return s


def safety_check(s: dict):
    text = " ".join([s["title"], s["synopsis"]] + [
        sc["narration"] + " " + sc["visual_prompt"] + " " + " ".join(d["line"] for d in sc["dialogue"])
        for sc in s["scenes"]]).lower()
    hits = [w for w in BLOCKED if w in text]
    if hits:
        raise ValidationError(f"content safety check failed: {hits}")


def validate_metadata(m: dict) -> dict:
    title = str(m.get("title", "")).strip()
    if not title:
        raise ValidationError("empty title")
    m["title"] = title[:100]
    tags = [str(t).lstrip("#").strip() for t in m.get("hashtags", []) if str(t).strip()]
    m["hashtags"] = tags[:15]
    desc = str(m.get("description", "")).strip()
    disclosure = "This video was created with AI-generated visuals, voices and script."
    if disclosure not in desc:
        desc += "\n\n" + disclosure
    desc += "\n\n" + " ".join("#" + t.replace(" ", "") for t in m["hashtags"][:3])
    m["description"] = desc[:5000]
    # YouTube tags field is limited to ~500 chars total
    out, n = [], 0
    for t in tags:
        n += len(t) + 1
        if n > 480:
            break
        out.append(t)
    m["tags"] = out
    return m
