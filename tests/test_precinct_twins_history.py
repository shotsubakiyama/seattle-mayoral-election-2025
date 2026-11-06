"""Offline checks for historical matching and research outputs."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from precinct_twins import CALIPERS, choose_pairs
import precinct_twins_history as history


class HistoricalTwinsTests(unittest.TestCase):
    def sample(self, historically_split=False):
        rows, shapes = [], {}
        for j in range(40):
            pid = str(2100+j)
            first = j < 20
            rows.append({
                "precinct_id": pid, "general_votes": 220,
                "primary_harrell_share": .5, "primary_other_share": .12,
                "vap_ratio": .8, "occupancy_ratio": .9,
                "log_pop_density": 8.0,
                "historical_harrell_share": (.35 if first else .65) if historically_split else .5,
                "votes_2021": 215,
                "actual_harrell_share": .3 if first else .7,
            })
            shapes[pid] = box(j * 7000, 0, j*7000+500, 500)
        return rows, shapes

    def test_historical_caliper_rejects_preexisting_divide(self):
        rows, shapes = self.sample(historically_split=True)
        old_pairs, _ = choose_pairs(rows, shapes, feature_calipers=CALIPERS)
        new_pairs, _ = choose_pairs(rows, shapes, feature_calipers=history.HISTORY_CALIPERS)
        self.assertGreater(len(old_pairs), 0)
        self.assertEqual(new_pairs, [])

    def test_tightly_matched_pre_november_pairs_can_be_found(self):
        rows, shapes = self.sample()
        pairs, counts = choose_pairs(rows, shapes, feature_calipers=history.HISTORY_CALIPERS)
        self.assertGreater(counts["candidates"], 0)
        self.assertGreater(len(pairs), 0)
        enriched = history.enrich_pairs(pairs, {r["precinct_id"]: r for r in rows})
        self.assertTrue(all(p["gap_2021_pp"] < .01 for p in enriched))
        self.assertTrue(all(p["november_gap_pp"] > 30 for p in enriched))

    def test_stable_history_filter_and_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "history.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "precinct_id", "stable_boundary", "two_candidate_votes_2021", "harrell_share_2021"
                ])
                w.writeheader()
                w.writerow({"precinct_id":"7","stable_boundary":"True","two_candidate_votes_2021":"250","harrell_share_2021":".55"})
                w.writerow({"precinct_id":"8","stable_boundary":"False","two_candidate_votes_2021":"300","harrell_share_2021":".60"})
                w.writerow({"precinct_id":"9","stable_boundary":"True","two_candidate_votes_2021":"50","harrell_share_2021":".30"})
            found = history.load_historical_panel(csv_path)
            self.assertEqual(set(found), {"7"})
            joined = history.assemble_history([{"precinct_id":"7"},{"precinct_id":"8"}], found)
            self.assertEqual(len(joined), 1)
            self.assertAlmostEqual(joined[0]["historical_harrell_share"], .55)

    def test_figure_and_csv_are_valid(self):
        rows, shapes = self.sample()
        pairs, counts = choose_pairs(rows, shapes, feature_calipers=history.HISTORY_CALIPERS)
        enriched = history.enrich_pairs(pairs, {r["precinct_id"]: r for r in rows})
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with (patch.object(history, "FIGURE", dest/"figure.svg"),
                  patch.object(history, "REPORT", dest/"report.md"),
                  patch.object(history, "OUTPUT", dest/"pairs.csv")):
                history.plot_gap_progression(enriched, {})
                history.write_report(enriched, counts, len(rows))
                ElementTree.parse(dest/"figure.svg")
                report = (dest/"report.md").read_text()
                self.assertIn("2021 Harrell", report)
                self.assertIn("November", report)
                with (dest/"pairs.csv").open(newline="", encoding="utf-8") as f:
                    self.assertEqual(len(list(csv.DictReader(f))), len(enriched))


if __name__=="__main__":
    unittest.main()
