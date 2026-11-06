"""Offline tests for the expanded Seattle, Through the Numbers computational research."""
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
import numpy as np
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import eight_experiments_stats as st
import eight_experiments_money as mo
import eight_experiments_maps as mp

class RemainingExperimentsTest(unittest.TestCase):
    def test_intervals_are_out_of_group_and_finite(self):
        rng=np.random.default_rng(7)
        rows=[]
        for i in range(100):
            row={f:float(rng.uniform(.25,.75)) for f in st.NUMERIC_FEATURES}
            row.update({"spatial_group":str(i%10),"general_votes":"300",
                        "actual_harrell_share":str(.4+.1*row["primary_harrell_share"])})
            rows.append(row)
        pred,low,high,summary=st.three_way_intervals(rows)
        self.assertEqual(summary["precincts"],100)
        self.assertTrue(((low<=pred)&(pred<=high)).all())
        self.assertEqual(len(summary["calibration_fold_sizes"]),5)

    def test_max_pair_simulation_respects_selection(self):
        rows=[{"general_votes":"200","expected_primary_plus_census_pct":"50",
               "actual_harrell_share":v} for v in ("0.3","0.5","0.7")]
        links=np.array([[0,1],[1,2],[0,2]])
        m,binom,shuffle=st.simulate_maxima(rows,links,draws=30,seed=42)
        self.assertEqual(m["candidate_pairs"],3)
        self.assertAlmostEqual(m["observed_max_gap_pp"],40)
        self.assertEqual(len(binom),30)
        self.assertEqual(len(shuffle),30)

    def test_eco_same_marginals_different_intersections(self):
        low=mo.ballot_cross_tab(overlap=30)
        high=mo.ballot_cross_tab(overlap=60)
        self.assertEqual(sum(low),100)
        self.assertEqual(sum(high),100)
        self.assertEqual(low[0],30)
        self.assertEqual(high[0],60)
        self.assertEqual(sum(low[:2]),60)
        self.assertEqual(low[0]+low[2],70)
        with self.assertRaises(ValueError):
            mo.ballot_cross_tab(overlap=10)

    def test_community_graph_is_spatial_and_repeatable(self):
        ids=[str(i) for i in range(9)]
        shapes={str(i):box(i%3,(i//3),i%3+1,i//3+1) for i in range(9)}
        edges=mp.precinct_edges(ids,shapes,min_shared_feet=.9)
        self.assertEqual(len(edges),12)
        x=np.array([[i/10]*6 for i in range(9)])
        g=mp.create_similarity_graph(x,edges)
        self.assertEqual(g.number_of_edges(),12)
        one=mp.detect_communities(g,seed=2025)
        two=mp.detect_communities(g,seed=2025)
        self.assertEqual(one,two)
        scenarios={"all":one,"separate":{i:i for i in range(9)}}
        categories=mp.share_border_sensitivity(edges,scenarios)
        self.assertEqual(len(categories),12)
        self.assertTrue(set(categories)<=set(["Model-sensitive border","Stable dividing border","Stable internal border"]))

    def test_all_static_figures_are_valid_svg(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            money=mo.figure_funding(root/"funds.svg")
            stats=mo.figure_ecological(root/"eco.svg")
            self.assertGreater(money["Katie Wilson"]["voucher_percent"],money["Bruce Harrell"]["voucher_percent"])
            self.assertEqual(stats["possible_overlap_min_pct"],30)
            ElementTree.parse(root/"funds.svg")
            ElementTree.parse(root/"eco.svg")
