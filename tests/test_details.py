import unittest

from fastapi.testclient import TestClient

from app.main import app


class RequestDetailsTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.details = {
            'effective_date': '2026-11-23',
            'justification': 'Taking responsibility for the engineering team.',
            'manager': 'EF-1002',
            'assignment_type': 'PERMANENT',
        }

    def plan(self, details):
        response = self.client.post('/agent/plan', json={
            'message': 'Move EF-1001 to MANAGER', 'details': details,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['plan']

    def test_complete_details_are_preserved_without_enabling_submission(self):
        plan = self.plan(self.details)
        self.assertEqual(plan['details'], self.details)
        self.assertTrue(plan['details_complete'])
        self.assertEqual(plan['missing_details'], [])
        self.assertEqual(plan['clarification_questions'], [])
        self.assertFalse(plan['ready_for_submission'])
        self.assertEqual(plan['status'], 'DRAFT')

    def test_partial_details_only_ask_for_missing_values(self):
        plan = self.plan({'justification': 'New team responsibilities'})
        self.assertEqual(plan['missing_details'], ['effective_date', 'manager', 'assignment_type'])
        self.assertEqual(len(plan['clarification_questions']), 3)
        self.assertFalse(plan['details_complete'])

    def test_invalid_details_are_rejected(self):
        for updates in [
            {'effective_date': '2026-02-30'}, {'justification': '   '},
            {'assignment_type': 'UNKNOWN'}, {'manager': 'Priya'},
            {'unexpected_field': True},
        ]:
            with self.subTest(updates=updates):
                response = self.client.post('/agent/plan', json={
                    'message': 'Move EF-1001 to MANAGER', 'details': {**self.details, **updates},
                })
                self.assertEqual(response.status_code, 422, response.text)

    def test_unknown_or_self_manager_requires_correction(self):
        for manager in ['EF-9999', 'EF-1001']:
            with self.subTest(manager=manager):
                plan = self.plan({**self.details, 'manager': manager})
                self.assertFalse(plan['details_complete'])
                self.assertEqual(plan['missing_details'], [])
                self.assertEqual(len(plan['clarification_questions']), 1)

    def test_request_details_do_not_leak_between_requests(self):
        self.plan(self.details)
        plan = self.plan({})
        self.assertEqual(len(plan['missing_details']), 4)
        self.assertIsNone(plan['details']['manager'])
