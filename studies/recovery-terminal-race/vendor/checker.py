"""Independent log specification/recount. Intentionally imports no simulator code.

It reconstructs the scheduler queue, dedup state and observable evidence from the
frozen contract, and audits branch coverage via a prefix tree over saved paths.
"""
import hashlib
import json


def _canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def _fail(condition,message):
    if not condition: raise ValueError(message)
def _event_key(e): return _canonical({k:v for k,v in e.items() if k!='id'})

def validate(row,coverage=False):
    c=row['case'];queue=[];keys={};attempts={};effects=[];now=0;calls=0;writes=0
    public=[];known=set();return_time=None;reason=None;last_observation=None
    last_event=None;requested=('original',['A','B'],c['scope']!='none')
    prefix=hashlib.sha256();branches=[];expect_sub=None
    def add(t,kind,**values): queue.append(dict(t=t,kind=kind,**values))
    def key(item): return 'batch' if c['scope']=='batch' else item
    for entry in row['hidden_trace']:
        k=entry['kind'];now=entry['t']
        if k=='event':
            _fail(expect_sub is None,'missing required semantic event')
            e={k:v for k,v in entry['event'].items() if k!='id'}
            _fail(queue,'executed an unscheduled event')
            earliest=min(q['t'] for q in queue)
            enabled={_event_key(q) for q in queue if q['t']==earliest}
            chosen=_event_key(e)
            _fail(e['t']==earliest and chosen in enabled,'invalid tie ordering or event')
            branches.append((prefix.hexdigest(),enabled,chosen))
            queue.remove(e);last_event=e
            _fail(now==e['t'] and now<=c['horizon'],'event time or horizon mismatch')
            if e['kind']=='effect':expect_sub='effect'
            elif e['kind']=='terminal':expect_sub='terminal'
            elif e['kind']=='read':expect_sub='observation'
            elif e['kind']=='decide':
                if return_time is None: expect_sub='action'
            elif e['kind']=='response':
                a=attempts[e['attempt']]; positives=[]
                for item in e['targets']:
                    owner=e['suppressed'].get(item,e['attempt'])
                    if item in attempts[owner]['effected']:positives.append(item)
                reply=dict(t=now,attempt=e['attempt'],positive=positives,outcome=e['outcome'])
                public.append(dict(t=now,kind='reply',reply=reply));known.update(positives)
                add(now,'decide')
            else:raise ValueError('unknown event class')
        elif k=='admission':
            _fail(requested is not None,'unrequested admission')
            aid,targets,keyed=requested;requested=None
            _fail((entry['attempt'],entry['targets'],entry['keyed'])==(aid,targets,keyed),'admission request changed')
            if keyed and c['scope']=='batch':_fail(targets==['A','B'],'changed keyed batch')
            accepted=[];suppressed={}
            for item in targets:
                cache=keys.get(key(item)) if keyed else None
                if cache and now<cache['expires']:suppressed[item]=cache['owner']
                else:accepted.append(item)
            _fail(entry['admitted']==accepted and entry['suppressed']==suppressed,'incorrect dedup admission')
            if keyed and c['strategy']=='reserve':
                for item in accepted:keys[key(item)]=dict(owner=aid,expires=now+c['ttl'])
            attempts[aid]=dict(items=accepted,effected=[],keyed=keyed,done=None)
            if aid=='original':
                for fate,t in [('early',0),('late',c['late'])]:
                    selected=[i for i,f in zip(['A','B'],c['originals']) if f==fate]
                    if selected:add(t,'effect',attempt=aid,items=selected)
                add(c['original_terminal'],'terminal',attempt=aid);add(1,'decide')
            else:
                mode=c['retry_outcome']
                if accepted and mode!='reject':add(now+(1 if mode=='success' else 3),'effect',attempt=aid,items=accepted)
                add(now+{'success':2,'reject':1,'timeout_commit':4}[mode],'terminal',attempt=aid)
                response=mode if accepted else 'suppressed'
                add(now+{'success':2,'reject':1,'timeout_commit':1,'suppressed':1}[response],
                    'response',attempt=aid,targets=targets,suppressed=suppressed,outcome=response)
            expect_sub=None
        elif k=='effect':
            _fail(expect_sub=='effect','unexpected effect')
            e=last_event;_fail((entry['attempt'],entry['items'])==(e['attempt'],e['items']),'effect payload changed')
            a=attempts[entry['attempt']]
            for item in entry['items']:
                _fail(item in a['items'] and item not in a['effected'],'duplicate per-attempt item event')
                a['effected'].append(item)
                if c['scope']=='item' and c['strategy']=='cache' and a['keyed']:
                    keys[item]=dict(owner=entry['attempt'],expires=now+c['ttl'])
            effects.append(entry);expect_sub=None
        elif k=='terminal':
            _fail(expect_sub=='terminal' and entry['attempt']==last_event['attempt'],'terminal mismatch')
            a=attempts[entry['attempt']];_fail(a['done'] is None,'duplicate terminal')
            a['done']=now
            if c['scope']=='batch' and c['strategy']=='cache' and a['keyed']:
                keys['batch']=dict(owner=entry['attempt'],expires=now+c['ttl'])
            expect_sub=None
        elif k=='observation':
            _fail(expect_sub=='observation','unexpected observation')
            snapshot=max(0,now-c['lag']);positive=[];negative=[]
            if c['observation']!='unavailable':
                for item in ['A','B']:
                    if any(item in e['items'] and e['t']<=snapshot for e in effects):positive.append(item)
                    elif c['observation']=='certified' and all(a['done'] is not None and a['done']<=snapshot for a in attempts.values() if item in a['items']):negative.append(item)
            observation=dict(snapshot=snapshot,positive=positive,terminal_absent=negative,write_count=writes,profile=c['observation'])
            _fail(entry['observation']==observation,'fabricated or stale evidence')
            public.append(dict(t=now,kind='observation',observation=observation));known.update(positive)
            last_observation=observation;add(now,'decide');expect_sub=None
        elif k=='action':
            _fail(expect_sub=='action','unexpected policy action')
            a=entry['action'];kind=a['kind'];expect_sub=None
            if kind=='stop':return_time=now;reason=a['reason']
            elif kind=='wait':
                _fail(a['until']>now,'nonprogressing wait');add(a['until'],'decide')
            else:
                _fail(now<=c['deadline'] and calls<c['budget'],'charged budget exceeded');calls+=1
                if kind=='read':add(now+1,'read')
                elif kind=='write':
                    if row['policy'] in ('horizon_aware','capability_fallback'):
                        if a['keyed']:
                            _fail(c['scope']!='none' and c['strategy']=='reserve' and max(c['original_terminal'],now+4)<c['ttl'],'invalid temporal key basis')
                        else:
                            _fail(last_observation is not None and last_observation['write_count']==writes and set(a['targets'])<=set(last_observation['terminal_absent']) and not(set(a['targets'])&known),'unjustified recovery write')
                    writes+=1;requested=(f'r{writes}',a['targets'],a['keyed'] and c['scope']!='none')
                    expect_sub='admission'
                else:raise ValueError('unknown action')
        else:raise ValueError('unknown trace entry')
        prefix.update(_canonical(entry).encode());prefix.update(b'\n')
    _fail(not queue and requested is None and expect_sub is None and return_time is not None,'incomplete pending trace')
    _fail(public==row['public_trace'],'public/evaluator evidence mismatch')
    counts={i:sum(i in e['items'] for e in effects) for i in ['A','B']}
    running={'A':0,'B':0};post=0
    for e in effects:
        for i in e['items']:
            running[i]+=1
            if running[i]>1 and e['t']>return_time:post+=1
    expected=dict(counts=counts,duplicate_effects=sum(max(0,n-1) for n in counts.values()),duplicate_items=sum(n>1 for n in counts.values()),
        post_return_duplicate_effects=post,actual_complete=all(n>=1 for n in counts.values()),justified_complete=known=={'A','B'},
        unresolved=[i for i in ['A','B'] if i not in known],calls=calls,cost=calls,return_time=return_time,return_reason=reason,
        evaluation_end=now,horizon=c['horizon'],pending_events=0)
    _fail(expected==row['metrics'],'recounted metric mismatch')
    return branches if coverage else expected

def validate_group(rows):
    tree={};n=0
    for row in rows:
        n+=1
        for prefix,expected,chosen in validate(row,coverage=True):
            if prefix not in tree:tree[prefix]=[expected,set()]
            _fail(tree[prefix][0]==expected,'inconsistent prefix queue')
            tree[prefix][1].add(chosen)
    _fail(n>0,'empty scheduler group')
    for expected,seen in tree.values():_fail(expected==seen,'missing allowed event ordering')
    return dict(paths=n,branch_nodes=len(tree),coverage_hash=hashlib.sha256(_canonical(sorted((p,sorted(v[0]),sorted(v[1])) for p,v in tree.items())).encode()).hexdigest())
