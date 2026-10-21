"""Offline fault model. No network, credentials, or external side effects."""
from dataclasses import dataclass,field

class Denied(Exception): pass
class UnknownOutcome(Exception): pass

@dataclass
class Service:
 fault: str='none'
 status_supported: bool=True
 idempotent: bool=False
 calls: int=0
 records: list=field(default_factory=list)
 seen: set=field(default_factory=set)
 def __post_init__(self):
  if self.fault not in ('none','before','after','denied'):raise ValueError('Unknown fault')
 def write(self,operation_id):
  self.calls+=1
  if self.fault=='denied': raise Denied('operation refused')
  first=operation_id not in self.seen
  self.seen.add(operation_id)
  if first and self.fault=='before': raise UnknownOutcome('transport failed before commit')
  if not self.idempotent or operation_id not in self.records:self.records.append(operation_id)
  if first and self.fault=='after':raise UnknownOutcome('transport failed after commit')
  return 'committed'
 def status(self,operation_id):
  self.calls+=1
  if not self.status_supported:return 'unknown'
  return 'committed' if operation_id in self.records else 'not_committed'

def execute(service,policy,operation_id='example-001'):
 if policy not in ('blind_retry','inspect_first'):raise ValueError('Unknown policy')
 try:return service.write(operation_id)
 except Denied:return 'denied'
 except UnknownOutcome:
  if policy=='inspect_first':
   state=service.status(operation_id)
   if state=='committed':return state
   if state=='unknown' and not service.idempotent:return 'needs_reconciliation'
  try:return service.write(operation_id)
  except Denied:return 'denied'
  except UnknownOutcome:return 'needs_reconciliation'

def read_all(fetch,max_pages=100):
 """Consume empty pages that carry continuation, reject cursor loops."""
 cursor=None;seen=set();rows=[]
 for _ in range(max_pages):
  page=fetch(cursor);rows.extend(page['items']);cursor=page.get('next_cursor')
  if cursor is None:return rows
  if cursor in seen:raise ValueError('Cursor loop')
  seen.add(cursor)
 raise ValueError('Page budget exhausted')
