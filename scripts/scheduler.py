#!/usr/bin/env python3
# huntd/scripts/scheduler.py
"""Install or remove the daily huntd cron job.

Usage:
  python scripts/scheduler.py enable   # install daily cron at configured time
  python scripts/scheduler.py disable  # remove huntd cron entry
  python scripts/scheduler.py status   # show current schedule
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
MARKER = "# huntd-daily"


def get_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def set_crontab(content: str) -> None:
    proc = subprocess.run(["crontab", "-"], input=content, text=True)
    if proc.returncode != 0:
        print("ERROR: Failed to update crontab.")
        sys.exit(1)


def parse_time(time_str: str) -> tuple[int, int]:
    """Parse '21:00', '8am', '9pm', '8:30am' into (hour, minute)."""
    time_str = time_str.strip().lower()
    m = re.match(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", time_str)
    if not m:
        return 21, 0
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    period = m.group(3)
    if period == "pm" and hour != 12:
        hour += 12
    elif period == "am" and hour == 12:
        hour = 0
    return hour, minute


def read_schedule_from_profile() -> tuple[int, int]:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from config import load_profile

        profile = load_profile()
        time_str = profile.get("schedule", {}).get("time", "21:00")
        return parse_time(time_str)
    except Exception:
        return 21, 0


def build_cron_line(hour: int, minute: int) -> str:
    uv = str(Path.home() / ".local" / "bin" / "uv")
    root = str(ROOT)
    log = str(ROOT / "data" / "pipeline.log")
    return (
        f"{minute} {hour} * * * "
        f"cd {root} && "
        f"{uv} run python scripts/scan.py && "
        f"{uv} run python scripts/score_batch.py && "
        f"{uv} run python scripts/push_notion.py "
        f">> {log} 2>&1 "
        f"{MARKER}"
    )


def enable_schedule() -> None:
    hour, minute = read_schedule_from_profile()
    crontab = get_crontab()
    lines = [l for l in crontab.splitlines() if MARKER not in l]
    lines.append(build_cron_line(hour, minute))
    set_crontab("\n".join(lines) + "\n")
    print(f"Schedule enabled: daily at {hour:02d}:{minute:02d} local time.")
    print(f"Log: data/pipeline.log")
    print(f"To change the time: tell your AI 'change my schedule to [time]'")


def disable_schedule() -> None:
    crontab = get_crontab()
    lines = [l for l in crontab.splitlines() if MARKER not in l]
    set_crontab("\n".join(lines) + "\n")
    print("Schedule disabled.")


def show_status() -> None:
    crontab = get_crontab()
    entries = [l for l in crontab.splitlines() if MARKER in l]
    if entries:
        print(f"Schedule active: {entries[0]}")
    else:
        print("No active schedule. Run: python scripts/scheduler.py enable")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "enable":
        enable_schedule()
    elif cmd == "disable":
        disable_schedule()
    elif cmd == "status":
        show_status()
    else:
        print(f"Unknown command: {cmd}. Use: enable | disable | status")
        sys.exit(1)


if __name__ == "__main__":
    main()
