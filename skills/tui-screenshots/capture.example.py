"""REFERENCE IMPLEMENTATION -- do not run as-is.

This is a complete, working capture script taken from a real Textual project. It is
included so the tui-screenshots skill has something concrete to adapt rather than a
sketch. It imports that project's application class and builds that project's dummy
dataset, so it will not run anywhere else without edits.

Adapt: the import and app class, make_workspace(), the screens driven in capture_svgs(),
and COLS/ROWS. Keep: the seeding, the fixed terminal size, the pilot-driven navigation,
and the --out/--only flags.

Original module docstring follows.

---

Capture SVG screenshots of the data-sampler TUI.

Drives the real ``DataSamplerApp`` headlessly (Textual's pilot), builds a
throw-away workspace with a dummy folder structure and a realistic dummy
dataset, and exports each screen as an SVG directly into the output directory.

Screens captured:
  - tui-welcome  — the opening welcome menu
  - tui-columns  — columns dashboard: auto-suggested anonymizers, a multi-row
                   selection, per-stat columns, and a variance-target reduction
  - tui-report   — post-run report + source-vs-sample column histograms

Usage:
    python scripts/capture_screens.py --out docs/img
    python scripts/capture_screens.py --out docs/img --only columns

Everything is deterministic (fixed RNG seed + fixed sample seed), so re-running
regenerates identical images.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

# ~16:9 terminal (cols : 2*rows ≈ 16:9, since a cell is ~1:2). Wide enough that
# all twelve columns of the stats table — through the trailing mean/median/mode/
# sd — fit inside the 58%-width columns panel without horizontal scrolling.
COLS, ROWS = 240, 68

FIRST = ["Ava", "Liam", "Noah", "Mia", "Ethan", "Zoe", "Kai", "Ivy", "Omar",
         "Lena", "Raj", "Sofia", "Hana", "Diego", "Nora", "Theo"]
LAST = ["Kim", "Patel", "Nguyen", "Silva", "Okafor", "Rossi", "Cohen", "Haddad",
        "Ivanov", "Mensah", "Torres", "Wang", "Larsen", "Costa", "Adeyemi"]
NOTE_SAMPLES = [
    "follow up next quarter about the renewal",
    "requested an export of last year's invoices",
    "flagged by billing — duplicate account suspected",
    "VIP; route escalations to the senior team",
    "opted out of marketing emails on signup",
]


def make_workspace(root: Path) -> Path:
    """Create a dummy folder tree + a realistic dummy CSV; return the CSV path."""
    for d in ("data/raw", "data/exports", "data/archive", "reports", "scripts"):
        (root / d).mkdir(parents=True, exist_ok=True)
    # decoy files so the directory browser looks like a real project
    for f in (
        "data/exports/monthly_summary.xlsx", "data/archive/2023_backup.parquet",
        "reports/q1_findings.md", "scripts/etl.py", "README.md",
    ):
        (root / f).write_text("placeholder\n", encoding="utf-8")

    n = 1200
    rng = np.random.default_rng(7)
    df = pd.DataFrame(
        {
            "customer_id": range(100001, 100001 + n),
            "full_name": [
                f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(n)
            ],
            "email": [f"user{i:04d}@example.com" for i in range(n)],
            "region": rng.choice(
                ["North", "South", "East", "West"], n, p=[0.40, 0.30, 0.20, 0.10]
            ),
            "tier": rng.choice(["gold", "silver", "bronze"], n, p=[0.2, 0.3, 0.5]),
            "department": rng.choice(
                ["sales", "engineering", "ops", "support", "finance"], n
            ),
            "signup_date": (
                pd.Timestamp("2021-01-01")
                + pd.to_timedelta(rng.integers(0, 1500, n), unit="D")
            ),
            "salary": rng.normal(72000, 18000, n).round(0),
            "age": rng.integers(21, 65, n),
            "score": rng.normal(70, 15, n).round(1),
            "active": rng.choice([True, False], n, p=[0.7, 0.3]),
            "notes": rng.choice(NOTE_SAMPLES, n),
        }
    )
    # a few missing values so the miss% column has something to show
    df.loc[df.index[:60], "region"] = np.nan
    df.loc[df.index[:30], "salary"] = np.nan
    src = root / "data" / "raw" / "customers.csv"
    df.to_csv(src, index=False)
    return src


async def _wait_for(app, screen_type: str, tries: int = 300) -> object:
    for _ in range(tries):
        if type(app.screen).__name__ == screen_type:
            return app.screen
        await asyncio.sleep(0.02)
    raise RuntimeError(
        f"never reached {screen_type}; currently on {type(app.screen).__name__}"
    )


def _write_svg(app, out_dir: Path, name: str) -> Path:
    svg = app.export_screenshot(title="data-sampler")
    p = out_dir / f"{name}.svg"
    p.write_text(svg, encoding="utf-8")
    return p


async def capture_svgs(out_dir: Path, src: Path, only: str | None) -> list[Path]:
    from textual.widgets import DataTable, Input, Select

    from data_sampler.tui.app import DataSamplerApp

    want = lambda k: only is None or only == k
    svgs: list[Path] = []

    # ── welcome screen ───────────────────────────────────────────────────────
    if want("welcome"):
        app = DataSamplerApp()
        async with app.run_test(size=(COLS, ROWS)) as pilot:
            await _wait_for(app, "WelcomeScreen")
            for _ in range(8):
                await pilot.pause(0.05)
            svgs.append(_write_svg(app, out_dir, "tui-welcome"))

    # ── columns screen ───────────────────────────────────────────────────────
    if want("columns"):
        app = DataSamplerApp(path=str(src))
        async with app.run_test(size=(COLS, ROWS)) as pilot:
            cs = await _wait_for(app, "ColumnsScreen")
            # wait for children to mount
            for _ in range(12):
                await pilot.pause(0.05)

            cs.action_suggest()  # populate anonymizer choices

            # cursor on full_name → names config panel visible
            cs.selected = "full_name"
            cs.store.set_kind("names")
            cs.store.set_names_attr("gender", "female")
            cs.store.set_names_attr("ethnicity", "chinese")

            # multi-select numeric columns for bulk editing
            cs.selection = {"salary", "age", "score"}
            cs._anchor = "score"

            # move table cursor to full_name row
            table = cs.query_one("#columns-table", DataTable)
            table.move_cursor(row=table.get_row_index("full_name"))

            # configure runbar widgets
            cs.query_one("#reduce-mode", Select).value = "variance"
            cs.query_one("#reduce-value", Input).value = "0.9"
            cs.query_one("#count", Input).value = "200"
            cs.query_one("#seed", Input).value = "7"

            for _ in range(10):
                await pilot.pause(0.05)
            svgs.append(_write_svg(app, out_dir, "tui-columns"))

    # ── report screen ────────────────────────────────────────────────────────
    if want("report"):
        app = DataSamplerApp(path=str(src))
        async with app.run_test(size=(COLS, ROWS)) as pilot:
            cs = await _wait_for(app, "ColumnsScreen")
            for _ in range(12):
                await pilot.pause(0.05)

            cs.action_suggest()
            cs.query_one("#count", Input).value = "200"
            cs.query_one("#seed", Input).value = "7"

            for _ in range(6):
                await pilot.pause(0.05)

            cs.action_run()
            await _wait_for(app, "ReportScreen")
            for _ in range(15):
                await pilot.pause(0.05)
            svgs.append(_write_svg(app, out_dir, "tui-report"))

    return svgs


def main() -> None:
    ap = argparse.ArgumentParser(description="Capture SVG screenshots of the TUI.")
    ap.add_argument("--out", default="docs/img", help="output directory for SVGs")
    ap.add_argument(
        "--only", choices=["welcome", "columns", "report"], default=None,
        help="capture just one screen (default: all three)",
    )
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ds_shots_") as tmp:
        workspace = Path(tmp)
        src = make_workspace(workspace)
        cwd = os.getcwd()
        os.chdir(workspace)  # so the file browser roots at the dummy tree
        try:
            svgs = asyncio.run(capture_svgs(out_dir, src, args.only))
        finally:
            os.chdir(cwd)

    for p in svgs:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
