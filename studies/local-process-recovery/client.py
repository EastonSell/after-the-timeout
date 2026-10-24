"""Real HTTP requests from client processes, recording observed replies/timeouts."""
import argparse
import http.client
import json
import socket
import time
from pathlib import Path
from common import Trace, write_json


def rpc(port, trace, method, path, data=None, timeout=3):
    trace.emit('request_start', method=method, path=path, data=data, timeout_s=timeout)
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        body = None if data is None else json.dumps(data)
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        value = json.loads(response.read())
        result = dict(status='response', http_status=response.status, body=value)
        trace.emit('response_received', method=method, path=path, **result)
        return result
    except (TimeoutError, socket.timeout) as exc:
        result = dict(status='timeout', exception=type(exc).__name__)
        trace.emit('request_timeout', method=method, path=path, **result)
        return result
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int)
    parser.add_argument('root', type=Path)
    parser.add_argument('actor')
    parser.add_argument('timeout', type=float)
    parser.add_argument('data')
    parser.add_argument('--recoverer', action='store_true')
    args = parser.parse_args()
    trace = Trace(args.root / f'{args.actor}.jsonl', args.actor)
    if args.recoverer:
        observed = rpc(args.port, trace, 'GET', '/read')
        write_json(args.root / f'{args.actor}-observed.json', observed)
        if (observed.get('http_status') != 200 or not observed['body']['terminal']
                or observed['body']['effect_count'] != 0):
            trace.emit('policy_decision', action='stop_without_terminal_zero', evidence=observed)
            write_json(args.root / f'{args.actor}-result.json', {'status': 'stopped', 'reason': 'no terminal zero'})
            return
        end = time.monotonic() + 10
        while not (args.root / 'release-recoverers').exists():
            if time.monotonic() > end:
                raise TimeoutError('recovery barrier watchdog')
            time.sleep(0.002)
        trace.emit('policy_decision', action='unkeyed_retry_after_current_zero', evidence=observed)
    result = rpc(args.port, trace, 'POST', '/write', json.loads(args.data), args.timeout)
    write_json(args.root / f'{args.actor}-result.json', dict(pid=trace.emit('client_finished')['pid'], **result))


if __name__ == '__main__':
    main()
