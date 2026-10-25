"""Hand-built synthetic receipts, never crash observations or empirical rows."""
import copy
import hashlib
import unittest
from assess import assess, summarize


def fixture():
    a = '{"item":"A","value":1}'
    digest = hashlib.sha256(a.encode()).hexdigest()
    before = {'effects': [{'id': 1, 'op': 'original', 'payload': a}],
              'keys': [{'key': 'K', 'digest': digest, 'effect_id': 1}],
              'attempts': [{'op': 'original', 'state': 'committed', 'effect_id': 1}],
              'integrity': ['ok'], 'journal_mode': 'delete', 'synchronous': 2}
    final = copy.deepcopy(before)
    final['attempts'].append({'op': 'recovery', 'state': 'deduplicated', 'effect_id': 1})
    def event(actor, event, time, **kw):
        return dict(actor=actor, event=event, mono_ns=time, pid={'original': 2, 'recovery': 3, 'driver': 1}[actor], nonce='n', **kw)
    original_request = {'op': 'original', 'payload': {'item': 'A', 'value': 1}, 'key': 'K'}
    recovery_request = {'op': 'recovery', 'payload': {'item': 'A', 'value': 1}, 'key': 'K'}
    barrier = event('original', 'barrier_reached', 5, phase='after_commit', op='original')
    original = [event('original', 'ready', 1, journal_mode='delete', synchronous=2), event('original', 'request_received', 2, request=original_request), event('original', 'before_commit', 3, op='original'), event('original', 'after_commit', 4, op='original'), barrier]
    reply = {'op': 'recovery', 'state': 'deduplicated', 'status': 200, 'effect_id': 1}
    recovery = [event('recovery', 'ready', 8, journal_mode='delete', synchronous=2), event('recovery', 'request_received', 9, request=recovery_request), event('recovery', 'before_commit', 10, op='recovery'), event('recovery', 'after_commit', 11, op='recovery'), event('recovery', 'response_ready', 12, response=reply), event('recovery', 'worker_finished', 13)]
    driver = [event('driver', 'original_started', 0, child_pid=2), event('driver', 'kill_requested', 6, child_pid=2), event('driver', 'original_exit', 7, child_pid=2, returncode=-9), event('driver', 'recovery_started', 7.5, child_pid=3), event('driver', 'recovery_exit', 14, child_pid=3, returncode=0), event('driver', 'final_read', 15)]
    case = {'id': 'synthetic-only', 'phase': 'after_commit', 'mode': 'same_key', 'expected': {'effects_before_recovery': 1, 'effects_final': 1, 'keys_before_recovery': 1, 'keys_final': 1, 'recovery_state': 'deduplicated', 'recovery_status': 200, 'original_state_after_restart': 'committed', 'original_payload_survives': True, 'recovery_payload': {'item': 'A', 'value': 1}, 'original_payload_count_final': 1}}
    e = dict(nonce='n', original=original, recovery=recovery, driver=driver, barrier=barrier,
             original_request=original_request, recovery_request=recovery_request,
             original_response_exists=False, recovery_response=reply, before_recovery=before,
             before_recovery_sql=copy.deepcopy(before), final_saved=final, final_sql=copy.deepcopy(final))
    return case, e


class AssessmentTests(unittest.TestCase):
    def test_valid_synthetic_fixture_is_a_pass(self):
        c, e = fixture()
        self.assertEqual(assess(c, e)['classification'], 'valid_pass')

    def test_missing_barrier_is_invalid_not_pass(self):
        c, e = fixture()
        e['original'].pop()
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_kill_before_barrier_is_invalid(self):
        c, e = fixture()
        e['driver'][1]['mono_ns'] = 4
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_successful_original_response_defeats_lost_reply_schedule(self):
        c, e = fixture()
        e['original_response_exists'] = True
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_wrong_signal_exit_is_invalid(self):
        c, e = fixture()
        e['driver'][2]['returncode'] = -15
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_reused_service_pid_is_invalid(self):
        c, e = fixture()
        for event in e['recovery']:
            event['pid'] = 2
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_wrong_request_is_invalid(self):
        c, e = fixture()
        e['recovery_request'] = {'op': 'recovery', 'payload': {'item': 'A', 'value': 2}, 'key': 'wrong'}
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_observed_extra_effect_is_valid_prediction_failure(self):
        c, e = fixture()
        extra = {'id': 2, 'op': 'recovery', 'payload': '{"item":"A","value":1}'}
        e['final_saved']['effects'].append(extra)
        e['final_sql']['effects'].append(extra)
        self.assertEqual(assess(c, e)['classification'], 'valid_prediction_fail')

    def test_fabricated_final_snapshot_is_invalid(self):
        c, e = fixture()
        e['final_saved']['effects'] = []
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_fabricated_restart_snapshot_is_invalid(self):
        c, e = fixture()
        e['before_recovery']['keys'] = []
        self.assertEqual(assess(c, e)['classification'], 'invalid')

    def test_missing_rows_stay_in_planned_denominator(self):
        summary = summarize([{'id': 'a'}, {'id': 'b'}, {'id': 'c'}], [{'id': 'a', 'classification': 'valid_pass'}])
        self.assertEqual(summary.get('planned'), 3)
        self.assertEqual(summary.get('valid_pass'), 1)
        self.assertEqual(summary.get('not_run'), 2)

    def test_duplicate_or_unknown_rows_are_refused(self):
        for rows in [[{'id': 'a'}, {'id': 'a'}], [{'id': 'b'}]]:
            with self.assertRaises(ValueError):
                summarize([{'id': 'a'}], rows)


if __name__ == '__main__':
    unittest.main()
