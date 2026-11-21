"""Integration against simulated Java HTTP responses; no external API calls."""

import json
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.http_backend import HttpEmployeeBackend
from app.main import app


class HttpBackendTests(unittest.TestCase):
    def setUp(self):
        self.employee = {
            'employee_code': 'EF-1001', 'name': 'Aarav Sharma', 'department': 'Engineering',
            'role': 'ENGINEER', 'permissions': ['GIT_READ', 'GIT_WRITE', 'JIRA_EDIT', 'VPN_ACCESS'], 'version': 1,
        }
        self.manager = {**self.employee, 'employee_code': 'EF-1002', 'name': 'Priya Patel', 'role': 'MANAGER'}
        self.policy = {'role': 'MANAGER', 'permissions': ['TEAM_DIRECTORY', 'REPORT_VIEW', 'JIRA_EDIT', 'VPN_ACCESS'], 'version': 1}
        self.posts = []
        self.requests_by_key = {}
        self.failure = None
        self.receipt_override = None
        self.backend = HttpEmployeeBackend('http://127.0.0.1:8081', transport=httpx.MockTransport(self.handle))
        self.patcher = patch('app.main.backend_client', self.backend)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.auth = {'Authorization': 'Bearer synthetic-user-token'}
        self.details = {'effective_date': '2026-11-23', 'justification': 'New responsibilities',
                        'manager': 'EF-1002', 'assignment_type': 'PERMANENT'}

    def handle(self, request):
        self.assertEqual(request.headers.get('Authorization'), self.auth['Authorization'])
        if self.failure:
            return self.failure(request)
        path = request.url.path
        if request.method == 'GET':
            records = {'/api/employees/EF-1001': self.employee, '/api/employees/EF-1002': self.manager,
                       '/api/roles/MANAGER/permissions': self.policy,
                       '/api/employees': [self.employee, self.manager], '/api/roles': [self.policy]}
            return httpx.Response(200, json=records[path]) if path in records else httpx.Response(404)
        self.assertEqual(path, '/api/access-requests')
        payload = json.loads(request.content)
        self.posts.append(payload)
        key = request.headers['Idempotency-Key']
        self.assertNotIn('status', payload)
        self.assertNotIn('approved_count', payload)
        receipt = {'request_id': 'AR-000001', 'action': payload['action'], 'employee_code': payload['employee_code'],
                   'status': 'PENDING_APPROVAL', 'required_approvals': 2, 'approved_count': 0}
        if self.receipt_override:
            receipt.update(self.receipt_override)
        self.requests_by_key.setdefault(key, receipt)
        return httpx.Response(201, json=self.requests_by_key[key])

    def draft(self, offboard=False, details=None):
        payload = {'employee_code': 'EF-1001', 'details': self.details if details is None else details}
        if not offboard:
            payload['target_role'] = 'MANAGER'
        response = self.client.post('/agent/offboard' if offboard else '/agent/role-change', json=payload, headers=self.auth)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['backend_mode'], 'http')
        return response.json()['plan']

    def submit(self, plan, key=None):
        return self.client.post('/agent/submit', json={'plan': plan}, headers={
            **self.auth, 'Idempotency-Key': key or str(uuid4()),
        })

    def test_http_reads_and_options_use_contract(self):
        response = self.client.get('/agent/form-options', headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['employees']), 2)
        self.assertEqual(response.json()['backend_mode'], 'http')
        draft = self.draft()
        self.assertTrue(draft['ready_for_submission'])
        self.assertEqual(draft['expected_employee_version'], 1)
        self.assertEqual(draft['expected_policy_version'], 1)
        self.assertEqual(self.posts, [])

    def test_submission_sends_validated_payload_and_idempotency_key(self):
        draft = self.draft()
        key = str(uuid4())
        first = self.submit(draft, key)
        second = self.submit(draft, key)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(self.requests_by_key), 1)
        self.assertEqual(first.json()['status'], 'PENDING_APPROVAL')
        self.assertEqual(first.json()['approved_count'], 0)
        self.assertEqual(self.posts[0]['proposed_permissions'], draft['permissions'])
        self.assertEqual(self.posts[0]['expected_policy_version'], 1)
        self.assertEqual(self.employee['role'], 'ENGINEER')

    def test_offboarding_submission_has_no_target_policy_or_grants(self):
        draft = self.draft(offboard=True, details={key: value for key, value in self.details.items() if key != 'assignment_type'})
        self.assertTrue(draft['ready_for_submission'])
        response = self.submit(draft)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('expected_policy_version', self.posts[0])
        self.assertIsNone(self.posts[0]['target_role'])
        self.assertIsNone(self.posts[0]['assignment_type'])
        self.assertEqual(self.posts[0]['proposed_permissions']['grant'], [])
        self.assertEqual(self.posts[0]['proposed_permissions']['retain'], [])

    def test_request_context_is_forwarded_as_descriptive_metadata_not_actor(self):
        draft = self.draft()
        context = {'request_title': 'Engineering leadership transition', 'priority': 'HIGH',
                   'requester_reference': 'Demo HR Operations', 'business_unit': 'Engineering'}
        draft['request_context'] = context
        response = self.submit(draft)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.posts[0]['request_context'], context)
        self.assertNotIn('actor_id', self.posts[0])
        self.assertNotIn('requested_by', self.posts[0])

    def test_modified_permissions_and_stale_snapshots_never_post(self):
        for change in ['permissions', 'employee_version', 'policy_version', 'current_access']:
            with self.subTest(change=change):
                self.employee['version'] = 1
                self.employee['permissions'] = ['GIT_READ', 'GIT_WRITE', 'JIRA_EDIT', 'VPN_ACCESS']
                self.policy['version'] = 1
                draft = self.draft()
                if change == 'permissions':
                    draft['permissions']['grant'].append('ADMIN')
                elif change == 'employee_version':
                    self.employee['version'] = 2
                elif change == 'policy_version':
                    self.policy['version'] = 2
                else:
                    self.employee['permissions'].append('NEW_ENTITLEMENT')
                response = self.submit(draft)
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(response.json()['code'], 'STALE_PLAN')
                self.assertEqual(self.posts, [])

    def test_incomplete_temporary_and_unversioned_drafts_never_post(self):
        incomplete = self.draft(details={})
        self.assertEqual(self.submit(incomplete).status_code, 422)
        temporary = self.draft(details={**self.details, 'assignment_type': 'TEMPORARY'})
        self.assertFalse(temporary['ready_for_submission'])
        self.assertEqual(self.submit(temporary).status_code, 422)
        self.employee.pop('version')
        unversioned = self.draft()
        self.assertFalse(unversioned['ready_for_submission'])
        self.assertEqual(self.submit(unversioned).json()['code'], 'VERSION_REQUIRED')
        self.assertEqual(self.posts, [])

    def test_no_change_submission_is_rejected(self):
        self.employee.update(role='MANAGER', permissions=self.policy['permissions'])
        draft = self.draft()
        response = self.submit(draft)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'NO_CHANGES')
        self.assertEqual(self.posts, [])

    def test_missing_login_and_idempotency_header_are_rejected(self):
        response = self.client.get('/agent/form-options')
        self.assertEqual(response.status_code, 401)
        draft = self.draft()
        response = self.client.post('/agent/submit', json={'plan': draft}, headers=self.auth)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.posts, [])

    def test_backend_failures_never_substitute_mock_data(self):
        for status in [401, 403, 409, 429, 500]:
            with self.subTest(status=status):
                self.failure = lambda request: httpx.Response(status, json={'private': 'HIDDEN'})
                response = self.client.post('/agent/role-change', json={
                    'employee_code': 'EF-1001', 'target_role': 'MANAGER',
                }, headers=self.auth)
                self.assertEqual(response.status_code, status if status != 500 else 502)
                self.assertNotIn('HIDDEN', response.text)
                self.assertNotIn('current_employee', response.json())

    def test_invalid_json_wrong_employee_and_wrong_policy_fail_safely(self):
        for handler in [
            lambda request: httpx.Response(200, text='not json'),
            lambda request: httpx.Response(200, json={**self.employee, 'employee_code': 'EF-9999'}),
        ]:
            self.failure = handler
            response = self.client.post('/agent/role-change', json={
                'employee_code': 'EF-1001', 'target_role': 'MANAGER',
            }, headers=self.auth)
            self.assertEqual(response.status_code, 502)
        self.failure = None
        self.policy['role'] = 'FINANCE'
        response = self.client.post('/agent/role-change', json={
            'employee_code': 'EF-1001', 'target_role': 'MANAGER',
        }, headers=self.auth)
        self.assertEqual(response.status_code, 502)

    def test_approval_or_mismatched_receipt_is_not_reported_as_success(self):
        draft = self.draft()
        for overrides in [{'status': 'APPLIED'}, {'approved_count': 1}, {'required_approvals': 1}, {'employee_code': 'EF-9999'}]:
            with self.subTest(overrides=overrides):
                self.receipt_override = overrides
                response = self.submit(draft)
                self.assertEqual(response.status_code, 502, response.text)
                self.assertEqual(response.json()['code'], 'INVALID_BACKEND_RESPONSE')

    def test_missing_employee_or_policy_stops_plan(self):
        self.failure = lambda request: httpx.Response(404)
        response = self.client.post('/agent/role-change', json={'employee_code': 'EF-1001', 'target_role': 'MANAGER'}, headers=self.auth)
        self.assertEqual(response.json()['status'], 'employee_not_found')
        self.assertIsNone(response.json()['plan'])

    def test_mock_submission_stays_disabled(self):
        from app.backend import MockEmployeeBackend
        with patch('app.main.backend_client', MockEmployeeBackend()):
            draft = self.client.post('/agent/role-change', json={
                'employee_code': 'EF-1001', 'target_role': 'MANAGER', 'details': self.details,
            }).json()['plan']
            response = self.submit(draft)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'MOCK_SUBMISSION_DISABLED')

    def test_post_timeout_is_unconfirmed_and_not_retried(self):
        draft = self.draft()
        calls = []
        original = self.handle
        def handler(request):
            if request.method == 'POST':
                calls.append(request)
                raise httpx.ReadTimeout('PRIVATE', request=request)
            return original(request)
        backend = HttpEmployeeBackend('http://127.0.0.1:8081', transport=httpx.MockTransport(handler))
        with patch('app.main.backend_client', backend):
            response = self.submit(draft)
        self.assertEqual(response.status_code, 504)
        self.assertIn('unconfirmed', response.json()['detail'])
        self.assertEqual(len(calls), 1)
        self.assertNotIn('PRIVATE', response.text)

    def test_redirects_and_unsafe_urls_are_not_followed(self):
        self.failure = lambda request: httpx.Response(302, headers={'Location': 'https://untrusted.example'})
        response = self.client.get('/agent/form-options', headers=self.auth)
        self.assertEqual(response.status_code, 502)
        for url in ['http://remote.example', 'https://user:password@example.com', 'file:///tmp/backend']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                HttpEmployeeBackend(url)
