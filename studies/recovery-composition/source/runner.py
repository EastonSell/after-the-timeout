"""Exclusive-output evidence-retaining experiment runner, one process only."""
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import resource
import sys
import time
import traceback
import checker
import model

ROOT=Path(__file__).resolve().parents[1]
def dump(path,obj):
    with open(path,'w') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify_freeze():
    for line in (ROOT/'SOURCE-FREEZE.sha256').read_text().splitlines():
        expected,path=line.split('  ',1)
        if sha(ROOT/path)!=expected:raise ValueError('freeze changed: '+path)
def run(out,cases=None,policies=None,force_prediction_failure=False):
    out=Path(out);out.mkdir();(out/'counterexamples').mkdir()
    started=time.monotonic();cpu0=time.process_time();start_utc=datetime.now(timezone.utc).isoformat()
    protocol=json.loads((ROOT/'protocol.json').read_text());limits=protocol['resource_limits']
    cases=cases if cases is not None else json.loads((ROOT/'cases.json').read_text())
    policies=policies or list(model.POLICIES)
    dump(out/'status.json',dict(state='running',started=start_utc))
    dump(out/'run-input.json',dict(case_count=len(cases),policies=policies,protocol_sha256=sha(ROOT/'protocol.json'),
        protocol_text_sha256=sha(ROOT/'PROTOCOL.md'),source_freeze_sha256=sha(ROOT/'SOURCE-FREEZE.sha256') if (ROOT/'SOURCE-FREEZE.sha256').exists() else None,
        cases_sha256=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()))
    totals=defaultdict(lambda:defaultdict(int));summaries=[];witnesses={};states=0;paths=0;raw_bytes=0;group_count=0
    def witness(name,row):
        if name not in witnesses:
            namepath=out/'counterexamples'/f'{name}.json';dump(namepath,row);witnesses[name]=namepath.name
    try:
        with gzip.open(out/'rows.jsonl.gz','wt',compresslevel=5) as rows_file,open(out/'group-summaries.jsonl','w') as groups_file:
            for case in cases:
                per_case={}
                for policy in policies:
                    rows=model.simulate(case,policy,limits['max_states_per_case_policy'])
                    for n,row in enumerate(rows):
                        row['path_index']=n
                        text=json.dumps(row,sort_keys=True,separators=(',',':'))+'\n'
                        rows_file.write(text);rows_file.flush();raw_bytes+=len(text.encode());paths+=1
                        m=row['metrics']
                        if m['duplicate_effects']:
                            witness('unsafe_'+policy,row)
                            if policy=='blind_keyed' and case['scope']=='item' and case['strategy']=='reserve':witness('expired_item_reservation',row)
                            if case['strategy']=='cache':witness('cache_concurrency',row)
                        if m['post_return_duplicate_effects']:witness('post_return_duplicate',row)
                        if policy=='horizon_aware' and model.omniscient_feasible(case) and not m['actual_complete']:
                            witness('false_P5_completion_upper_bound',row)
                    # Saved and flushed before independent checks or any predictions.
                    coverage=checker.validate_group(rows)
                    states+=rows[0]['states_explored'];group_count+=1
                    metrics=[r['metrics'] for r in rows];N=len(rows)
                    summary=dict(case_id=case['id'],family=case['family'],policy=policy,paths=N,
                        unsafe_paths=sum(m['duplicate_effects']>0 for m in metrics),
                        actual_complete_paths=sum(m['actual_complete'] for m in metrics),
                        justified_complete_paths=sum(m['justified_complete'] for m in metrics),
                        post_return_unsafe_paths=sum(m['post_return_duplicate_effects']>0 for m in metrics),
                        min_calls=min(m['calls'] for m in metrics),max_calls=max(m['calls'] for m in metrics),
                        min_return=min(m['return_time'] for m in metrics),max_return=max(m['return_time'] for m in metrics),
                        states=rows[0]['states_explored'],coverage=coverage,
                        omniscient_feasible=model.omniscient_feasible(case))
                    summaries.append(summary);per_case[policy]=summary
                    groups_file.write(json.dumps(summary,sort_keys=True)+'\n');groups_file.flush()
                    agg=totals[case['family']+'|'+policy]
                    for key,val in dict(cases=1,paths=N,unsafe_cases=int(summary['unsafe_paths']>0),
                        all_safe_cases=int(summary['unsafe_paths']==0),all_actual_complete_cases=int(summary['actual_complete_paths']==N),
                        any_actual_complete_cases=int(summary['actual_complete_paths']>0),all_justified_cases=int(summary['justified_complete_paths']==N),
                        post_return_unsafe_cases=int(summary['post_return_unsafe_paths']>0)).items():agg[key]+=val
                    if states>limits['max_total_states'] or time.monotonic()-started>limits['max_wall_seconds'] or raw_bytes>limits['max_output_bytes']:
                        raise RuntimeError('predeclared resource cap exceeded; incomplete run retained')
                    if group_count%100==0: print(json.dumps(dict(groups=group_count,paths=paths,states=states,elapsed=round(time.monotonic()-started,2))),flush=True)
                if 'capability_fallback' in per_case and 'horizon_aware' in per_case:
                    b=per_case['capability_fallback'];h=per_case['horizon_aware']
                    if h['min_return']>b['max_return'] and b['actual_complete_paths']==b['paths'] and h['actual_complete_paths']==h['paths']:
                        if 'horizon_not_dominant_latency' not in witnesses:
                            dump(out/'counterexamples'/'horizon_not_dominant_latency.json',dict(case=case,baseline=b,horizon=h));witnesses['horizon_not_dominant_latency']='horizon_not_dominant_latency.json'
        predictions=[dict(id='P1',passed=all(s['unsafe_paths']==0 for s in summaries if s['policy']=='horizon_aware'),required=True),
            dict(id='P2',passed=all(s['unsafe_paths']==0 for s in summaries if s['policy']=='capability_fallback'),required=True),
            dict(id='P3',passed='unsafe_naive_inspection' in witnesses,required='naive_inspection' in policies),
            dict(id='P4',passed='expired_item_reservation' in witnesses,required='blind_keyed' in policies),
            dict(id='P5',passed='false_P5_completion_upper_bound' not in witnesses,required=False),
            dict(id='P6',passed='horizon_not_dominant_latency' in witnesses,required=False)]
        if force_prediction_failure:predictions.append(dict(id='forced_retention_test',passed=False,required=True))
        dump(out/'predictions.json',predictions)
        dump(out/'summary.json',dict(totals=dict(totals),groups=group_count,paths=paths,states=states,
            witnesses=witnesses,scheduler_weighting='Raw path counts are not probabilities; compare universal/existential case outcomes.',
            scope='Finite synthetic model only; no model adherence or production-rate evidence.'))
        success=all(p['passed'] for p in predictions if p['required'])
        dump(out/'status.json',dict(state='complete' if success else 'prediction_failed',success=success,started=start_utc,finished=datetime.now(timezone.utc).isoformat()))
        return dict(success=success,groups=group_count,paths=paths,states=states)
    except BaseException as error:
        dump(out/'status.json',dict(state='failed',error=repr(error),traceback=traceback.format_exc(),groups=group_count,paths=paths))
        raise
    finally:
        usage=resource.getrusage(resource.RUSAGE_SELF)
        dump(out/'resource-ledger.json',dict(started=start_utc,finished=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-started,
            cpu_seconds=time.process_time()-cpu0,max_rss_kib=usage.ru_maxrss,python=sys.version,platform=platform.platform(),processes=1,
            network_requests=0,api_calls=0,model_calls=0,device_actions=0,installs=0,external_writes=0,
            states=states,terminal_paths=paths,groups=group_count,uncompressed_row_bytes=raw_bytes,
            compressed_row_bytes=(out/'rows.jsonl.gz').stat().st_size if (out/'rows.jsonl.gz').exists() else 0,
            frozen_caps=limits))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);a=parser.parse_args()
    verify_freeze();result=run(a.out);print(json.dumps(result,sort_keys=True));return 0 if result['success'] else 1
if __name__=='__main__':raise SystemExit(main())
