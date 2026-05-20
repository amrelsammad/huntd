# huntd/scripts/config.py
"""Shared utilities for loading config, profiles, and managing data state."""

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent


def load_profile() -> dict:
    path = ROOT / "config" / "profile.yml"
    if not path.exists():
        raise FileNotFoundError(
            "config/profile.yml not found.\n"
            "Copy config/profile.example.yml to config/profile.yml and fill it in."
        )
    with open(path) as f:
        return yaml.safe_load(f)


def load_portals() -> dict:
    path = ROOT / "config" / "portals.yml"
    if not path.exists():
        path = ROOT / "config" / "portals.example.yml"
        print("[WARN] config/portals.yml not found, using example portals config.")
    with open(path) as f:
        return yaml.safe_load(f)


def load_seen() -> set:
    path = ROOT / "data" / "seen.json"
    if not path.exists():
        return set()
    with open(path) as f:
        return set(json.load(f))


def save_seen(seen: set) -> None:
    path = ROOT / "data" / "seen.json"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def load_pipeline_urls() -> set:
    """Return all URLs already in data/pipeline.md."""
    path = ROOT / "data" / "pipeline.md"
    if not path.exists():
        return set()
    text = path.read_text()
    return set(re.findall(r"https?://[^\s|]+", text))


def append_to_pipeline(jobs: list[dict]) -> None:
    """Append new job entries to data/pipeline.md."""
    path = ROOT / "data" / "pipeline.md"
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        path.write_text("# Pipeline — Discovered Jobs\n\n## Pending\n\n")

    with open(path, "a") as f:
        for job in jobs:
            location = job.get("location") or "Unknown"
            line = f"- [ ] {job['url']} | {job['company']} | {job['title']} | {location}\n"
            f.write(line)


def job_id(url: str) -> str:
    """Stable MD5 hash of a job URL for deduplication."""
    return hashlib.md5(url.strip().encode()).hexdigest()
