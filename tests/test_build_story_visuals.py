"""Smoke tests for the new editorial figures; use synthetic data only."""
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_story_visuals as story


class StoryVisualsTests(unittest.TestCase):
    def test_weighted_prediction_errors_use_vote_counts(self):
        rows = [
            {"precinct_id":"1", "general_votes":"100", "actual_harrell_share":".60",
             "primary_harrell_share":".50", "expected_primary_only_pct":"55",
             "expected_primary_plus_census_pct":"58"},
            {"precinct_id":"2", "general_votes":"300", "actual_harrell_share":".40",
             "primary_harrell_share":".20", "expected_primary_only_pct":"30",
             "expected_primary_plus_census_pct":"35"},
        ]
        np.testing.assert_allclose(story.weighted_errors(rows),[17.5,8.75,4.25])

    def test_diagram_is_valid_svg_and_says_example(self):
        result=story.prediction_explainer()
        ElementTree.fromstring(result)
        self.assertIn("made-up example", result)
        self.assertIn("retrospective test", result.lower())

    def test_outliers_separate_over_and_under_predictions(self):
        rows=[]
        for i in range(30):
            rows.append({"precinct_id":str(i),"general_votes":"200",
                         "residual_pp":str(i-15)})
        area={str(i):"Area" for i in range(30)}
        chosen=story.choose_outliers(rows,area,3)
        self.assertEqual(len(chosen),6)
        self.assertTrue(all(x[2]>0 for x in chosen[:3]))
        self.assertTrue(all(x[2]<0 for x in chosen[3:]))

    def test_twin_profiles_reject_changed_boundaries(self):
        model=[
            {"precinct_id":pid, "primary_harrell_share":".50", "primary_other_share":".16",
             "vap_ratio":".75", "occupancy_ratio":".91", "log_pop_density":"8",
             "actual_harrell_share":nov}
            for pid,nov in (("1246",".466"),("1464",".639"))
        ]
        old=[
            {"precinct_id":pid, "harrell_share_2021":prior,
             "turnout_2025":turnout,"stable_boundary":"True"}
            for pid,prior,turnout in (("1246",".611",".624"),("1464",".619",".766"))
        ]
        result=story.twin_features(model,old)
        self.assertAlmostEqual(result[0]["prior"],61.1)
        self.assertAlmostEqual(result[1]["november"],63.9)
        ElementTree.fromstring(story.twin_profile_svg(result))
        old[0]["stable_boundary"]="False"
        with self.assertRaises(ValueError):
            story.twin_features(model,old)

    def test_all_matplotlib_exports(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            story.render_error_chart([5.32,3.39,3.01],1006,folder/"errors.svg")
            outliers=[(str(i),"Neighborhood",v,200) for i,v in
                      enumerate([12,11,10,9,-12,-11,-10,-9])]
            story.render_outlier_chart(outliers,folder/"outliers.svg")
            story.render_feature_ablation([("log_pop_density",.01),
                                          ("vap_ratio",-.02),
                                          ("occupancy_ratio",.07)], folder/"ablation.svg")
            for filename in ("errors.svg","outliers.svg","ablation.svg"):
                ElementTree.parse(folder/filename)

    def test_feature_ablation_runs_on_spatially_held_out_synthetic_data(self):
        rows=[]
        for i in range(60):
            primary=.25+.005*i
            rows.append({"primary_harrell_share":primary,
                         "primary_other_share":.08,
                         "vap_ratio":.73+(i%3)*.01,
                         "occupancy_ratio":.89+(i%4)*.01,
                         "log_pop_density":8.0+(i%5)*.1,
                         "actual_harrell_share":primary+.04,
                         "general_votes":175+i,
                         "spatial_group":str(i//10)})
        result,full=story.leave_one_feature_out(rows)
        self.assertEqual(len(result),3)
        self.assertTrue(all(np.isfinite(value) for _,value in result))
        self.assertGreaterEqual(full,0)


if __name__ == "__main__":
    unittest.main()
