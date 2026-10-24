"""Post-hoc candidate: change read timing only, never simulator contracts."""
from vendor import model
ORIGINAL = model.policy_action

def policy_action(policy, view):
    if policy != 'terminal_barrier':
        return ORIGINAL(policy, view)
    action = ORIGINAL('horizon_aware', view)
    c = view['contract']
    if c['observation'] != 'certified' or action['kind'] not in ('read', 'wait'):
        return action
    bound = max(c['original_terminal'], view['last_write_bound'])
    # At zero lag, delivery at bound can precede same-tick terminal events.
    # Positive lag already delivers a snapshot of bound strictly after bound.
    start = max(view['now'], bound + max(c['lag'], 1) - 1)
    if start > c['deadline']:
        return dict(kind='stop', reason='barrier snapshot exceeds action deadline')
    if start > view['now']:
        return dict(kind='wait', until=start)
    return dict(kind='read')

model.policy_action = policy_action
