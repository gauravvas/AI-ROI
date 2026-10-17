"""Bounded, deterministic action/observation controller.

This is an executable demonstration of a ReAct-style tool interface, not an
LLM-powered ReAct implementation and not a historical platform component.
No external API, model credential, private reasoning trace or company system.
"""
import json
from pathlib import Path
from model import create_fixture, baseline, compare, graph_effort, adjusted_credit

class EvidenceCoordinator:
    def __init__(self, events, graph, changes):
        self.events,self.graph,self.changes=events,graph,changes
        self.state={};self.trace=[]
        self.tools={'inspect_inputs':self.inspect_inputs,'discover_baseline':lambda:baseline(self.events),
          'reconstruct_graph':lambda:graph_effort(self.graph),
          'adjust_quality_credit':lambda:[dict(c,adjusted=adjusted_credit(c['credit'],c['churn'],c['repeat'])) for c in self.changes],
          'calculate_comparison':lambda:compare(self.events,100,500)}

    def inspect_inputs(self):
        origins={e['dataset_origin'] for e in self.events}
        return {'events':len(self.events),'origins':sorted(origins),'sample_only':origins=={'synthetic'}}

    def choose_action(self):
        if 'inspect_inputs' not in self.state:return 'inspect_inputs'
        if not self.state['inspect_inputs']['sample_only']:return 'stop_for_field_data_validation'
        if 'discover_baseline' not in self.state:return 'discover_baseline'
        if self.state['discover_baseline'] is None:return 'stop_insufficient_baseline'
        for name in ['reconstruct_graph','adjust_quality_credit','calculate_comparison']:
            if name not in self.state:return name
        return 'finish'

    def run(self,max_actions=8):
        for _ in range(max_actions):
            action=self.choose_action()
            if action=='finish' or action.startswith('stop_'):
                self.trace.append({'action':action,'observation':{'status':action}})
                return {'status':action,'controller':'deterministic; no LLM invoked','trace':self.trace}
            observation=self.tools[action]()
            self.state[action]=observation
            self.trace.append({'action':action,'observation':observation})
        raise RuntimeError('Action budget exceeded')

if __name__=='__main__':
    result=EvidenceCoordinator(*create_fixture()).run()
    target=Path(__file__).parent/'results'/'agent_run.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print('Controller:',result['status'],'Actions:',len(result['trace']))
