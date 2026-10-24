"""Pure finite event simulator. No I/O except explicit input grid loading."""
import copy
import itertools
import json
from pathlib import Path

ITEMS=('A','B')
POLICIES=('naive_inspection','blind_keyed','capability_fallback','horizon_aware')
PROTOCOL=Path(__file__).resolve().parents[1]/'protocol.json'

def generate_cases():
    p=json.loads(PROTOCOL.read_text()); out=[]
    g=p['exhaustive']
    for originals,key,obs,outcome in itertools.product(itertools.product(g['original_each'],repeat=2),g['key_contracts'],g['observation_profiles'],g['retry_outcomes']):
        out.append(dict(family='exhaustive',originals=list(originals),late=g['late_effect'],original_terminal=g['original_terminal'],scope=key[0],strategy=key[1],ttl=key[2],observation=obs[0],lag=obs[1],retry_outcome=outcome,budget=g['call_budget'],deadline=g['action_deadline'],horizon=g['evaluation_horizon']))
    for f in p['held_out_families']:
        for late,terminal in zip(f['late_effects'],f['original_terminals']):
            for ttl,scope,strategy,originals,obs,outcome in itertools.product(f['ttls'],f['scopes'],f['strategies'],f['originals'],f['observations'],f['outcomes']):
                if scope=='none' and ttl!=f['ttls'][0]: continue
                out.append(dict(family=f['name'],originals=originals,late=late,original_terminal=terminal,scope=scope,strategy=strategy,ttl=ttl if scope!='none' else 0,observation=obs[0],lag=obs[1],retry_outcome=outcome,budget=f['budget'],deadline=f['deadline'],horizon=f['horizon']))
    for n,c in enumerate(out): c['id']=f"{c['family']}-{n:04d}"
    return out

def initial_view(case):
    allowed=('scope','strategy','ttl','observation','lag','original_terminal','budget','deadline','horizon')
    return dict(contract={k:case[k] for k in allowed},now=1,known=[],calls=0,actions=[],observations=[],replies=[],writes=0,last_write_bound=0)

def policy_action(policy,v):
    """Only a public view enters this function. Hidden fates cannot be queried."""
    c=v['contract']; now=v['now']; missing=[i for i in ITEMS if i not in v['known']]
    if not missing: return dict(kind='stop',reason='positive evidence for all items')
    if v['calls']>=c['budget'] or now>c['deadline']: return dict(kind='stop',reason='resource limit')
    if policy=='naive_inspection':
        if not v['observations']: return dict(kind='read')
        if not v['writes']: return dict(kind='write',targets=missing,keyed=False,reason='naive missing-as-absent')
        return dict(kind='stop',reason='one inspected replay finished')
    if policy=='blind_keyed':
        return dict(kind='write',targets=list(ITEMS),keyed=c['scope']!='none',reason='blind identical replay')
    if policy not in ('capability_fallback','horizon_aware'): raise ValueError(policy)
    # Both temporal and structural adequacy, never merely key presence.
    safe_key=(c['scope']!='none' and c['strategy']=='reserve' and
              max(c['original_terminal'],now+4,v['last_write_bound'])<c['ttl'])
    if policy=='capability_fallback' and not v['actions'] and safe_key:
        return dict(kind='write',targets=list(ITEMS),keyed=True,reason='full-horizon atomic reservation')
    if c['observation']=='unavailable': return dict(kind='stop',reason='no evidence interface')
    latest=v['observations'][-1] if v['observations'] else None
    if latest and latest['write_count']==v['writes']:
        targets=[i for i in latest['terminal_absent'] if i in missing]
        if targets: return dict(kind='write',targets=targets,keyed=False,reason='certified terminal absence')
        if c['observation']=='opaque': return dict(kind='stop',reason='negative is not terminal evidence')
    bound=max(c['original_terminal'],v['last_write_bound'])
    read_start=max(now,bound+c['lag']-1)
    if read_start>c['deadline']: return dict(kind='stop',reason='terminal snapshot exceeds action deadline')
    if read_start>now: return dict(kind='wait',until=read_start)
    return dict(kind='read')

