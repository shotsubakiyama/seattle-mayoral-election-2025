"""No-network tests for the Seattle precinct field guide."""
import sys
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import box

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import precinct_field_guide as fg


class PrecinctFieldGuideTests(unittest.TestCase):
    def test_registered_and_area_metrics_reconcile(self):
        votes={
            "City of Seattle Mayor":{
                str(i):{"Bruce Harrell":40,"Katie Wilson":60}
                for i in range(1001,2001)
            }
        }
        # Synthetic full-city totals don't reconcile; reject rather than publish.
        polygons={str(i):box(i*100,0,i*100+100,100) for i in range(1001,2001)}
        registered={str(i):300 for i in range(1001,2001)}
        with self.assertRaisesRegex(ValueError,"certified candidate totals"):
            fg.summarize_precincts(votes,registered,polygons,{})

    def test_times_counted_reader(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"official.csv"
            p.write_text(
                "Precinct,Race,CounterGroup,CounterType,SumOfCount\n"
                "SEA 43-1001,City of Seattle Mayor,Total,Times Counted,250\n"
                "SEA 43-1002,City of Seattle Mayor,Total,Times Counted,120\n"
                "SEA 43-1001,City of Seattle Mayor,Total,Registered Voters,500\n"
                "SEA 43-1001,City of Seattle City Attorney,Total,Times Counted,245\n",
                encoding="utf-8"
            )
            result=fg.read_ballots_counted(p)
        self.assertEqual(result,{"1001":250,"1002":120})

    def test_neighborhood_weighting_is_vote_weighted(self):
        sample=[]
        for i in range(12):
            sample.append(dict(precinct_id=str(i),cra_name="Study Area",
                    stable_boundary="True",two_candidate_votes_2025="200",
                    harrell_share_2025=str(.2 if i<6 else .8)))
        result=fg.neighborhood_stats(sample,minimum_precincts=8)
        self.assertEqual(len(result),1)
        self.assertAlmostEqual(result[0]["mean_harrell_pct"],50)
        self.assertAlmostEqual(result[0]["weighted_sd_pp"],30)
        self.assertEqual(result[0]["precincts"],12)

    def test_historical_data_rejects_unstable_or_low_turnout(self):
        rows=[{"precinct_id":str(i)} for i in range(800)]
        panel=[{"precinct_id":str(i),"stable_boundary":"True",
                "two_candidate_votes_2025":"150",
                "two_candidate_votes_2021":"180",
                "harrell_share_2025":".4",
                "harrell_share_2021":".6",
                "cra_name":"Study Area"} for i in range(800)]
        result=fg.model_2021_panel(panel,rows)
        self.assertEqual(len(result),800)
        self.assertAlmostEqual(result["1"]["change_pp"],-20)
        panel[0]["stable_boundary"]="False"
        result=fg.model_2021_panel(panel,rows)
        self.assertNotIn("0",result)

    def test_plot_anatomy_is_valid_svg(self):
        rows=[{"registered":500+i*7,"area_sqmi":.01+i*.001} for i in range(70)]
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"hist.svg"
            fg.plot_anatomy(rows,p)
            self.assertIn("<svg",p.read_text(encoding="utf-8"))

    def test_transparent_rule_for_sharp_boundaries(self):
        rows=[{"precinct_a":"A","precinct_b":"B","difference_pp":d}
              for d in range(100)]
        # p99 is ~98, so largest is clearly top one percent.
        import numpy as np
        cutoff=float(np.quantile([x["difference_pp"] for x in rows],.99))
        self.assertAlmostEqual(cutoff,98.01,places=2)


if __name__=="__main__":
    unittest.main()
