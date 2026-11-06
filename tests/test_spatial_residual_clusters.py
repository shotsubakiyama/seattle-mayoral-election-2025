"""Offline checks for spatial-neighbor and FDR logic."""
import sys
import unittest
from pathlib import Path
import numpy as np
from shapely.geometry import box
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from spatial_residual_clusters import fdr_bh, neighbors

class SpatialTests(unittest.TestCase):
    def test_adjustment(self):
        np.testing.assert_allclose(fdr_bh([.001, .02, .03, .8]), [.004, .04, .04, .8])
    def test_corner_is_not_neighbor(self):
        polygons = {"1":box(0,0,200,200), "2":box(200,0,400,200),
                    "3":box(-200,-200,0,0)}
        links=neighbors(["1","2","3"], polygons)
        self.assertEqual(links, {"1":["2"],"2":["1"],"3":[]})
    def test_min_border(self):
        polygons={"1":box(0,0,200,200),"2":box(200,0,400,200)}
        self.assertEqual(neighbors(["1","2"],polygons,min_border=250), {"1":[],"2":[]})
    def test_reject_bad_p(self):
        for vals in [[-.1,.9],[float("nan"),.5]]:
            with self.assertRaises(ValueError):
                fdr_bh(vals)
