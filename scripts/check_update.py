#!/usr/bin/env python3
# huntd/scripts/check_update.py
"""Check if the local huntd repo is behind its remote origin.

Prints a formatted notice if updates are available. Exits silently if
no remote is configured, no network is available, or the repo is up to date.

Usage: python scripts/check_update.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=5)
    return result.returncode, result.stdout.strip()


def main() -> None:
    # Bail immediately if not a git repo
    code, _ = run(["git", "rev-parse", "--is-inside-work-tree"], ROOT)
    if code != 0:
        return

    # Fetch quietly — if there's no network or no remote, this fails silently
    fetch_code, _ = run(["git", "fetch", "--quiet", "origin"], ROOT)
    if fetch_code != 0:
        return

    # Compare local HEAD to remote tracking branch
    _, local_sha = run(["git", "rev-parse", "HEAD"], ROOT)
    _, remote_sha = run(["git", "rev-parse", "@{u}"], ROOT)

    if not local_sha or not remote_sha:
        return

    if local_sha == remote_sha:
        return  # Up to date

    # Count commits behind
    _, behind_str = run(
        ["git", "rev-list", "--count", f"HEAD..{remote_sha}"],
        ROOT,
    )
    behind = int(behind_str) if behind_str.isdigit() else 1
    plural = "s" if behind != 1 else ""

    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(
            Panel(
                f"[bold yellow]{behind} update{plural} available.[/] Run [bold cyan]/huntd update[/] to get the latest features.",
                border_style="yellow",
            )
        )
    except ImportError:
        print(f"[huntd] {behind} update{plural} available. Run /huntd update to get the latest.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never block the user — update check is best-effort
