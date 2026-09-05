#!/usr/bin/env python3
"""Beacon's declaration operations; all consumer paths are relative to cwd."""
import json
from pathlib import Path
import subprocess
import sys

POLICY_PATH = Path('docs/link-policy.json')
CASE_PATH = Path('tests/fixtures/link-contract.md')
EXPECTED = [
    {'text': 'Manual', 'url': '../../README.md'},
    {'text': 'Service status', 'url': 'https://status.example.invalid'},
]
POLICY = {
    'scope': 'local-only',
    'network': False,
    'reference_case': CASE_PATH.as_posix(),
    'expected_links': EXPECTED,
}
CASE = '''# Extraction contract

[Manual](../../README.md) and [Service status](https://status.example.invalid)

These destinations are inventory data. This example makes no network requests.
'''


def inspect_contract():
    policy = json.loads(POLICY_PATH.read_text())
    for key, expected in POLICY.items():
        if policy.get(key) != expected:
            raise ValueError(f'{POLICY_PATH}: unexpected {key}')
    completed = subprocess.run(
        [sys.executable, 'app.py', str(CASE_PATH)],
        capture_output=True, text=True, timeout=10,
    )
    if completed.returncode:
        raise ValueError(f'consumer exited {completed.returncode}: {completed.stderr.strip()}')
    if json.loads(completed.stdout) != policy['expected_links']:
        raise ValueError('consumer inventory differs from docs/link-policy.json expected_links')
    return 'policy, Markdown example, and observed consumer inventory agree'


def main():
    context = json.load(sys.stdin)
    action = sys.argv[1]
    with Path('.author-trace.jsonl').open('a') as trace:
        trace.write(json.dumps({
            'publisher': 'beacon',
            'argv': sys.argv,
            'cwd': str(Path.cwd()),
            'declaration': context['declaration'],
            'selection': context['selection'],
        }, sort_keys=True) + '\n')
    if action == 'fix-contract':
        POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
        CASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        POLICY_PATH.write_text(json.dumps(POLICY, indent=2) + '\n')
        CASE_PATH.write_text(CASE)
        return 'wrote docs/link-policy.json and tests/fixtures/link-contract.md'
    if action == 'check-contract':
        return inspect_contract()
    if action == 'readiness':
        completed = subprocess.run(
            [sys.executable, 'app.py', '--help'],
            capture_output=True, text=True, timeout=10,
        )
        if completed.returncode or not completed.stdout.strip():
            raise ValueError('consumer must expose a working nonempty --help response')
        return 'consumer command reference is available from --help'
    raise ValueError(f'unknown declaration operation: {action}')


if __name__ == '__main__':
    try:
        message = main()
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'fail', 'message': str(error)}))
        sys.exit(1)
    print(json.dumps({'status': 'pass', 'message': message}))
