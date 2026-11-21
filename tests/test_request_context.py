import unittest

from fastapi.testclient import TestClient

from app.main import app


class RequestContextTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_context_is_preserved_without_changing_permissions_risk_or_approvals(self):
        context = {
            'request_title': 'Engineering leadership transition',
            'priority': 'HIGH',
            'requester_reference': 'HR Operations (demo)',
            'business_unit': 'Platform Engineering',
        }
        data = self.client.post('/agent/role-change', json={
            'employee_code': 'EF-1001', 'target_role': 'MANAGER', 'request_context': context,
        }).json()
        plan = data['plan']
        self.assertEqual(plan['request_context'], context)
        self.assertEqual(plan['permissions']['grant'], ['REPORT_VIEW', 'TEAM_DIRECTORY'])
        self.assertEqual(plan['risk_suggestion']['level'], 'MEDIUM')
        self.assertEqual(plan['required_approvals'], 2)
        self.assertFalse(plan['ready_for_submission'])

    def test_context_is_optional_and_does_not_add_required_detail_questions(self):
        data = self.client.post('/agent/offboard', json={'employee_code': 'EF-1001'}).json()
        self.assertEqual(data['plan']['request_context']['priority'], 'NORMAL')
        self.assertIsNone(data['plan']['request_context']['requester_reference'])
        self.assertEqual(data['plan']['missing_details'], ['effective_date', 'justification', 'manager'])

    def test_context_rejects_actor_override_and_invalid_priority(self):
        for context in [{'actor_id': 'admin'}, {'priority': 'URGENT'}, {'request_title': '   '}]:
            with self.subTest(context=context):
                response = self.client.post('/agent/role-change', json={
                    'employee_code': 'EF-1001', 'target_role': 'MANAGER', 'request_context': context,
                })
                self.assertEqual(response.status_code, 422)
