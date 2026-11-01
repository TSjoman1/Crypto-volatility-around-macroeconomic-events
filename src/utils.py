#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers: logging, HTTP retry, checksums, manifest, design/test guard."""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config as cfg  # noqa: E402

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logger(name: str) -> logging.Logger:
    cfg.LOGS.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = logging.FileHandler(cfg.LOGS / f"{name}.log")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


# ---------------------------------------------------------------------------
# Design / test mode guard
# ---------------------------------------------------------------------------
def assert_design_or_registered(mode: str) -> None:
    if mode not in ("design", "test"):
        raise ValueError("mode must be 'design' or 'test'")
    if mode == "design":
        return
    # Stronger than env alone: frozen spec file must exist and env unlock
    if not cfg.FROZEN_SPEC.exists():
        raise PermissionError(
            f"Test window locked: missing {cfg.FROZEN_SPEC}. "
            "Write and register the frozen specification first."
        )
    if os.environ.get("SPEC_REGISTERED") != "yes":
        raise PermissionError(
            "Test window locked. After registering the frozen spec, set "
            "SPEC_REGISTERED=yes in the environment."
        )


def load_panel(con: Any, table: str, mode: str = "design"):
    """All analysis must load panels through this helper."""
    assert_design_or_registered(mode)
    if mode == "test":
        return con.sql(f"SELECT * FROM {table}").df()
    return con.sql(f"SELECT * FROM {table} WHERE window = 'design'").df()


def last_complete_utc_day() -> date:
    # Exclude today's partial UTC day
    return datetime.now(tz=UTC).date().fromordinal(
        datetime.now(tz=UTC).date().toordinal() - 1
    )


def analysis_end() -> date:
    return cfg.END_DATE or last_complete_utc_day()


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
_last_req = 0.0


def http_get(
    url: str,
    *,
    params: Optional[dict] = None,
    max_retries: int = 6,
    stream: bool = False,
) -> requests.Response:
    global _last_req
    min_interval = 1.0 / max(cfg.HTTP_MAX_RPS, 0.1)
    for attempt in range(max_retries):
        elapsed = time.time() - _last_req
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        try:
            resp = requests.get(
                url, params=params, timeout=cfg.HTTP_TIMEOUT, stream=stream
            )
            _last_req = time.time()
            if resp.status_code == 404:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = min(2 ** attempt, 60)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(min(2 ** attempt, 60))
    raise RuntimeError(f"Failed GET {url}")


def download_file(url: str, dest: Path, logger: Optional[logging.Logger] = None) -> bool:
    """Download to dest. Returns False on 404. Resumable if .part exists."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    resp = http_get(url, stream=True)
    if resp.status_code == 404:
        if logger:
            logger.info("404 %s", url)
        return False
    with open(part, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            if chunk:
                f.write(chunk)
    part.replace(dest)
    return True


# ---------------------------------------------------------------------------
# Checksums / manifest
# ---------------------------------------------------------------------------
def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def parse_binance_checksum(text: str) -> str:
    # "<hash>  <filename>" or "<hash> *<filename>"
    line = text.strip().splitlines()[0]
    return line.split()[0].strip()


def verify_checksum(file_path: Path, checksum_path: Path, logger: logging.Logger) -> bool:
    expected = parse_binance_checksum(checksum_path.read_text(encoding="utf-8", errors="replace"))
    actual = sha256_file(file_path)
    ok = actual.lower() == expected.lower()
    if not ok:
        logger.error("CHECKSUM FAIL %s expected=%s actual=%s", file_path, expected, actual)
        quarantine = file_path.parent / "_quarantine"
        quarantine.mkdir(exist_ok=True)
        file_path.rename(quarantine / file_path.name)
    return ok


def append_manifest(
    path: Path,
    source_url: str,
    sha: str,
    row_count: Optional[int] = None,
) -> None:
    import csv

    cfg.DATA.mkdir(parents=True, exist_ok=True)
    new_file = not cfg.MANIFEST.exists()
    with open(cfg.MANIFEST, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["path", "source_url", "downloaded_at_utc", "sha256", "row_count"],
        )
        if new_file:
            w.writeheader()
        w.writerow(
            {
                "path": str(path.relative_to(cfg.ROOT)) if path.is_relative_to(cfg.ROOT) else str(path),
                "source_url": source_url,
                "downloaded_at_utc": datetime.now(tz=UTC).isoformat(),
                "sha256": sha,
                "row_count": row_count if row_count is not None else "",
            }
        )


def already_in_manifest(path: Path, sha: Optional[str] = None) -> bool:
    if not cfg.MANIFEST.exists() or not path.exists():
        return False
    import pandas as pd

    rel = str(path.relative_to(cfg.ROOT)) if path.is_relative_to(cfg.ROOT) else str(path)
    m = pd.read_csv(cfg.MANIFEST)
    if m.empty or "path" not in m.columns:
        return False
    hits = m[m["path"] == rel]
    if hits.empty:
        return False
    if sha is None:
        return True
    return str(hits.iloc[-1]["sha256"]).lower() == sha.lower()


def et_to_utc(d: date, hour: int, minute: int = 0) -> datetime:
    """US Eastern local wall time → UTC datetime (tz-aware then strip to naive UTC)."""
    local = datetime(d.year, d.month, d.day, hour, minute, tzinfo=ET)
    return local.astimezone(UTC).replace(tzinfo=None)


def note(msg: str) -> None:
    cfg.DOCS.mkdir(parents=True, exist_ok=True)
    p = cfg.DOCS / "data_notes.md"
    if not p.exists():
        p.write_text("# Data notes\n\n", encoding="utf-8")
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"- {datetime.now(tz=UTC).date()}: {msg}\n")
