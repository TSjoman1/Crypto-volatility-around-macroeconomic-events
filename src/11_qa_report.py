#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data-quality report: counts only (no test-window vol/return/volume levels)."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config as cfg
from utils import setup_logger

log = setup_logger("11_qa_report")


def main() -> None:
    cfg.DOCS.mkdir(parents=True, exist_ok=True)
    lines = ["# QA report\n", f"Generated for project root `{cfg.ROOT}`\n"]

    if not cfg.DB_PATH.exists():
        lines.append("\n**DB missing** — run `10_build_db.py` first.\n")
        (cfg.DOCS / "qa_report.md").write_text("".join(lines), encoding="utf-8")
        return

    con = duckdb.connect(str(cfg.DB_PATH), read_only=True)

    def q(sql: str):
        try:
            return con.execute(sql).fetchdf()
        except Exception as e:
            return f"ERR: {e}"

    lines.append("\n## Symbols\n")
    lines.append(str(q("SELECT * FROM symbols")) + "\n")

    lines.append("\n## Klines partitions (row counts by symbol/year)\n")
    lines.append(
        str(
            q(
                """
                SELECT symbol, year(ts_utc) AS y, COUNT(*) AS rows
                FROM klines
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            )
        )
        + "\n"
    )

    lines.append("\n## Panel hourly row counts by window (counts only)\n")
    lines.append(str(q("SELECT symbol, window, COUNT(*) AS n FROM panel_hourly GROUP BY 1,2 ORDER BY 1,2")) + "\n")

    lines.append("\n## Macro event counts by year/type\n")
    lines.append(
        str(
            q(
                """
                SELECT event_type, year(cast(event_time_utc AS TIMESTAMP)) AS y, COUNT(*) AS n
                FROM macro_events
                GROUP BY 1, 2
                ORDER BY 1, 2
                """
            )
        )
        + "\n"
    )

    lines.append("\n## Expiries by source\n")
    lines.append(str(q("SELECT currency, source, COUNT(*) AS n FROM expiries GROUP BY 1,2")) + "\n")

    lines.append("\n## DVOL coverage (timestamps only)\n")
    lines.append(str(q("SELECT currency, min(ts_utc) AS first_ts, max(ts_utc) AS last_ts, COUNT(*) AS n FROM dvol GROUP BY 1")) + "\n")

    lines.append("\n## Funding row counts\n")
    lines.append(str(q("SELECT symbol, COUNT(*) AS n FROM funding GROUP BY 1")) + "\n")

    lines.append(
        "\n*Note: No returns, realised variance levels, or volume levels are reported "
        "for the test window.*\n"
    )

    path = cfg.DOCS / "qa_report.md"
    path.write_text("".join(lines), encoding="utf-8")
    log.info("Wrote %s", path)
    con.close()


if __name__ == "__main__":
    main()
