"""Instagram Reels publishing via the Instagram Graph API (resumable local-file upload)."""
import time

import requests

from .config import env

GRAPH = "https://graph.facebook.com/v21.0"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload/v21.0"
MAX_CAPTION = 2200


def build_caption(meta):
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in meta.get("tags", [])[:30] if t.strip())
    text = meta["title"] + "\n\n" + meta["description"]
    caption = (text + "\n\n" + tags).strip() if tags else text
    return caption[:MAX_CAPTION]


def _check(r):
    r.raise_for_status()
    return r.json()


def publish_reel(cfg, meta, video, session=requests, sleep=time.sleep):
    token, user = env("INSTAGRAM_ACCESS_TOKEN"), env("INSTAGRAM_USER_ID")
    ig = cfg["instagram"]
    data = {"media_type": "REELS", "upload_type": "resumable", "caption": build_caption(meta),
            "share_to_feed": str(bool(ig["share_to_feed"])).lower(), "access_token": token}
    cid = _check(session.post(f"{GRAPH}/{user}/media", data=data, timeout=60))["id"]
    with open(video, "rb") as f:
        payload = f.read()
    _check(session.post(f"{RUPLOAD}/{cid}", data=payload, timeout=600, headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(payload))}))
    for _ in range(ig["poll_attempts"]):
        status = _check(session.get(f"{GRAPH}/{cid}", params={"fields": "status_code", "access_token": token},
                                    timeout=60)).get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram processing failed: {status}")
        sleep(ig["poll_delay"])
    else:
        raise RuntimeError("Instagram processing timed out")
    mid = _check(session.post(f"{GRAPH}/{user}/media_publish",
                              data={"creation_id": cid, "access_token": token}, timeout=60))["id"]
    link = _check(session.get(f"{GRAPH}/{mid}", params={"fields": "permalink", "access_token": token},
                              timeout=60)).get("permalink")
    return {"media_id": mid, "url": link}
