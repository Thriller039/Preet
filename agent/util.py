import json
import logging
import subprocess
import time
from pathlib import Path

log = logging.getLogger("agent")


def run(cmd):
    log.debug("run: %s", " ".join(map(str, cmd)))
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-1500:]}")
    return r.stdout


def duration(path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def read_json(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def retry(fn, attempts=3, base_delay=2.0, sleep=time.sleep):
    for i in range(attempts):
        try:
            return fn()
        except BudgetExceeded:
            raise
        except Exception as e:  # noqa: BLE001
            if i == attempts - 1:
                raise
            delay = base_delay * 2 ** i
            log.warning("attempt %d failed (%s); retrying in %.1fs", i + 1, e, delay)
            sleep(delay)


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, cap):
        self.cap, self.spent = cap, 0.0

    def charge(self, usd, what=""):
        self.spent += usd
        log.info("cost +$%.3f (%s) total $%.3f", usd, what, self.spent)
        if self.spent > self.cap:
            raise BudgetExceeded(f"Cost cap ${self.cap:.2f} exceeded (${self.spent:.2f})")
