import copy
import unittest
from model import create_fixture, baseline, graph_effort, adjusted_credit, union_hours, compare

class ModelTests(unittest.TestCase):
    def setUp(self): self.events,self.graph,self.changes=create_fixture()
    def test_observed_baseline(self): self.assertAlmostEqual(baseline(self.events)['hours'],3.9)
    def test_cold_start_blocks_claim(self):
        few=[e for e in self.events if e['condition']=='assisted' or int(e['run_id'].split('-')[1])<=4]
        self.assertIsNone(compare(few,100,500)['hours_saved'])
    def test_duplicate_event_not_double_counted(self):
        self.assertEqual(union_hours(self.events),union_hours(self.events+self.events[:3]))
    def test_conflicting_duplicate_rejected(self):
        e=copy.deepcopy(self.events[0]);e['end']=self.events[1]['end']
        with self.assertRaises(ValueError):union_hours([self.events[0],e])
    def test_overlapping_human_intervals_union(self):
        e=copy.deepcopy(self.events[0]);e['event_id']='overlap'
        self.assertEqual(union_hours([e,self.events[0]]),union_hours([e]))
    def test_two_people_are_two_person_intervals(self):
        e=copy.deepcopy(self.events[0]);e['event_id']='second-person';e['actor_id']='analyst-2'
        self.assertAlmostEqual(union_hours([e,self.events[0]]),2*union_hours([e]))
    def test_machine_time_not_human_time(self):
        self.assertEqual(union_hours(e for e in self.events if e['actor_type']=='ai'),0)
    def test_assisted_incomplete_blocks_claim(self):
        with self.assertRaises(ValueError):compare([e for e in self.events if e['event_id']!='assisted-001-1'],100,500)
    def test_graph_example(self):self.assertAlmostEqual(graph_effort(self.graph)['effort_index_hours'],9.8)
    def test_graph_cycle_and_duplicate_edges(self):
        self.graph['edges']+=self.graph['edges']
        self.assertAlmostEqual(graph_effort(self.graph)['effort_index_hours'],9.8)
    def test_graph_window_excludes_old_resource(self):
        self.graph['nodes'][1]['time']='2020-01-01T00:00:00+00:00'
        self.assertNotIn('ticket',graph_effort(self.graph)['included_resources'])
        self.assertFalse(any(e['to']=='ticket' for e in graph_effort(self.graph)['retained_edges']))
    def test_single_channel_tax_zero(self):
        for n in self.graph['nodes']:n['channel']='same'
        self.assertEqual(graph_effort(self.graph)['effort_index_hours'],7)
    def test_raa_exact_threshold_no_penalty(self):self.assertEqual(adjusted_credit(10,.5,True),10)
    def test_raa_repeat_above_threshold(self):self.assertAlmostEqual(adjusted_credit(10,.8,True),1)
    def test_invalid_churn_rejected(self):
        with self.assertRaises(ValueError):adjusted_credit(10,1.1)
    def test_reconciled_savings(self):
        r=compare(self.events,100,500)
        self.assertAlmostEqual(r['hours_saved'],270)
        self.assertAlmostEqual(r['capacity_value_less_ai_cost'],26500)
    def test_negative_savings_preserved(self):
        from datetime import datetime,timedelta
        events=copy.deepcopy(self.events)
        # A long additional review by a different person is actual labor.
        for i in range(100):
            e=copy.deepcopy(events[0]);e.update(event_id=f'extra-{i}',condition='assisted',run_id=f'assisted-{i+1:03d}',actor_id=f'reviewer-{i}')
            e['end']=(datetime.fromisoformat(e['start'])+timedelta(hours=10)).isoformat();events.append(e)
        self.assertLess(compare(events,100,500)['hours_saved'],0)
    def test_controller_stops_on_missing_baseline(self):
        from agents import EvidenceCoordinator
        result=EvidenceCoordinator([e for e in self.events if e['condition']=='assisted'],self.graph,self.changes).run()
        self.assertEqual(result['status'],'stop_insufficient_baseline')
        self.assertFalse(any(e['action']=='calculate_comparison' for e in result['trace']))
    def test_controller_completes(self):
        from agents import EvidenceCoordinator
        self.assertEqual(EvidenceCoordinator(self.events,self.graph,self.changes).run()['status'],'finish')

if __name__=='__main__':unittest.main(verbosity=2)
