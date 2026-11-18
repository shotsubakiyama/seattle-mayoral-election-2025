"""No-network checks for the precinct guide's additional diagrams."""
import io
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import precinct_field_guide_extensions as ext


class ExtensionsTest(unittest.TestCase):
    def test_archived_snapshot_count_query(self):
        class Response:
            def __init__(self):self.content=b'{"count":888}'
            def __enter__(self):return self
            def __exit__(self,*x):return False
            def read(self):return self.content
        with patch.object(ext.urllib.request,"urlopen",return_value=Response()) as get:
            rows=ext.historical_counts((2015,))
        self.assertEqual(rows[0]["seattle_precincts"],888)
        self.assertIn("2015",rows[0]["url"])
        self.assertIn("returnCountOnly",get.call_args.args[0].full_url)

    def test_area_location_nearest_is_flagged_approximate(self):
        polygons={"1":box(0,0,100,100),"2":box(100,0,200,100),"3":box(4000,0,4100,100)}
        summary={"precinct_population_2025":{
            "top_geographic_area":[{"precinct_id":"2"},{"precinct_id":"1"}]}}
        ext.enrich_area_location(summary,polygons,{"1":"Queen Anne","3":"Ballard"})
        rows=summary["precinct_population_2025"]["top_geographic_area"]
        self.assertEqual(rows[0]["near_area"],"Queen Anne")
        self.assertIn("approximate",rows[0]["area_label_quality"])
        self.assertEqual(rows[1]["area_label_quality"],"assigned community area")

    def test_vote_weighted_map_is_png(self):
        polygons={"1":box(0,0,100,100),"2":box(100,0,200,100)}
        rows=[{"precinct_id":"1","harrell_pct":25,"finalist_votes":300},
              {"precinct_id":"2","harrell_pct":75,"finalist_votes":600}]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"vote.png"
            ext.plot_voter_bubble_comparison(polygons,rows,path)
            self.assertGreater(path.stat().st_size,1000)

    def test_historical_change_figure(self):
        example={str(i):{"change_pp":float(-i%21-10)} for i in range(20)}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"change.svg"
            result=ext.plot_change_distribution(example,path)
            self.assertEqual(result["total"],20)
            self.assertTrue(path.exists())


if __name__=="__main__":
    unittest.main()
