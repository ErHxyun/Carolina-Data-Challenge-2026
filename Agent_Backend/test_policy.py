import unittest
from unittest.mock import Mock, patch
import server
from policy import target_scenario, validate_planning
from workflow import create_report_graph, run_report_graph
class PolicyTests(unittest.TestCase):
 def test_future(self):
  r=server.route_query("Armenia halve unpaid work gap by 2035")
  self.assertIsNone(r["year"])
  self.assertEqual(r["target_year"],2035)
  x=target_scenario(r,server.statistical_data(r),2026)
  self.assertEqual(x["baseline_year"],2008)
  self.assertAlmostEqual(x["target"],4.149/2)
  self.assertAlmostEqual(x["annual_change"],-4.149/2/27)
 def test_two_dates(self):
  r=server.route_query("Armenia policy from 2004 halve unpaid work gap by 2035")
  self.assertEqual(r["year"],2004)
  self.assertEqual(r["target_year"],2035)
 def test_past(self):
  r=server.route_query("Armenia halve unpaid work gap by 2025")
  x=target_scenario(r,server.statistical_data(r),2026)
  self.assertEqual(x["status"],"retrospective")
  self.assertIsNone(x["annual_change"])
 def test_missing_goal(self):
  r=server.route_query("Armenia policy address unpaid work gap by 2035")
  x=target_scenario(r,server.statistical_data(r),2026)
  self.assertIsNone(x["target"])
 def test_missing_data(self):
  x=target_scenario({"topic":"time_tax","target_year":2035,"reduction_pct":50},{"facts":[]},2026)
  self.assertIsNone(x["baseline"])
 def test_invalid_goal(self):
  for value in (-1,101,float("nan"),True):
   with self.assertRaises(ValueError): validate_planning({"reduction_pct":value})
 def test_isolation(self):
  brief=Mock(return_value={"status":"complete"});roadmap=Mock(return_value={"status":"partial"})
  g=create_report_graph(lambda r:r,lambda r:{},lambda b:{"status":"complete"},lambda r,b:{"status":"unavailable"},brief,roadmap)
  events=[]
  run_report_graph(g,{"output_mode":"policy_roadmap"},lambda *v:events.append(v))
  brief.assert_not_called();roadmap.assert_called_once()
  self.assertIn(("roadmap","limited"),events)
  run_report_graph(g,{"output_mode":"research_brief"},lambda *v:None)
  brief.assert_called_once();roadmap.assert_called_once()
 def test_offline(self):
  r=server.route_query("Armenia halve unpaid work gap by 2035");b=server.statistical_data(r)
  with patch.object(server,"completion",side_effect=RuntimeError("offline")):
   x=server.roadmap_agent(r,b,{"status":"data_only","summary":"Records","data":b},{"status":"unavailable","summary":"No sources","sources":[]})
  self.assertEqual(x["status"],"partial")
  self.assertIsNotNone(x["scenario"]["target"])