def omniscient_feasible(c):
    """Information-only upper bound with constructive keyless schedule at t=1."""
    return ('never' not in c['originals'] or
            (c['retry_outcome']!='reject' and c['budget']>=1 and c['deadline']>=1))

def _event(s,t,kind,**data):
    s['serial']+=1; s['events'].append(dict(id=s['serial'],t=t,kind=kind,**data))

def _key(c,item): return 'batch' if c['scope']=='batch' else item

def _log(s,kind,**data):
    s['hidden'].append(dict(t=s['now'],kind=kind,**data))

def _admit(s,aid,targets,keyed,original=False):
    c=s['case']; t=s['now']; admitted=[]; suppressed={}
    if keyed and c['scope']=='batch' and targets!=list(ITEMS): raise ValueError('changed batch payload')
    for item in targets:
        k=_key(c,item)
        record=s['keys'].get(k) if keyed else None
        if record is not None and t<record['expires']:
            suppressed[item]=record['owner']
        else: admitted.append(item)
    # A batch reservation is installed once, after checking the whole request.
    if keyed and c['strategy']=='reserve':
        for item in admitted: s['keys'][_key(c,item)]=dict(owner=aid,expires=t+c['ttl'])
    if original:
        eff=[i for i,f in zip(ITEMS,c['originals']) if f!='never']
        terminal=c['original_terminal']
    else:
        eff=admitted if c['retry_outcome']!='reject' else []
        terminal=t+({'success':2,'reject':1,'timeout_commit':4}[c['retry_outcome']])
    s['attempts'][aid]=dict(targets=admitted,begin=t,terminal=terminal,done=False,effected=[],keyed=keyed)
    _log(s,'admission',attempt=aid,targets=targets,keyed=keyed,admitted=admitted,suppressed=suppressed)
    if original:
        for fate,time in [('early',0),('late',c['late'])]:
            selected=[i for i,f in zip(ITEMS,c['originals']) if f==fate]
            if selected: _event(s,time,'effect',attempt=aid,items=selected)
    elif eff:
        delay=1 if c['retry_outcome']=='success' else 3
        _event(s,t+delay,'effect',attempt=aid,items=eff)
    _event(s,terminal,'terminal',attempt=aid)
    if not original:
        outcome=c['retry_outcome'] if admitted else 'suppressed'
        delay={'success':2,'reject':1,'timeout_commit':1,'suppressed':1}[outcome]
        _event(s,t+delay,'response',attempt=aid,targets=targets,suppressed=suppressed,outcome=outcome)

def _observe(s):
    c=s['case']; snapshot=max(0,s['now']-c['lag']); pos=[]; neg=[]
    if c['observation']!='unavailable':
        for i in ITEMS:
            if any(e['kind']=='effect' and e['t']<=snapshot and i in e['items'] for e in s['hidden']): pos.append(i)
            elif c['observation']=='certified':
                relevant=[a for a in s['attempts'].values() if i in a['targets']]
                if all(a['done'] and a['done_time']<=snapshot for a in relevant): neg.append(i)
    return dict(snapshot=snapshot,positive=pos,terminal_absent=neg,write_count=s['view']['writes'],profile=c['observation'])

