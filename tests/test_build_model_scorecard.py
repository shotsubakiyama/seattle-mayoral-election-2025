"""Offline tests for the article scorecard chart."""
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from build_model_scorecard import errors, svg_document


class ScorecardTests(unittest.TestCase):
    def test_weighted_error(self):
        data = [
            dict(precinct_id="1", general_votes=100, actual_harrell_share=.6,
                 primary_harrell_share=.5, expected_primary_only_pct=55,
                 expected_primary_plus_census_pct=58),
            dict(precinct_id="2", general_votes=300, actual_harrell_share=.4,
                 primary_harrell_share=.2, expected_primary_only_pct=30,
                 expected_primary_plus_census_pct=35),
        ]
        actual=errors(data)
        self.assertAlmostEqual(actual[0],17.5)
        self.assertAlmostEqual(actual[1],8.75)
        self.assertAlmostEqual(actual[2],4.25)

    def test_svg_valid(self):
        doc = svg_document([5.32,3.39,3.01],1006)
        ElementTree.fromstring(doc)
        self.assertIn("1,006 Seattle precincts",doc)
        self.assertIn("3.01",doc)
        self.assertIn("Lower is better",doc)

    def test_bad_inputs_rejected(self):
        with self.assertRaises(ValueError):
            errors([])
        with self.assertRaises(ValueError):
            svg_document([12,3,2],100)
