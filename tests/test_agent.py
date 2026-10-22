import pytest

from agent import schema, voice
from agent.config import load_config
from agent.notify import build_message
from agent.script_stage import mock_script
from agent.util import Budget, BudgetExceeded, retry
from agent.youtube import build_body


def test_script_valid_and_invalid():
    cfg = load_config(); cfg.data["provider"] = "mock"
    s = mock_script(cfg)
    schema.validate_script(s); schema.safety_check(s)
    s["scenes"][0]["dialogue"][0]["character"] = "Nobody"
    with pytest.raises(schema.ValidationError):
        schema.validate_script(s)
    with pytest.raises(schema.ValidationError):
        schema.validate_script({"title": "x"})


def test_safety_blocks():
    cfg = load_config(); cfg.data["provider"] = "mock"
    s = mock_script(cfg); s["scenes"][0]["narration"] = "so much gore"
    with pytest.raises(schema.ValidationError):
        schema.safety_check(s)


def test_metadata_limits_and_disclosure():
    m = schema.validate_metadata({"title": "t" * 200, "description": "d", "hashtags": ["#a", "b"] * 400})
    assert len(m["title"]) == 100 and "AI-generated" in m["description"]
    assert len(m["description"]) <= 5000 and sum(len(t) + 1 for t in m["tags"]) <= 500


def test_retry_and_budget():
    calls = []
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("x")
        return "ok"
    assert retry(flaky, 3, 0, sleep=lambda s: None) == "ok"
    b = Budget(0.05)
    with pytest.raises(BudgetExceeded):
        b.charge(0.1)
    with pytest.raises(BudgetExceeded):
        retry(lambda: b.charge(1), 3, 0, sleep=lambda s: None)


def test_srt_and_voices():
    assert voice.srt_time(3661.5) == "01:01:01,500"
    cfg = load_config(); cfg.data["provider"] = "mock"
    v = voice.voice_map(cfg, mock_script(cfg))
    assert v["narrator"] and v["Mika"] != v["Kitsu"]


def test_upload_body_schedule_forces_private():
    cfg = load_config(); cfg.data["upload"]["publish_at"] = "2030-01-01T00:00:00Z"
    cfg.data["upload"]["privacy"] = "public"
    b = build_body(cfg, {"title": "t", "description": "d", "tags": []})
    assert b["status"]["privacyStatus"] == "private" and b["status"]["publishAt"]


def test_email():
    assert build_message("a@b.c", "s", "b")["Subject"] == "s"


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="ffmpeg missing")
def test_mock_pipeline_end_to_end(tmp_path):
    from agent.pipeline import Run
    cfg = load_config(); cfg.data["provider"] = "mock"
    cfg.data["video"]["scenes"] = 2
    cfg.data["video"]["fps"] = 10
    cfg.data["work_dir"] = str(tmp_path)
    r = Run(cfg, "2030-01-01", dry_run=True)
    r.cfg.data["video"]["orientation"] = "portrait"
    st = r.run()
    assert (tmp_path / "2030-01-01" / "final.mp4").stat().st_size > 0
    assert st["upload"]["skipped"] == "dry-run"
