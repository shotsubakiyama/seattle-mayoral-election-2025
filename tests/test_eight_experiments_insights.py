"""Offline validation for geographic baseline and reader-first election figures."""
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from eight_experiments_insights import (
    cross_race_alignment,plot_alignment,miss_categories,plot_miss_map,
    geography_only_comparison,plot_geography_vs_vote
)
from eight_experiments_maps import precinct_edges,create_similarity_graph,detect_communities


class NewInsightsTests(unittest.TestCase):
    def test_correlation_is_precinct_level_and_different_majority_is_separate(self):
        a=np.array([.15,.30,.48,.65,.78,.92])
        x=np.column_stack([a,a,.5+.2*a,1-a,a**2,.35+.3*a])
        metrics=cross_race_alignment(x)
        self.assertEqual(len(metrics),5)
        self.assertAlmostEqual(metrics[0]["correlation"],1.0,places=2)
        self.assertGreater(metrics[0]["different_majority_pct"],-0.01)
        self.assertAlmostEqual(metrics[2]["correlation"],-1.0,places=2)
        self.assertGreater(metrics[2]["different_majority_pct"],80)

    def test_map_miss_respects_prediction_band(self):
        rows=[
            {"precinct_id":"1","actual_harrell_share":"0.51"},
            {"precinct_id":"2","actual_harrell_share":"0.57"},
            {"precinct_id":"3","actual_harrell_share":"0.69"},
        ]
        pred=np.array([.5,.5,.5])
        lo=np.array([.4,.4,.4]); hi=np.array([.6,.6,.6])
        self.assertEqual(miss_categories(rows,pred,lo,hi),{"1":0,"2":1,"3":2})

    def test_geographic_baseline_is_deterministic_and_checks_borders(self):
        ids=[str(i) for i in range(12)]
        shapes={str(i):box((i%4)*100,(i//4)*100,(i%4+1)*100,(i//4+1)*100)
                for i in range(12)}
        edges=precinct_edges(ids,shapes)
        features=np.array([[((i%4)/4),((i//4)/3),((i%4)/4),.5,.4,.8] for i in range(12)])
        electoral=detect_communities(create_similarity_graph(features,edges),
                                     resolution=.62,seed=2025)
        geo,summary=geography_only_comparison(features,edges,electoral)
        self.assertEqual(set(geo),set(range(12)))
        self.assertEqual(summary["shared_borders"],len(edges))
        self.assertLessEqual(summary["border_status_changes_pct"],100)
        self.assertGreaterEqual(summary["border_status_changes_pct"],0)
        self.assertEqual(summary["voting_informed_groups"],len(set(electoral.values())))
        self.assertEqual(
            summary["adjusted_rand_geography_vs_voting"],
            geography_only_comparison(features,edges,electoral)[1][
                "adjusted_rand_geography_vs_voting"])

    def test_all_new_graphics_render(self):
        a=np.array([.1,.3,.5,.7,.9,.99])
        data=cross_race_alignment(np.column_stack([a,a,a,a,a,a]))
        shapes={"1":box(0,0,100,100),"2":box(100,0,200,100)}
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            plot_alignment(data,p/"correlation.svg")
            m=plot_miss_map(shapes,{"1":0,"2":2},p/"misses.png")
            self.assertEqual(m["outside_range"],1)
            self.assertTrue((p/"correlation.svg").is_file())
            self.assertGreater((p/"misses.png").stat().st_size,500)
            edges=precinct_edges(["1","2"],shapes)
            summary={"border_status_changes_pct":100.0,"shared_borders":1}
            plot_geography_vs_vote(shapes,["1","2"],edges,
                {0:0,1:1},{0:0,1:0},summary,p/"baseline.png")
            self.assertTrue((p/"baseline.png").is_file())


if __name__ == "__main__":
    unittest.main()
