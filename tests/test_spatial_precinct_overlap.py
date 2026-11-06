"""Offline geometry smoke test; run python -m unittest discover -s tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from spatial_precinct_overlap import esri_polygon


class EsriGeometryTests(unittest.TestCase):
    def test_hole_is_subtracted(self):
        outer = [[0, 0], [0, 3], [3, 3], [3, 0], [0, 0]]
        hole = [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]
        geometry = esri_polygon({"rings": [outer, hole]})
        self.assertAlmostEqual(geometry.area, 8)

    def test_polygon_missing_exterior_rejected(self):
        hole = [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]
        with self.assertRaises(ValueError):
            esri_polygon({"rings": [hole]})


if __name__ == "__main__":
    unittest.main()
