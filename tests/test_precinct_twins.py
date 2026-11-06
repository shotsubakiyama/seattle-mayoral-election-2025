"""Offline checks for the precinct-twins matching logic and figures."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import precinct_twins as twins


class PrecinctTwinTests(unittest.TestCase):
    def sample(self):
        data, shapes = [], {}
        for i in range(35):
            pid = str(2000 + i)
            data.append({
                "precinct_id": pid, "general_votes": 230,
                "primary_harrell_share": .50 + (i % 3) * .006,
                "primary_other_share": .17 + (i % 4) * .003,
                "vap_ratio": .77 + (i % 4) * .004,
                "occupancy_ratio": .87 + (i % 3) * .005,
                "log_pop_density": 7.2 + (i % 4) * .025,
                "actual_harrell_share": .52 + (.13 if i % 5 == 0
                                                 else -.13 if i % 5 == 1 else 0),
                "expected_primary_only_pct": 52.,
                "expected_primary_plus_census_pct": 51.,
            })
            shapes[pid] = box(i * 8000, 0, i * 8000 + 700, 700)
        return data, shapes

    def test_baselines_are_comparable(self):
        rows, _ = self.sample()
        errors = twins.baseline_errors(rows)
        self.assertEqual(set(errors), {"raw_primary", "trained_primary", "trained_census"})
        self.assertTrue(all(v >= 0 for v in errors.values()))

    def test_matches_are_similar_and_unique(self):
        rows, shapes = self.sample()
        pairs, counts = twins.choose_pairs(rows, shapes)
        self.assertGreater(len(pairs), 0)
        self.assertEqual(len(pairs), len({
            id for p in pairs for id in (p["precinct_a"], p["precinct_b"])
        }) // 2)
        self.assertLessEqual(len(pairs), 10)
        self.assertGreater(counts["candidates"], 0)
        for pair in pairs:
            self.assertLessEqual(pair["august_gap_pp"], 5.0001)
            self.assertGreaterEqual(pair["november_gap_pp"], 8)
            self.assertGreaterEqual(pair["straight_line_miles"], 1)

    def test_far_distance_filter(self):
        rows, shapes = self.sample()
        pairs, _ = twins.choose_pairs(rows, shapes, min_miles=99999)
        self.assertEqual(pairs, [])

    def test_november_not_used_in_feature_distance(self):
        rows, shapes = self.sample()
        pairs, _ = twins.choose_pairs(rows, shapes)
        self.assertTrue(pairs)
        for r in rows:
            r["actual_harrell_share"] = .52
        zero_gap_pairs, _ = twins.choose_pairs(rows, shapes)
        self.assertEqual(zero_gap_pairs, [])

    def test_report_and_svg(self):
        rows, shapes = self.sample()
        pairs, counts = twins.choose_pairs(rows, shapes)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with (patch.object(twins, "FIGURE", dest / "twins.svg"),
                  patch.object(twins, "PAIRS_CSV", dest / "twins.csv"),
                  patch.object(twins, "REPORT", dest / "twins.md")):
                twins.render_chart(pairs, {})
                twins.save_report(pairs, twins.baseline_errors(rows), counts)
                ElementTree.parse(dest / "twins.svg")
                self.assertIn("Precinct Twins", (dest / "twins.md").read_text())
                self.assertTrue((dest / "twins.csv").exists())


if __name__ == "__main__":
    unittest.main()
