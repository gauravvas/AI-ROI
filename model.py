"""Executable reference demonstration of OBD, GWER and RAA.

Synthetic data only. Newly implemented from the supplied paper, not the
author's original experiment code or evidence of any company's deployment.
Python 3.10+, standard library only. Run: python3 model.py
"""
from __future__ import annotations
import hashlib
import json
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ['Collect records', 'Match entries', 'Investigate differences',
         'Resolve exceptions', 'Validate result', 'Approve and close']
MANUAL = [24, 48, 36, 54, 42, 30]
ASSISTED = [6, 12, 10, 18, 14, 12]
CHANNELS = ['ERP', 'ERP', 'Ticketing', 'Collaboration', 'Documents', 'ERP']

def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()

def union_hours(events):
    """Sum person-hours; union overlapping intervals per actor, never across actors.

    Input intervals represent observed active work, not browser-open spans.
    This distinction must be established by real instrumentation in field use.
    """
    intervals = defaultdict(list)
    seen = {}
    for event in events:
        if event['event_id'] in seen:
            if seen[event['event_id']] != event:
                raise ValueError('Conflicting duplicate event ID')
            continue
        seen[event['event_id']] = event
        if event['actor_type'] != 'human':
            continue
        start, end = timestamp(event['start']), timestamp(event['end'])
        if end <= start:
            raise ValueError('Invalid active-work interval')
        intervals[event['actor_id']].append((start, end))
    seconds = 0
    for spans in intervals.values():
        merged = []
        for start, end in sorted(spans):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(end, merged[-1][1])
            else:
                merged.append([start, end])
        seconds += sum(end-start for start, end in merged)
    return seconds/3600

def baseline(events, min_runs=5):
    groups = defaultdict(list)
    for event in events:
        if event['condition'] == 'manual' and event['actor_type'] == 'human':
            groups[event['run_id']].append(event)
    # Complete runs only. A real deployment must also verify workflow version,
    # complexity strata and source coverage before forming this cohort.
    complete = {r: es for r, es in groups.items()
                if {e['step'] for e in es} == set(STEPS)}
    if len(complete) < min_runs:
        return None
    step_hours = {step: statistics.median(
        union_hours(e for e in es if e['step'] == step)
        for es in complete.values()) for step in STEPS}
    return {'hours': sum(step_hours.values()), 'step_hours': step_hours,
            'complete_runs': len(complete), 'excluded_runs': len(groups)-len(complete),
            'source_event_ids': sorted(e['event_id'] for es in complete.values() for e in es)}

def graph_effort(graph, tau=0.08, max_hops=2, window_days=14):
    """Paper equation 3: a resource-effort index, not observed human labor.

    Contains agent-session time if the graph contains it. Keep this index
    separate from the observed person-hours used in the financial comparison.
    """
    if tau < 0 or max_hops < 0 or window_days < 0:
        raise ValueError('Invalid graph parameters')
    root, anchor = graph['root'], timestamp(graph['anchor'])
    nodes = {n['id']: n for n in graph['nodes']}
    if len(nodes) != len(graph['nodes']):
        raise ValueError('Duplicate graph resource')
    edges = defaultdict(list)
    for edge in graph['edges']:
        if edge['from'] not in nodes or edge['to'] not in nodes:
            raise ValueError('Unresolved graph edge')
        edges[edge['from']].append(edge['to'])
        edges[edge['to']].append(edge['from'])
    todo, visited, selected = deque([(root, 0)]), set(), []
    while todo:
        node_id, depth = todo.popleft()
        if node_id in visited: continue
        visited.add(node_id)
        node = nodes[node_id]
        if abs(timestamp(node['time'])-anchor) > window_days*86400: continue
        if node['hours'] < 0: raise ValueError('Negative resource duration')
        if node_id != root: selected.append(node)
        if depth < max_hops:
            todo.extend((n, depth+1) for n in edges[node_id])
    channels = {n['channel'] for n in selected}
    raw = sum(n['hours'] for n in selected)
    multiplier = 1+tau*max(0, len(channels)-1)
    retained_ids = {root} | {n['id'] for n in selected}
    return {'resource_hours': raw, 'channels': len(channels), 'tau': tau,
            'multiplier': multiplier, 'effort_index_hours': raw*multiplier,
            'included_resources': [n['id'] for n in selected],
            'retained_edges': [e for e in graph['edges']
                               if e['from'] in retained_ids and e['to'] in retained_ids]}

