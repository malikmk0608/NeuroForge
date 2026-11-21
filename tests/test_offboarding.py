import unittest

from fastapi.testclient import TestClient

from app.main import app


class OffboardingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_offboarding_revokes_every_current_permission_for_all_employees(self):
        for code, manager in [('EF-1001', 'EF-1002'), ('EF-1002', 'EF-1001'),
                              ('EF-1003', 'EF-1002'), ('EF-1004', 'EF-1002')]:
            with self.subTest(employee=code):
                response = self.client.post('/agent/offboard', json={
                    'employee_code': code,
                    'details': {'effective_date': '2026-11-23', 'justification': 'Employee departure', 'manager': manager},
                })
                self.assertEqual(response.status_code, 200, response.text)
                data = response.json()
                plan = data['plan']
                self.assertEqual(plan['action'], 'OFFBOARD')
                self.assertIsNone(plan['target_role'])
                self.assertEqual(plan['permissions']['grant'], [])
                self.assertEqual(plan['permissions']['retain'], [])
                self.assertEqual(plan['permissions']['revoke'], sorted(data['current_employee']['permissions']))
                self.assertTrue(plan['details_complete'])
                self.assertEqual(plan['required_approvals'], 2)
                self.assertFalse(plan['ready_for_submission'])
                self.assertEqual(plan['status'], 'DRAFT')
                repeated = self.client.post('/agent/plan', json={'message': f'Offboard {code}'}).json()
                self.assertEqual(repeated['current_employee'], data['current_employee'])

    def test_offboarding_missing_details_exclude_assignment_type(self):
        data = self.client.post('/agent/offboard', json={'employee_code': 'EF-1001'}).json()
        self.assertEqual(data['plan']['missing_details'], ['effective_date', 'justification', 'manager'])

    def test_direct_offboarding_phrasings(self):
        for message in ['Offboard EF-1001', 'Please deactivate employee ef1001.']:
            with self.subTest(message=message):
                data = self.client.post('/agent/plan', json={'message': message}).json()
                self.assertEqual(data['interpretation']['action'], 'OFFBOARD')
                self.assertEqual(data['status'], 'draft_plan_ready')

    def test_ambiguous_negative_and_mixed_actions_stop_before_lookup(self):
        for message in ['Do not offboard EF-1001', 'Offboard EF-1001 and EF-1002',
                        'Offboard EF-1001 and move to MANAGER', 'If approved offboard EF-1001',
                        'Offboard EF-1001 or keep access', 'Offboard', 'Archive EF-1001']:
            with self.subTest(message=message):
                data = self.client.post('/agent/plan', json={'message': message}).json()
                self.assertEqual(data['status'], 'needs_clarification')
                self.assertIsNone(data['plan'])

    def test_offboarding_unknown_employee(self):
        data = self.client.post('/agent/offboard', json={'employee_code': 'EF-9999'}).json()
        self.assertEqual(data['status'], 'employee_not_found')
        self.assertIsNone(data['plan'])
