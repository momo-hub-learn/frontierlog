"""Independent calendar landmarks and read-only/export behavior checks."""

import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("calendar_plan.py")
SPEC = importlib.util.spec_from_file_location("calendar_plan", MODULE_PATH)
calendar = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(calendar)


class CalendarGeometryTests(unittest.TestCase):
    def test_full_year_unique_chronological_and_exact_counts(self):
        plan = calendar.build_plan()
        self.assertEqual(len(plan), 365)
        dates = [record["date"] for record in plan]
        self.assertEqual(len(set(dates)), 365)
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(dates[0], "2027-01-01")
        self.assertEqual(dates[-1], "2027-12-31")
        self.assertTrue(all(date.fromisoformat(value).year == 2027 for value in dates))
        self.assertEqual(sum(record["lit"] for record in plan), 111)
        self.assertEqual(sum(record["extra_commits"] for record in plan), 2220)
        self.assertTrue(all(record["extra_commits"] == (20 if record["lit"] else 0) for record in plan))

    def test_independent_monthly_counts(self):
        expected = (0, 10, 16, 9, 10, 9, 10, 11, 11, 18, 7, 0)
        actual = tuple(
            sum(record["lit"] for record in calendar.build_plan() if int(record["date"][5:7]) == month)
            for month in range(1, 13)
        )
        self.assertEqual(actual, expected)

    def test_known_grid_and_text_boundaries(self):
        metadata = calendar.build_metadata()
        self.assertEqual(metadata["grid_start"], "2026-12-27")
        self.assertEqual(metadata["grid_end"], "2028-01-01")
        self.assertEqual(metadata["grid_columns"], 53)
        self.assertEqual(metadata["text_width_columns"], 41)
        self.assertEqual(metadata["left_padding_columns"], 6)
        self.assertEqual(metadata["right_padding_columns"], 6)
        self.assertEqual(metadata["first_lit_date"], "2027-02-07")
        self.assertEqual(metadata["last_lit_date"], "2027-11-20")
        self.assertEqual(metadata["blank_days"], 254)
        self.assertEqual(metadata["total_extra_commits"], 2220)

    def test_friday_year_edges_and_first_lit_sunday(self):
        jan1 = calendar.day("2027-01-01")
        self.assertEqual((jan1["row"], jan1["col"], jan1["lit"]), (5, 0, False))
        dec31 = calendar.day(date(2027, 12, 31))
        self.assertEqual((dec31["row"], dec31["col"], dec31["lit"]), (5, 52, False))
        feb7 = calendar.day("2027-02-07")
        self.assertEqual((feb7["row"], feb7["col"], feb7["letter"], feb7["lit"]), (0, 6, "W", True))
        self.assertEqual(feb7["extra_commits"], 20)

    def test_c_opening_remains_unlit_and_o_is_closed(self):
        for value in ("2027-07-13", "2027-07-14", "2027-07-15"):
            with self.subTest(value=value):
                record = calendar.day(value)
                self.assertEqual(record["letter"], "C")
                self.assertFalse(record["lit"])
                self.assertEqual(record["extra_commits"], 0)
        for value in ("2027-08-24", "2027-08-25", "2027-08-26"):
            with self.subTest(value=value):
                record = calendar.day(value)
                self.assertEqual(record["letter"], "O")
                self.assertTrue(record["lit"])

    def test_last_e_pixel_and_interletter_gap(self):
        nov20 = calendar.day("2027-11-20")
        self.assertEqual((nov20["row"], nov20["col"], nov20["letter"], nov20["lit"]), (6, 46, "E", True))
        for delta in range(7):
            record = calendar.day(date(2027, 3, 14) + timedelta(days=delta))
            self.assertIsNone(record["letter"])
            self.assertFalse(record["lit"])

    def test_lit_dates_exports_and_safe_outside_year(self):
        self.assertEqual(tuple(calendar.lit_dates()), calendar.LIT_DATES)
        self.assertEqual(len(calendar.LIT_DATES), 111)
        for value in ("2026-12-31", "2028-01-01"):
            record = calendar.day(value)
            self.assertEqual(record["extra_commits"], 0)
            self.assertFalse(record["lit"])
            self.assertIsNone(record["row"])
            self.assertIsNone(record["col"])


