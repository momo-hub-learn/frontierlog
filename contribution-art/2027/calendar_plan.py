#!/usr/bin/env python3
"""Deterministic 2027 WELCOME calendar; this module never creates commits.

Calendar rows are Sunday through Saturday. Art dates use UTC explicitly;
ordinary development can continue on every day, including unlit art dates.
Run ``generate`` to export the plan beside this file, or ``today`` to inspect
one date without writing files.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict


YEAR = 2027
TEXT = "WELCOME"
START_COLUMN = 6
GLYPH_WIDTH = 5
GLYPH_HEIGHT = 7
LETTER_SPACING = 1
ART_COMMITS_PER_LIT_DAY = 20
SCHEDULE_TIMEZONE = "UTC"
ROW_NAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")

# Rows run top to bottom (Sunday -> Saturday); columns run left to right.
GLYPHS = {
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
}

YEAR_START = date(YEAR, 1, 1)
YEAR_END = date(YEAR, 12, 31)
GRID_START = YEAR_START - timedelta(days=(YEAR_START.weekday() + 1) % 7)
GRID_COLUMNS = ((YEAR_END - GRID_START).days // 7) + 1
GRID_END = GRID_START + timedelta(days=GRID_COLUMNS * 7 - 1)
TEXT_WIDTH_COLUMNS = len(TEXT) * GLYPH_WIDTH + (len(TEXT) - 1) * LETTER_SPACING
END_COLUMN = START_COLUMN + TEXT_WIDTH_COLUMNS - 1
CSV_FIELDS = ("date", "row", "col", "letter", "lit", "extra_commits")


class DayRecord(TypedDict):
    date: str
    row: int | None
    col: int | None
    letter: str | None
    lit: bool
    extra_commits: int


def utc_date(moment: datetime | None = None) -> date:
    """Convert an aware instant to its UTC schedule date.

    Naive datetimes are rejected so the machine's local timezone cannot
    silently shift a target date. With no argument, read the current UTC date.
    """
    if moment is None:
        moment = datetime.now(timezone.utc)
    if not isinstance(moment, datetime):
        raise TypeError("moment must be a timezone-aware datetime")
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("moment must include a timezone; naive datetimes are ambiguous")
    return moment.astimezone(timezone.utc).date()


def _as_date(value: date | str) -> date:
    if isinstance(value, datetime):
        raise TypeError("Pass a calendar date, or convert the instant with utc_date() first")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # date.fromisoformat also accepts compact and week-date forms. This
        # public interface deliberately accepts only the documented YYYY-MM-DD.
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("date must use YYYY-MM-DD")
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("date must use YYYY-MM-DD")
        return parsed
    raise TypeError("date must be a datetime.date or YYYY-MM-DD string")


def _validate_extra_commits(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("extra_commits_per_lit_day must be a non-negative integer")


def day(
    value: date | str,
    *,
    extra_commits_per_lit_day: int = ART_COMMITS_PER_LIT_DAY,
) -> DayRecord:
    """Return one date's art allocation; outside 2027 safely returns zero.

    ``letter`` identifies the letter's rectangular block, even for an unlit
    interior pixel. It is None in spacing, padding, or outside the year.
    ``row`` and ``col`` are zero-based, and None outside 2027.
    """
    selected = _as_date(value)
    _validate_extra_commits(extra_commits_per_lit_day)
    result: DayRecord = {
        "date": selected.isoformat(),
        "row": None,
        "col": None,
        "letter": None,
        "lit": False,
        "extra_commits": 0,
    }
    if selected.year != YEAR:
        return result

    col, row = divmod((selected - GRID_START).days, GLYPH_HEIGHT)
    result["col"] = col
    result["row"] = row
    if not START_COLUMN <= col <= END_COLUMN:
        return result

    letter_index, glyph_col = divmod(col - START_COLUMN, GLYPH_WIDTH + LETTER_SPACING)
    if glyph_col >= GLYPH_WIDTH:
        return result

    letter = TEXT[letter_index]
    result["letter"] = letter
    result["lit"] = GLYPHS[letter][row][glyph_col] == "1"
    if result["lit"]:
        result["extra_commits"] = extra_commits_per_lit_day
    return result


def build_plan(
    *, extra_commits_per_lit_day: int = ART_COMMITS_PER_LIT_DAY,
) -> list[DayRecord]:
    """Return all 365 dates in chronological order, with no clock dependency."""
    _validate_extra_commits(extra_commits_per_lit_day)
    days_in_year = (YEAR_END - YEAR_START).days + 1
    return [
        day(YEAR_START + timedelta(days=offset), extra_commits_per_lit_day=extra_commits_per_lit_day)
        for offset in range(days_in_year)
    ]


def lit_dates() -> list[str]:
    """Return the 111 illuminated dates as sorted YYYY-MM-DD strings."""
    return [record["date"] for record in build_plan() if record["lit"]]


def build_metadata(plan: list[DayRecord] | None = None) -> dict:
    """Describe geometry and totals for a complete, internally consistent plan."""
    if plan is None:
        plan = build_plan()
    dates = [record["date"] for record in plan]
    expected_dates = [
        (YEAR_START + timedelta(days=offset)).isoformat()
        for offset in range((YEAR_END - YEAR_START).days + 1)
    ]
    if dates != expected_dates:
        raise ValueError("metadata requires the complete 2027 plan in chronological order")
    lit = [record for record in plan if record["lit"]]
    extra_counts = {record["extra_commits"] for record in lit}
    if len(extra_counts) != 1:
        raise ValueError("all lit dates must use the same extra commit allocation")
    per_day = next(iter(extra_counts))
    if plan != build_plan(extra_commits_per_lit_day=per_day):
        raise ValueError("plan records do not match the WELCOME glyph calendar")

    letter_blocks = []
    for index, letter in enumerate(TEXT):
        first_col = START_COLUMN + index * (GLYPH_WIDTH + LETTER_SPACING)
        last_col = first_col + GLYPH_WIDTH - 1
        letter_blocks.append({
            "letter": letter,
            "index": index,
            "start_column": first_col,
            "end_column": last_col,
            "first_date": (GRID_START + timedelta(days=first_col * 7)).isoformat(),
            "last_date": (GRID_START + timedelta(days=last_col * 7 + 6)).isoformat(),
            "lit_days": sum(row.count("1") for row in GLYPHS[letter]),
        })

    return {
        "schema_version": 1,
        "year": YEAR,
        "text": TEXT,
        "strategy": "normal_development_plus_darker_letters",
        "schedule_timezone": SCHEDULE_TIMEZONE,
        "rows": list(ROW_NAMES),
        "grid_start": GRID_START.isoformat(),
        "grid_end": GRID_END.isoformat(),
        "grid_columns": GRID_COLUMNS,
        "start_column": START_COLUMN,
        "end_column": END_COLUMN,
        "glyph_width": GLYPH_WIDTH,
        "glyph_height": GLYPH_HEIGHT,
        "letter_spacing": LETTER_SPACING,
        "text_width_columns": TEXT_WIDTH_COLUMNS,
        "left_padding_columns": START_COLUMN,
        "right_padding_columns": GRID_COLUMNS - END_COLUMN - 1,
        "art_commits_per_lit_day": per_day,
        "lit_days": len(lit),
        "blank_days": len(plan) - len(lit),
        "total_extra_commits": sum(record["extra_commits"] for record in plan),
        "first_lit_date": lit[0]["date"],
        "last_lit_date": lit[-1]["date"],
        "monthly_lit_days": {
            f"{YEAR}-{month:02d}": sum(record["date"].startswith(f"{YEAR}-{month:02d}") for record in lit)
            for month in range(1, 13)
        },
        "letter_blocks": letter_blocks,
    }


# A convenient immutable export for consumers that only need the date set.
LIT_DATES = tuple(lit_dates())


def _generate() -> dict:
    plan = build_plan()
    metadata = build_metadata(plan)
    destination = Path(__file__).resolve().parent
    json_path = destination / "plan.json"
    csv_path = destination / "dates.csv"
    json_path.write_text(
        json.dumps({"metadata": metadata, "days": plan}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for record in plan:
            writer.writerow({**record, "lit": "true" if record["lit"] else "false"})
    return {
        "plan_json": str(json_path),
        "dates_csv": str(csv_path),
        "lit_days": metadata["lit_days"],
        "total_extra_commits": metadata["total_extra_commits"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("generate", help="Write plan.json and dates.csv beside this script")
    today_parser = commands.add_parser("today", help="Read-only explanation of one UTC schedule date")
    today_parser.add_argument("--date", metavar="YYYY-MM-DD", help="Inspect this date instead of the current UTC date")
    args = parser.parse_args(argv)

    if args.command == "generate":
        print(json.dumps(_generate(), indent=2))
        return 0

    try:
        record = day(args.date if args.date is not None else utc_date())
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    if record["lit"]:
        explanation = f"Lit {record['letter']} pixel: {record['extra_commits']} planned extra art commits; normal development continues."
    elif record["row"] is None:
        explanation = "Outside 2027: no extra art commits are scheduled."
    else:
        explanation = "Unlit art pixel: no extra art commits are scheduled; normal development continues."
    print(json.dumps({
        "schedule_timezone": SCHEDULE_TIMEZONE,
        "read_only": True,
        **record,
        "explanation": explanation,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
