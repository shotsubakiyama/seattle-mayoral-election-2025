"""Offline smoke checks for case-study maps; no network or downloaded data needed."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import render_fault_line_cases as cases


class CaseStudyTests(unittest.TestCase):
    def setUp(self):
        self.polygons={"1709":box(0,0,1000,1000),"1724":box(1000,0,2000,1000),
                       "9999":box(0,1000,1000,2000)}
        self.votes={"1709":{"Bruce Harrell":72,"Katie Wilson":231},
                    "1724":{"Bruce Harrell":179,"Katie Wilson":41},
                    "9999":{"Bruce Harrell":50,"Katie Wilson":50}}
        self.pair={"precinct_a":"1709","precinct_b":"1724",
                   "difference_pp":57.601,"shared_border_ft":1000.0}

    def test_color_scale_is_candidate_consistent(self):
        self.assertEqual(cases.vote_color(0),"#226990")
        self.assertEqual(cases.vote_color(50),"#f2f5f7")
        self.assertEqual(cases.vote_color(100),"#d48039")

    def test_svg_is_valid_clipped_and_labeled(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(cases,"FIGURES",Path(directory)):
                path=cases.draw_case(self.pair,self.polygons,self.votes,
                                     {"1709":"Queen Anne","1724":"Queen Anne"})
                ElementTree.parse(path)
                svg=path.read_text(encoding="utf-8")
                self.assertIn("mapclip",svg)
                self.assertIn("57.6 pp",svg)
                self.assertIn("23.8%",svg)
                self.assertIn("81.4%",svg)
                self.assertIn("Queen Anne",svg)

    def test_bad_border_is_rejected(self):
        with self.assertRaises(ValueError):
            cases.draw_case({**self.pair,"shared_border_ft":3000},
                            self.polygons,self.votes,{})


if __name__=="__main__":
    unittest.main()
