"""CLI entry point: python -m agent.run_daily [--dry-run] [--force] [--approve] [--day D] [--stage S]"""
import argparse
import logging

from .config import load_config
from .pipeline import Run, run_daily


def main(argv=None):
    p = argparse.ArgumentParser(description="Create and upload one anime video.")
    p.add_argument("--config", default=None)
    p.add_argument("--dry-run", action="store_true", help="build the video but do not upload or email")
    p.add_argument("--force", action="store_true", help="ignore checkpoints and start over")
    p.add_argument("--approve", action="store_true", help="publish an existing draft for --day")
    p.add_argument("--day", default=None, help="YYYY-MM-DD working folder (default today)")
    p.add_argument("--stage", choices=[n for n, _ in Run.STAGES], help="re-run only this stage")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    state = run_daily(load_config(a.config), a.day, a.dry_run, a.force, a.approve, a.stage)
    print("Done:", state.get("upload", {}))


if __name__ == "__main__":
    main()
