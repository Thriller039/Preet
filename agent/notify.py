"""Email notifications via Gmail API (gmail.send) or SMTP app password."""
import base64
import smtplib
from email.message import EmailMessage

from .config import env


def build_message(to, subject, body, sender="me"):
    m = EmailMessage()
    m["To"], m["From"], m["Subject"] = to, sender, subject
    m.set_content(body)
    return m


def send(cfg, subject, body):
    method = cfg["notify"]["method"]
    to = env(cfg["notify"]["to_env"], required=False)
    if method == "none" or not to:
        return False
    if method == "smtp":
        user = env("SMTP_USER")
        m = build_message(to, subject, body, user)
        with smtplib.SMTP_SSL(env("SMTP_HOST", False) or "smtp.gmail.com", 465) as s:
            s.login(user, env("SMTP_PASSWORD"))
            s.send_message(m)
        return True
    from googleapiclient.discovery import build
    from .youtube import credentials
    raw = base64.urlsafe_b64encode(build_message(to, subject, body).as_bytes()).decode()
    build("gmail", "v1", credentials=credentials(), cache_discovery=False).users().messages().send(
        userId="me", body={"raw": raw}).execute()
    return True
