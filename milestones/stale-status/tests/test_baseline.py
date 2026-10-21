import unittest
from workflow import *
class RecoveryTests(unittest.TestCase):
 def test_timeout_after_inspect(self):
  s=Service('after');self.assertEqual(execute(s,'inspect_first'),'committed');self.assertEqual(len(s.records),1)
 def test_blind_duplicates(self):
  s=Service('after');execute(s,'blind_retry');self.assertEqual(len(s.records),2)
 def test_timeout_before(self):
  s=Service('before');self.assertEqual(execute(s,'inspect_first'),'committed');self.assertEqual(len(s.records),1)
 def test_unknown_stops(self):
  s=Service('after',False);self.assertEqual(execute(s,'inspect_first'),'needs_reconciliation');self.assertEqual(len(s.records),1)
 def test_idempotency(self):
  s=Service('after',False,True);self.assertEqual(execute(s,'inspect_first'),'committed');self.assertEqual(len(s.records),1)
 def test_denial_terminal(self):
  s=Service('denied');self.assertEqual(execute(s,'inspect_first'),'denied');self.assertEqual(s.calls,1)
 def test_empty_page_with_cursor(self):
  pages={None:{'items':[],'next_cursor':'next'},'next':{'items':[1,2]}};self.assertEqual(read_all(pages.get),[1,2])
 def test_distinct_operation_ids(self):
  s=Service('after',True,True)
  execute(s,'inspect_first','first');execute(s,'inspect_first','second')
  self.assertEqual(s.records,['first','second']);self.assertEqual(s.calls,4)
 def test_unknown_fault(self):
  with self.assertRaises(ValueError):Service('typo')
 def test_cursor_loop(self):
  with self.assertRaises(ValueError):read_all(lambda c:{'items':[],'next_cursor':'same'})
if __name__=='__main__':unittest.main()