def adjusted_credit(credit, churn, repeat=False, theta=0.5, rho=0.5):
    """Paper equation 4, for nonnegative attribution credit, not cash savings."""
    if credit < 0 or not 0 <= churn <= 1 or not 0 <= theta <= 1 or not 0 <= rho <= 1:
        raise ValueError('Invalid attribution input')
    return credit if churn <= theta else credit*(1-churn)*(rho if repeat else 1)

def compare(events, hourly_rate, ai_cost):
    if hourly_rate < 0 or ai_cost < 0: raise ValueError('Negative cost')
    b = baseline(events)
    if b is None: return {'status': 'insufficient_manual_baseline', 'hours_saved': None}
    groups = defaultdict(list)
    for e in events:
        if e['condition'] == 'assisted': groups[e['run_id']].append(e)
    if not groups: return {'status': 'no_assisted_runs', 'hours_saved': None}
    for es in groups.values():
        if {e['step'] for e in es if e['actor_type']=='human'} != set(STEPS):
            raise ValueError('Incomplete assisted workflow; no savings claim')
    human_after = sum(union_hours(es) for es in groups.values())
    manual_equivalent = b['hours']*len(groups)
    saved = manual_equivalent-human_after  # Negative savings remain visible.
    # Cohorts in the supplied fixture have matching task complexity and quality.
    return {'status': 'synthetic_demonstration', 'manual_runs': b['complete_runs'],
            'assisted_runs': len(groups), 'baseline_hours_per_run': b['hours'],
            'observed_manual_cohort_hours': union_hours(e for e in events if e['condition']=='manual'),
            'manual_equivalent_hours_for_assisted_volume': manual_equivalent,
            'observed_assisted_human_hours': human_after,
            'hours_saved': saved, 'reduction_percent': 100*saved/manual_equivalent,
            'loaded_hourly_rate_assumption': hourly_rate,
            'gross_labor_capacity_value': saved*hourly_rate,
            'incremental_ai_cost_assumption': ai_cost,
            'capacity_value_less_ai_cost': saved*hourly_rate-ai_cost,
            'cash_savings_verified': False,
            'causal_effect_established': False,
            'comparison_boundary': 'Equal synthetic volume and complexity; all review, exception handling and rework included in human intervals',
            'baseline': b}

