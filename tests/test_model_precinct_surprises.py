"""Synthetic tests; no Internet or election files required."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import model_precinct_surprises as m


class SurpriseModelTests(unittest.TestCase):
    def test_primary_candidate_totals_and_other_vote_share(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"primary.csv"
            with path.open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=["Precinct","Race","CounterGroup","CounterType","SumOfCount"])
                writer.writeheader()
                for candidate,count in [("Bruce Harrell",60),("Katie Wilson",40),("Third Candidate",20),("Registered Voters",400)]:
                    writer.writerow({"Precinct":"SEA 37-0001","Race":"City of Seattle Mayor", "CounterGroup":"Total", "CounterType":candidate,"SumOfCount":count})
            with patch.object(m,"PRIMARY_CERTIFIED",{"Bruce Harrell":60,"Katie Wilson":40}):
                data=m.read_primary(path)
            self.assertEqual(data["0001"]["Third Candidate"],20)
            self.assertNotIn("Registered Voters", data["0001"])

    def test_census_allocation_and_table(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"census.csv"
            with path.open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=["precinct_id","allocated_population_2020","allocated_vap_2020","allocated_housing_units_2020","allocated_occupied_housing_2020"])
                writer.writeheader()
                for item in [
                    {"precinct_id":"10","allocated_population_2020":150,"allocated_vap_2020":120,"allocated_housing_units_2020":80,"allocated_occupied_housing_2020":70},
                    {"precinct_id":"10","allocated_population_2020":50,"allocated_vap_2020":30,"allocated_housing_units_2020":20,"allocated_occupied_housing_2020":15},
                ]:
                    writer.writerow(item)
            census=m.census_by_precinct(path)
        self.assertEqual(census["10"]["pop"],200)
        self.assertEqual(census["10"]["vap"],150)
        general={"10":{"Bruce Harrell":130,"Katie Wilson":70}}
        primary={"10":{"Bruce Harrell":70,"Katie Wilson":60,"Other":20}}
        shapes={"10":box(0,0,1000,1000)}
        rows,excluded=m.build_table(general,primary,census,shapes)
        self.assertEqual(excluded,{})
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]["vap_ratio"],.75)
        self.assertAlmostEqual(rows[0]["occupancy_ratio"],.85)
        self.assertAlmostEqual(rows[0]["primary_other_share"],20/150)
        self.assertAlmostEqual(rows[0]["actual_harrell_share"],.65)

    def test_geographically_held_out_predictions_are_finite(self):
        rows=[]
        for i in range(100):
            p=.25+.005*i
            rows.append({"primary_harrell_share":p,"primary_other_share":.06,
                         "vap_ratio":.85,"occupancy_ratio":.9,
                         "log_pop_density":7.5+(i%7)/10,
                         "actual_harrell_share":min(.99,p+.025*((i%3)-1)),
                         "general_votes":150+i,
                         "spatial_group":str(i//10)})
        pred,mae=m.cross_validate(rows,m.NUMERIC_FEATURES)
        self.assertTrue(np.isfinite(pred).all())
        self.assertEqual(len(pred),100)
        self.assertGreaterEqual(mae,0)
        self.assertLess(mae,.1)

    def test_non_causal_graphics_produce_files(self):
        rows=[{"precinct_id":str(i),"actual_harrell_share":.2+.08*i} for i in range(1,7)]
        pred=np.array([.2+.08*i for i in range(1,7)])
        shapes={str(i):box(i*100,0,(i+1)*100,100) for i in range(1,7)}
        with tempfile.TemporaryDirectory() as td:
            with patch.object(m,"FIG_DIR",Path(td)):
                m.render_figures(rows,pred,shapes)
                for name in ["precinct_surprises_scatter.svg","precinct_surprises_map.svg"]:
                    text=(Path(td)/name).read_text()
                    self.assertIn("<svg",text)
                    self.assertIn("</svg>",text)


if __name__=="__main__":
    unittest.main()
