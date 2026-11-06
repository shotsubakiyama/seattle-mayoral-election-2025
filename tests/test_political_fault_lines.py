"""Synthetic tests for spatial adjacency ranking."""
import sys
import unittest
from pathlib import Path
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from political_fault_lines import find_fault_lines


class FaultLinesTests(unittest.TestCase):
    def setUp(self):
        self.polygons = {"1": box(0,0,200,200), "2": box(200,0,400,200),
                         "3": box(-200,-200,0,0)}
        self.votes = {
            "1": {"Bruce Harrell": 80, "Katie Wilson": 120},
            "2": {"Bruce Harrell": 140, "Katie Wilson": 60},
            "3": {"Bruce Harrell": 100, "Katie Wilson": 100},
        }

    def test_border_only_and_30_point_gap(self):
        rows = find_fault_lines(self.polygons, self.votes)
        self.assertEqual(len(rows), 1)
        self.assertEqual({rows[0]["precinct_a"], rows[0]["precinct_b"]}, {"1","2"})
        self.assertEqual(rows[0]["difference_pp"], 30)
        self.assertEqual(rows[0]["shared_border_ft"], 200)

    def test_exclude_low_vote_precinct(self):
        self.votes["2"] = {"Bruce Harrell": 4, "Katie Wilson": 6}
        self.assertFalse(find_fault_lines(self.polygons, self.votes))

    def test_exclude_tiny_shared_border(self):
        self.assertFalse(find_fault_lines(self.polygons, self.votes, min_border_feet=250))


if __name__ == "__main__":
    unittest.main()