def _step(s,e):
    s['now']=e['t']; v=s['view']; v['now']=s['now']; c=s['case']
    _log(s,'event',event=e)
    kind=e['kind']
    if kind=='effect':
        a=s['attempts'][e['attempt']]
        for i in e['items']:
            s['counts'][i]+=1; a['effected'].append(i)
            if c['strategy']=='cache' and c['scope']=='item' and a['keyed']:
                s['keys'][i]=dict(owner=e['attempt'],expires=s['now']+c['ttl'])
        _log(s,'effect',attempt=e['attempt'],items=e['items'])
    elif kind=='terminal':
        a=s['attempts'][e['attempt']]; a['done']=True; a['done_time']=s['now']
        if c['strategy']=='cache' and c['scope']=='batch' and a['keyed']:
            s['keys']['batch']=dict(owner=e['attempt'],expires=s['now']+c['ttl'])
        _log(s,'terminal',attempt=e['attempt'])
    elif kind=='response':
        a=s['attempts'][e['attempt']]; positives=[]
        for i in e['targets']:
            owner=e['suppressed'].get(i,e['attempt'])
            if i in s['attempts'][owner]['effected']: positives.append(i)
        reply=dict(t=s['now'],attempt=e['attempt'],positive=positives,outcome=e['outcome'])
        v['known']=sorted(set(v['known'])|set(positives));v['replies'].append(reply)
        s['public'].append(dict(t=s['now'],kind='reply',reply=reply))
        _event(s,s['now'],'decide')
    elif kind=='read':
        obs=_observe(s);v['observations'].append(obs);v['known']=sorted(set(v['known'])|set(obs['positive']))
        s['public'].append(dict(t=s['now'],kind='observation',observation=obs))
        _log(s,'observation',observation=obs)
        _event(s,s['now'],'decide')
    elif kind=='decide':
        if s['returned'] is not None: return
        action=policy_action(s['policy'],copy.deepcopy(v));k=action['kind']
        _log(s,'action',action=action)
        if k=='stop':
            s['returned']=s['now'];s['reason']=action['reason'];return
        if k=='wait':
            if action['until']<=s['now']:raise ValueError('nonprogressing wait')
            _event(s,action['until'],'decide');return
        if s['now']>c['deadline'] or v['calls']>=c['budget']:raise ValueError('budget admission')
        v['calls']+=1;v['actions'].append(dict(t=s['now'],**action))
        if k=='read': _event(s,s['now']+1,'read')
        elif k=='write':
            v['writes']+=1;v['last_write_bound']=s['now']+4
            _admit(s,f"r{v['writes']}",action['targets'],action['keyed'] and c['scope']!='none')
        else:raise ValueError(k)
    else:raise ValueError(kind)

def _finish(s,states):
    counts=s['counts'];ret=s['returned'];duplicates=sum(max(0,n-1) for n in counts.values())
    running={i:0 for i in ITEMS};post=0
    for e in s['hidden']:
        if e['kind']=='effect':
            for i in e['items']:
                running[i]+=1
                if running[i]>1 and e['t']>ret:post+=1
    metrics=dict(counts=counts,duplicate_effects=duplicates,duplicate_items=sum(n>1 for n in counts.values()),
        post_return_duplicate_effects=post,actual_complete=all(counts[i]>=1 for i in ITEMS),
        justified_complete=set(s['view']['known'])==set(ITEMS),unresolved=[i for i in ITEMS if i not in s['view']['known']],
        calls=s['view']['calls'],cost=s['view']['calls'],return_time=ret,return_reason=s['reason'],
        evaluation_end=s['now'],horizon=s['case']['horizon'],pending_events=len(s['events']))
    return dict(case=s['case'],policy=s['policy'],public_trace=s['public'],hidden_trace=s['hidden'],metrics=metrics,
                scheduler_paths=1,states_explored=states)

def simulate(case,policy,max_states=100000):
    s=dict(case=copy.deepcopy(case),policy=policy,now=0,serial=0,events=[],hidden=[],public=[],keys={},attempts={},counts={i:0 for i in ITEMS},view=initial_view(case),returned=None,reason=None)
    _admit(s,'original',list(ITEMS),case['scope']!='none',True);_event(s,1,'decide')
    todo=[s];rows=[];states=0
    while todo:
        current=todo.pop();states+=1
        if states>max_states:raise RuntimeError('state cap exceeded; enumeration incomplete')
        if not current['events']:
            if current['returned'] is None:raise RuntimeError('policy did not return')
            rows.append(_finish(current,states));continue
        first=min(e['t'] for e in current['events'])
        if first>case['horizon']:raise RuntimeError('pending event beyond frozen horizon')
        choices=[e['id'] for e in current['events'] if e['t']==first]
        for choice in choices:
            branch=copy.deepcopy(current)
            e=next(e for e in branch['events'] if e['id']==choice);branch['events'].remove(e)
            _step(branch,e);todo.append(branch)
    for row in rows:row['states_explored']=states
    return rows
