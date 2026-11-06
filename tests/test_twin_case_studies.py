"""Offline tests for historical twins case-study assembly and plotting."""
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import twin_case_studies as cases


class TwinCaseTests(unittest.TestCase):
    def fixtures(self):
        model = [
            {"precinct_id":"1246","primary_harrell_share":".50",
             "actual_harrell_share":".47","general_votes":"247","primary_finalist_votes":"130"},
            {"precinct_id":"1464","primary_harrell_share":".54",
             "actual_harrell_share":".64","general_votes":"294","primary_finalist_votes":"150"},
        ]
        history = [
            {"precinct_id":"1246","stable_boundary":"True",
             "harrell_share_2021":".61","turnout_2021":".60",
             "turnout_2025":".62","two_candidate_votes_2021":"200"},
            {"precinct_id":"1464","stable_boundary":"True",
             "harrell_share_2021":".62","turnout_2021":".71",
             "turnout_2025":".77","two_candidate_votes_2021":"250"},
        ]
        twins = [{"precinct_a":"1246","precinct_b":"1464"}]
        labels = [
            {"precinct_id":"1246","cra_name":"Highland Park"},
            {"precinct_id":"1464","cra_name":"Junction-Genesee Hill"},
        ]
        return model, history, twins, labels

    def test_prepare_and_vote_gaps(self):
        parts=self.fixtures()
        result=cases.prepare_cases(*parts,selected=[("1246","1464","West Seattle")])
        self.assertEqual(len(result),1)
        self.assertAlmostEqual(result[0]["gap"][0],1)
        self.assertAlmostEqual(result[0]["gap"][1],4)
        self.assertAlmostEqual(result[0]["gap"][2],17)

    def test_reject_unverified_pair(self):
        model, history, twins, areas=self.fixtures()
        with self.assertRaises(ValueError):
            cases.prepare_cases(model,history,[],areas,selected=[("1246","1464","West Seattle")])

    def test_reject_nonstable_precinct(self):
        model, history, twins, areas=self.fixtures()
        history[0]["stable_boundary"]="False"
        with self.assertRaises(ValueError):
            cases.prepare_cases(model,history,twins,areas,selected=[("1246","1464","West Seattle")])

    def test_svg_and_report(self):
        selected=cases.prepare_cases(*self.fixtures(),selected=[("1246","1464","West Seattle")])
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            svg=folder/"test.svg"
            md=folder/"test.md"
            cases.draw_cases(selected,svg)
            cases.write_report(selected,md)
            ElementTree.parse(svg)
            self.assertIn("17.0",md.read_text(encoding="utf-8"))
            self.assertIn("Turnout",md.read_text(encoding="utf-8").title())


if __name__=="__main__":
    unittest.main()
