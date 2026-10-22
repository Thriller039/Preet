"""YouTube Data API v3 upload. First login: `python -m agent.auth` to get a refresh token."""
import json

from .config import env

SCOPES_YT = ["https://www.googleapis.com/auth/youtube.upload"]
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.send"]


def credentials(scopes=None):
    from google.oauth2.credentials import Credentials
    return Credentials(
        None, refresh_token=env("GOOGLE_REFRESH_TOKEN"), token_uri="https://oauth2.googleapis.com/token",
        client_id=env("GOOGLE_CLIENT_ID"), client_secret=env("GOOGLE_CLIENT_SECRET"),
        scopes=scopes or SCOPES_YT + SCOPES_GMAIL)


def build_body(cfg, meta):
    up = cfg["upload"]
    status = {"privacyStatus": up["privacy"], "selfDeclaredMadeForKids": up["made_for_kids"],
              "containsSyntheticMedia": True}
    if up.get("publish_at"):  # scheduled publishing requires private
        status.update(privacyStatus="private", publishAt=up["publish_at"])
    return {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": str(up["category_id"])}, "status": status}


def upload(cfg, meta, video, thumbnail):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=credentials(), cache_discovery=False)
    req = yt.videos().insert(part="snippet,status", body=build_body(cfg, meta),
                             media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    if thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail))).execute()
        except Exception as e:  # noqa: BLE001  (thumbnails need a verified channel)
            import logging
            logging.getLogger("agent").warning("thumbnail upload failed: %s", e)
    return {"video_id": vid, "url": f"https://youtu.be/{vid}"}
