"""Post-hoc independent finite safe-action closure; no simulator imports.

Alphabet: integer-tick waits, unavailable reads, original-key or keyless writes
of A/B/AB, and stop. One synchronous client; each read/write costs one of three
calls. The fixed worlds share success retry behavior and all public metadata.
"""
import itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
worlds=json.loads((ROOT/'supplementary/indistinguishability-pair.json').read_text())['worlds']
left,right=worlds
public_fields=('scope','strategy','ttl','observation','lag','original_terminal','budget','deadline','horizon')
assert {k:left[k] for k in public_fields}=={k:right[k] for k in public_fields}
assert left['originals']==['early','never'] and right['originals']==['early','late']
assert left['scope']=='item' and left['strategy']=='reserve' and left['ttl']==2
assert left['observation']=='unavailable' and left['late']==3 and left['original_terminal']==4
assert left['retry_outcome']==right['retry_outcome']=='success'
assert left['budget']==3 and left['deadline']==10 and left['horizon']==15
rows=[]
for t,targets,keyed in itertools.product(range(1,11),[('A',),('B',),('A','B')],[False,True]):
    # Independent closed form: the original reservation is half-open [0,2).
    # Reservation expiry does not cancel the late original and is not renewed.
    admitted=[] if keyed and t<2 else list(targets)
    counts_left={'A':1+('A' in admitted),'B':int('B' in admitted)}
    counts_right={'A':1+('A' in admitted),'B':1+('B' in admitted)}
    safe=max(counts_left.values())<=1 and max(counts_right.values())<=1
    if safe:
        # All safe mutations are suppressed at t=1; reply at t=2, before B=late.
        reply_left=[i for i in targets if i=='A'];reply_right=[i for i in targets if i=='A']
    else:reply_left=reply_right=None
    rows.append(dict(t=t,targets=targets,keyed=keyed,admitted=admitted,left_counts=counts_left,
        right_counts=counts_right,safe_in_both=safe,safe_reply_left=reply_left,safe_reply_right=reply_right))
safe=[r for r in rows if r['safe_in_both']]
assert len(rows)==60 and len(safe)==3
assert all(r['t']==1 and r['keyed'] and not r['admitted'] for r in safe)
assert all(r['safe_reply_left']==r['safe_reply_right'] for r in safe)
assert all(r['left_counts']['B']==0 for r in safe)
# Closure: reads/waits/stop never renew keys or change effects. Every safe write
# consumes t=1 -> 2 and is suppressed, so no subsequent safe mutation exists.
# Thus any safe action history has identical public observations in both worlds
# and cannot complete B in the never world. This checks the finite pair only.
result=dict(label='Post-hoc bounded two-world safe-action closure, not part of the frozen 800-case test',
    allowed_action_alphabet=['wait to an integer tick','read unavailable status','write A/B/AB using original keys or keyless','stop'],
    sequential_client=True,call_budget=3,read_cost=1,read_latency=1,write_cost=1,suppressed_reply_latency=1,
    reservation_valid_interval='[0,2)',admission_deadline=10,evaluation_horizon=15,
    examined_first_mutation_choices=len(rows),safe_first_mutation_choices=len(safe),
    all_safe_mutations_suppressed=True,safe_observations_identical=True,
    safe_action_closure_explanation='Only keyed t=1 writes are safe in both worlds. They are suppressed and reply at t=2 with identical positives. They create no new reservation/effect. All later writes duplicate an item in at least one world; unavailable reads and waits cannot distinguish or change the worlds. Therefore a policy safe in both cannot complete B in the never world.',
    no_robust_safe_completion_for_this_pair=True,rows=rows,imports_simulator=False)
(ROOT/'supplementary/safe-action-closure.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
