"""Tests for the reader-friendly chart builder; no downloaded election data required."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import build_story_visuals as story
import model_precinct_surprises as model


class NarrativeFigureTests(unittest.TestCase):
    def test_three_errors_have_clear_meanings(self):
        rows = [
            {"general_votes":100,"actual_harrell_share":.6,
             "primary_harrell_share":.5,"expected_primary_only_pct":55,
             "expected_primary_plus_census_pct":58},
            {"general_votes":300,"actual_harrell_share":.4,
             "primary_harrell_share":.3,"expected_primary_only_pct":45,
             "expected_primary_plus_census_pct":42},
        ]
        actual = story.weighted_mae_comparison(rows)
        for value, wanted in zip(actual,[10,5,2]):
            self.assertAlmostEqual(value,wanted)

    def test_story_intro_svg_is_valid_and_honest_about_retrospective(self):
        svg = story.prediction_flow_svg()
        ElementTree.fromstring(svg)
        self.assertIn("retrospective",svg.lower())
        self.assertIn("55%",svg)
        self.assertIn("hypothetical",svg.lower())

    def test_twin_profile_uses_distinct_highlight_and_census_values(self):
        first = dict(precinct_id="1246",year2021=61.1,august=52.4,other=12.3,
                     voting_age=84.5,occupied=91.2,density=8400,
                     november=46.6,turnout=62.4)
        second = dict(precinct_id="1464",year2021=61.9,august=57.2,other=13.1,
                      voting_age=85.0,occupied=94.2,density=7600,
                      november=63.9,turnout=76.6)
        svg = story.twin_profile_svg([first,second])
        ElementTree.fromstring(svg)
        for value in ("61.1%","61.9%","46.6%","63.9%","17.3"):
            self.assertIn(value,svg)
        with self.assertRaises(ValueError):
            story.twin_profile_svg([second,first])

    def test_outliers_require_labels_and_votes(self):
        names={}
        rows=[]
        for i in range(12):
            pid=str(i+1)
            names[pid]=f"Area {pid}"
            rows.append(dict(precinct_id=pid,general_votes="220",
                             residual_pp=str(12-i if i<6 else -(i+1))))
        chosen=story.find_labeled_outliers(rows,names)
        self.assertEqual(len(chosen),8)
        self.assertGreater(chosen[0][2],0)
        self.assertLess(chosen[-1][2],0)

    def test_ablation_removes_one_feature_per_run(self):
        example=[{"precinct_id":"1"}]
        with patch.object(model,"cross_validate",return_value=(None,.03)) as cv:
            values,full=story.census_ablation(example)
        self.assertEqual(cv.call_count,4)
        self.assertAlmostEqual(full,3)
        self.assertEqual(len(values),3)
        original=set(model.NUMERIC_FEATURES)
        for call in list(cv.call_args_list)[1:]:
            features=call.args[1]
            self.assertEqual(len(features),len(original)-1)
            self.assertEqual(len(original-set(features)),1)

    def test_rendered_charts_are_valid_svg(self):
        pair=[
            dict(precinct_id="1246",year2021=61.1,august=52.4,other=12.3,
                 voting_age=84.5,occupied=91.2,density=8400,november=46.6,turnout=62.4),
            dict(precinct_id="1464",year2021=61.9,august=57.2,other=13.1,
                 voting_age=85.0,occupied=94.2,density=7600,november=63.9,turnout=76.6),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            story.render_mae([5.32,3.39,3.01],1006,folder/"mae.svg")
            story.render_outliers(
                [("1","Highland Park",12),("2","Queen Anne",10),
                 ("3","Ravenna",9),("4","South Beacon",8),
                 ("5","Wallingford",-9),("6","Pinehurst",-10),
                 ("7","Uptown",-11),("8","Delridge",-12)],
                folder/"outliers.svg")
            story.render_ablation([("vap_ratio",.08),("occupancy_ratio",-.02),("log_pop_density",.04)],
                                  folder/"ablation.svg")
            for fn in ("mae.svg","outliers.svg","ablation.svg"):
                ElementTree.parse(folder/fn)


if __name__=="__main__":
    unittest.main()
