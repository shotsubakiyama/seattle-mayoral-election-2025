"""Offline checks for spatial-neighbor and FDR logic."""
import sys
import unittest
from pathlib import Path
import numpy as np
from shapely.geometry import box
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from spatial_residual_clusters import fdr_bh, neighbors, draw_without_replacement, permutation_moran, run_analysis

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


class MonteCarloTests(unittest.TestCase):
    def test_uniform_samples_contain_no_duplicate_neighbors(self):
        rng = np.random.default_rng(123)
        samples = draw_without_replacement(rng, 60, 5, 300)
        self.assertEqual(samples.shape, (300, 5))
        for row in samples:
            self.assertEqual(len(set(row.tolist())), 5)
            self.assertTrue((row < 60).all())

    def test_structured_spatial_signal_and_island(self):
        polygons, rows = {}, []
        for y in range(8):
            for x in range(8):
                pid = str(y * 8 + x + 1)
                polygons[pid] = box(x * 200, y * 200, (x+1) * 200, (y+1) * 200)
                rows.append({"precinct_id": pid, "residual_pp": 8 if x < 4 else -8,
                             "general_votes": 180})
        polygons["65"] = box(3000, 3000, 3200, 3200)
        rows.append({"precinct_id": "65", "residual_pp": 2, "general_votes": 125})
        result, global_i, global_p, connected, islands = run_analysis(
            rows, polygons, permutations=999)
        self.assertEqual(connected, 64)
        self.assertEqual(islands, 1)
        self.assertEqual(result["65"]["cluster"], "No eligible neighbors")
        self.assertGreater(global_i, .35)
        self.assertLess(global_p, .05)

    def test_permutation_results_are_reproducible(self):
        ids = [str(i) for i in range(1, 41)]
        graph = {pid: [ids[(j + 1) % 40], ids[(j - 1) % 40]]
                 for j, pid in enumerate(ids)}
        values = np.linspace(-3, 3, len(ids))
        first = permutation_moran(values, graph, ids, permutations=99, seed=12)
        second = permutation_moran(values, graph, ids, permutations=99, seed=12)
        for a, b in zip(first, second):
            np.testing.assert_array_equal(a, b)