class TimeAndInputTests(unittest.TestCase):
    def test_beijing_utc_boundary(self):
        beijing = timezone(timedelta(hours=8))
        before = datetime(2027, 2, 7, 7, 59, 59, tzinfo=beijing)
        after = datetime(2027, 2, 7, 8, 0, 0, tzinfo=beijing)
        self.assertEqual(calendar.utc_date(before), date(2027, 2, 6))
        self.assertEqual(calendar.utc_date(after), date(2027, 2, 7))
        self.assertFalse(calendar.day(calendar.utc_date(before))["lit"])
        self.assertTrue(calendar.day(calendar.utc_date(after))["lit"])

    def test_late_utc_stays_on_utc_date(self):
        moment = datetime(2027, 2, 7, 23, 59, 59, tzinfo=timezone.utc)
        self.assertEqual(calendar.utc_date(moment), date(2027, 2, 7))
        self.assertEqual(moment.astimezone(timezone(timedelta(hours=8))).date(), date(2027, 2, 8))

    def test_ambiguous_or_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            calendar.utc_date(datetime(2027, 2, 7))
        with self.assertRaises(TypeError):
            calendar.day(datetime(2027, 2, 7, tzinfo=timezone.utc))
        for invalid in ("20270207", "2027-02-30", "2027-2-7"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                calendar.day(invalid)
        for invalid in (-1, True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                calendar.build_plan(extra_commits_per_lit_day=invalid)

    def test_metadata_rejects_truncated_or_modified_plan(self):
        plan = calendar.build_plan()
        with self.assertRaises(ValueError):
            calendar.build_metadata(plan[:-1])
        plan[0]["extra_commits"] = 20
        with self.assertRaises(ValueError):
            calendar.build_metadata(plan)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, script, cwd, *args):
        return subprocess.run(
            [sys.executable, "-B", str(script), *args],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=True,
        )

    def test_today_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "calendar_plan.py"
            script.write_bytes(MODULE_PATH.read_bytes())
            before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            result = json.loads(self.run_cli(script, root, "today", "--date", "2027-02-07").stdout)
            after = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertTrue(result["read_only"])
            self.assertTrue(result["lit"])
            self.assertEqual(result["extra_commits"], 20)
            self.assertEqual(result["schedule_timezone"], "UTC")

    def test_generate_is_deterministic_and_uses_script_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script_dir = root / "script"
            other_dir = root / "other"
            script_dir.mkdir()
            other_dir.mkdir()
            script = script_dir / "calendar_plan.py"
            script.write_bytes(MODULE_PATH.read_bytes())
            self.run_cli(script, other_dir, "generate")
            json_path = script_dir / "plan.json"
            csv_path = script_dir / "dates.csv"
            first = (json_path.read_bytes(), csv_path.read_bytes())
            self.run_cli(script, other_dir, "generate")
            self.assertEqual(first, (json_path.read_bytes(), csv_path.read_bytes()))
            self.assertEqual(list(other_dir.iterdir()), [])
            payload = json.loads(first[0])
            self.assertEqual(len(payload["days"]), 365)
            self.assertEqual(payload["metadata"]["total_extra_commits"], 2220)
            with csv_path.open(newline="", encoding="utf-8") as handle:
                records = list(csv.DictReader(handle))
            self.assertEqual(len(records), 365)
            self.assertEqual(sum(record["lit"] == "true" for record in records), 111)
            self.assertEqual(sum(int(record["extra_commits"]) for record in records), 2220)


if __name__ == "__main__":
    unittest.main()
