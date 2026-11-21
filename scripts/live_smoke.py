"""Opt-in synthetic Groq checks against a local mock-mode server.

Print the cases without network calls: python scripts/live_smoke.py
Run explicitly: python scripts/live_smoke.py --run --output docs/live-smoke-results.json
No secrets are read by this script. It uses the running server's configuration.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx

CASES = [
    ("role change", "Could you give EF-1001 the MANAGER role?", "draft_plan_ready", "ROLE_CHANGE", "MANAGER"),
    ("demotion", "Please downgrade EF-1002 to ENGINEER.", "draft_plan_ready", "ROLE_CHANGE", "ENGINEER"),
    ("offboarding", "Please offboard EF-1004.", "draft_plan_ready", "OFFBOARD", None),
    ("negative request", "Do not move EF-1001 to MANAGER.", "needs_clarification", None, None),
    ("unsupported role", "Move EF-1001 to CEO.", "needs_clarification", None, None),
    ("missing employee", "Move to MANAGER.", "needs_clarification", None, None),
    ("complete metadata", "Move EF-1001 to MANAGER; effective date: 2026-11-23; justification: Leading the engineering team; manager: EF-1002; assignment type: PERMANENT", "draft_plan_ready", "ROLE_CHANGE", "MANAGER"),
    ("undefined archival", "Archive EF-1001.", "needs_clarification", None, None),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8002')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.run:
        for name, message, *_ in CASES:
            print(f'{name}: {message}')
        print('No network calls made. --run sends these synthetic fixtures to Groq through the local server.')
        return
    parsed = urlsplit(args.base_url)
    if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
        raise SystemExit('Only a local server URL without embedded credentials is supported.')
    results = []
    with httpx.Client(base_url=args.base_url.rstrip('/'), timeout=40) as client:
        health = client.get('/health')
        health.raise_for_status()
        state = health.json()
        if state.get('backend_mode') != 'mock' or state.get('model') != {'provider': 'groq', 'configured': True}:
            raise SystemExit('This test requires mock employee data and an explicitly configured Groq provider.')
        for name, message, expected, action, target in CASES:
            response = client.post('/agent/plan', json={'message': message, 'use_model': True})
            data = response.json()
            passed = response.status_code == 200 and data.get('status') == expected
            if passed and action:
                passed = data['interpretation']['action'] == action and data['interpretation']['target_role'] == target
                passed = passed and data['plan']['required_approvals'] == 2 and not data['plan']['ready_for_submission']
                if action == 'OFFBOARD':
                    changes = data['plan']['permissions']
                    passed = passed and not changes['grant'] and not changes['retain'] and set(changes['revoke']) == set(data['current_employee']['permissions'])
                if name == 'complete metadata':
                    passed = passed and data['plan']['details_complete']
            result = {'case': name, 'http_status': response.status_code, 'expected_status': expected,
                      'actual_status': data.get('status'), 'passed': bool(passed)}
            if not passed and response.status_code == 200:
                result['interpretation'] = data.get('interpretation')
            if response.status_code != 200:
                result['safe_error'] = data.get('detail', 'Request failed')
            results.append(result)
            print(f'{"PASS" if passed else "FAIL"}: {name} (HTTP {response.status_code})', flush=True)
            if response.status_code != 200:
                print('Stopped after provider/server error; no automatic retries.', flush=True)
                break
    report = {'provider': 'groq', 'employee_backend': 'mock', 'synthetic_data_only': True,
              'planned_cases': len(CASES), 'executed_cases': len(results), 'results': results}
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if len(results) != len(CASES) or not all(result['passed'] for result in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
