"""Offline checks for experiments 01 and 02; official reconciliation occurs in CI."""
import csv
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import eight_experiments_opening as exp


def sample_votes():
    results={}
    for race,a,b,_,_,_ in exp.CONTESTS:
        results[race]={
            "1001":{a:20,b:80},
            "1002":{a:80,b:20},
        }
    # Correctly designate Wilson as first named candidate in mayor's race
    return results


class OpeningExperimentsTest(unittest.TestCase):
    def test_parse_official_csv_reads_seattle_total_only(self):
        with tempfile.TemporaryDirectory() as td:
            filename=Path(td)/"official.csv"
            fieldnames=["Precinct","Race","CounterGroup","CounterType","SumOfCount"]
            records=[
                ["SEA 11-1001","City of Seattle Mayor","Total","Katie Wilson","25"],
                ["SEA 11-1001","City of Seattle Mayor","Total","Bruce Harrell","75"],
                ["SEA 11-1001","City of Seattle Mayor","Total","Registered Voters","500"],
                ["SEA 11-1001","City of Seattle Mayor","Total","Write-in","4"],
                ["SEA 11-1001","City of Seattle Mayor","Not Total","Katie Wilson","999"],
                ["SEA 11-1001","City of Seattle City Attorney","Total","Erika Evans","60"],
            ]
            with filename.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow(fieldnames)
                w.writerows(records)
            vote,reg=exp.parse_official_csv(filename)
        self.assertEqual(vote["City of Seattle Mayor"]["1001"]["Katie Wilson"],25)
        self.assertEqual(reg["1001"],500)
        self.assertEqual(vote["City of Seattle City Attorney"]["1001"]["Erika Evans"],60)

    def test_certified_totals_reconciliation(self):
        votes={}
        for race,a,b,expected_a,expected_b,_ in exp.CONTESTS:
            votes[race]={"1001":{a:expected_a,b:expected_b}}
        exp.validate_contests(votes)
        key=exp.CONTESTS[1][0]
        votes[key]["1001"][exp.CONTESTS[1][1]]-=1
        with self.assertRaisesRegex(ValueError,"does not match official totals"):
            exp.validate_contests(votes)

    def test_cross_race_precinct_groups(self):
        votes=sample_votes()
        groups={"1001":"Harrell-winning precincts","1002":"Wilson-winning precincts"}
        rows=exp.cross_contest_shares(votes,groups)
        self.assertEqual(len(rows),12)
        for r in rows:
            self.assertAlmostEqual(r["share"],
                20 if r["group"]=="Harrell-winning precincts" else 80)

    def test_equal_participation_is_registered_weighted(self):
        # Synthetic data with official total mayor votes, split across 2 areas.
        race="City of Seattle Mayor"
        votes={race:{
            "1001":{"Katie Wilson":100_000,"Bruce Harrell":20_000},
            "1002":{"Katie Wilson":38_931,"Bruce Harrell":116_920},
        }}
        reg={"1001":150_000,"1002":300_000}
        x=exp.equal_participation(votes,reg)
        self.assertEqual(x["precincts"],2)
        self.assertGreater(x["actual_wilson"],x["equal_wilson"])
        expected=(150000*(100000/120000)+300000*(38931/(38931+116920)))/450000
        self.assertAlmostEqual(x["equal_wilson"],100*expected)
        reg.pop("1001")
        with self.assertRaisesRegex(ValueError,"denominator"):
            exp.equal_participation(votes,reg)

    def test_plot_svg(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            rows=exp.cross_contest_shares(sample_votes(),
                {"1001":"Harrell-winning precincts","1002":"Wilson-winning precincts"})
            x={"actual_wilson":50.36,"equal_wilson":49.95}
            exp.plot_coalitions(rows,folder/"one.svg")
            exp.plot_counterfactual(x,folder/"two.svg")
            ElementTree.parse(folder/"one.svg")
            ElementTree.parse(folder/"two.svg")

    def test_export_report_and_csv(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rows=exp.cross_contest_shares(sample_votes(),
                {"1001":"Harrell-winning precincts","1002":"Wilson-winning precincts"})
            cf={"actual_wilson":50.36,"equal_wilson":49.9,
                "precincts":1000,"registered":505393}
            with patch.object(exp,"OUTPUT",root/"processed"),patch.object(exp,"SUPPORT",root/"reports"):
                path=exp.write_outputs(rows,cf)
            self.assertTrue(path.is_file())
            self.assertIn("50.36%",(root/"reports/02_equal_participation.md").read_text())
            self.assertIn("not individual-level split-ticket", (root/"reports/01_coalitions.md").read_text().lower().replace("**",""))