def create_fixture():
    events = []
    for condition, minutes in [('manual', MANUAL), ('assisted', ASSISTED)]:
        for run in range(100):
            factor = [0.8, 0.9, 1, 1.1, 1.2][run % 5]
            day = datetime(2026, 1 if condition=='manual' else 6, 1, 9, tzinfo=timezone.utc)+timedelta(days=run)
            current = day
            for step, duration, channel in zip(STEPS, minutes, CHANNELS):
                finish = current+timedelta(minutes=duration*factor)
                events.append({'event_id': f'{condition}-{run+1:03d}-{STEPS.index(step)+1}',
                    'dataset_origin': 'synthetic', 'workflow_id': 'AP-reconciliation',
                    'workflow_version': '1', 'complexity': 'standard',
                    'run_id': f'{condition}-{run+1:03d}', 'condition': condition,
                    'step': step, 'actor_id': 'analyst-1', 'actor_type': 'human',
                    'channel': channel, 'resource_id': f'case-{condition}-{run+1:03d}',
                    'start': current.isoformat(), 'end': finish.isoformat(),
                    'accepted': True})
                current = finish+timedelta(minutes=15)  # Idle gap not billable effort.
            if condition=='assisted':
                events.append({'event_id': f'agent-{run+1:03d}', 'dataset_origin':'synthetic',
                    'workflow_id':'AP-reconciliation','workflow_version':'1','complexity':'standard',
                    'run_id':f'assisted-{run+1:03d}','condition':'assisted','step':'Agent execution',
                    'actor_id':'agent-1','actor_type':'ai','channel':'Agent runtime',
                    'resource_id':f'case-assisted-{run+1:03d}',
                    'start':day.isoformat(),'end':(day+timedelta(minutes=18)).isoformat(),'accepted':True})
    anchor = '2026-06-15T12:00:00+00:00'
    resources = [('ticket',1,'Ticketing'),('agent',.5,'Agent runtime'),('code',1.5,'Code hosting'),
                 ('call',1,'Collaboration'),('chat',.5,'Collaboration'),
                 ('document',1,'Documents'),('research',1.5,'Research')]
    graph={'root':'PR-1','anchor':anchor,
           'nodes':[{'id':'PR-1','hours':0,'channel':'root','time':anchor}]+[
               {'id':n,'hours':h,'channel':c,'time':anchor} for n,h,c in resources],
           'edges':[{'from':'PR-1','to':n,'evidence_id':'synthetic-link-'+n} for n,_,_ in resources]}
    changes = [{'change_id':'PR-A','credit':10,'churn':.15,'repeat':False},
               {'change_id':'PR-B','credit':10,'churn':.8,'repeat':False},
               {'change_id':'PR-C','credit':10,'churn':.8,'repeat':True}]
    return events, graph, changes

def run():
    data, outputs = HERE/'sample_data', HERE/'results'
    data.mkdir(exist_ok=True); outputs.mkdir(exist_ok=True)
    events, graph, changes = create_fixture()
    for name, content in [('events.json',events),('resource_graph.json',graph),('changes.json',changes)]:
        (data/name).write_text(json.dumps(content,indent=2)+'\n')
    result = compare(events,100,500)
    result['GWER_example']=graph_effort(graph)
    result['RAA_examples']=[dict(c,adjusted_credit=adjusted_credit(c['credit'],c['churn'],c['repeat'])) for c in changes]
    agent_hours=sum((timestamp(e['end'])-timestamp(e['start']))/3600 for e in events if e['actor_type']=='ai')
    result['naive_agent_time_hours']=agent_hours
    result['naive_claimed_hours_saved']=result['manual_equivalent_hours_for_assisted_volume']-agent_hours
    result['naive_overstatement_hours']=result['naive_claimed_hours_saved']-result['hours_saved']
    result['lineage']={'data_origin':'synthetic','implementation':'new reference implementation, not original study reproduction',
        'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(data.glob('*.json'))},
        'model_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (outputs/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    trace=[]
    for name, tool, observation in [
        ('Intake','validate_sources',{'event_count':len(events),'origin':'synthetic'}),
        ('Baseline','baseline',{'manual_runs':100,'baseline_hours':result['baseline_hours_per_run']}),
        ('Effort','compare',{'human_hours':result['observed_assisted_human_hours'],'hours_saved':result['hours_saved']}),
        ('Graph','graph_effort',result['GWER_example']),
        ('Quality','adjusted_credit',{'results':result['RAA_examples']}),
        ('Evidence','write_metrics',{'source_hashes':result['lineage']['input_sha256']})]:
        trace.append({'step':len(trace)+1,'worker':name,'controller':'deterministic tool workflow; no LLM invoked',
                      'action':tool,'observation':observation})
    (outputs/'tool_trace.json').write_text(json.dumps(trace,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['baseline','lineage']},indent=2))
    return result

if __name__ == '__main__': run()
