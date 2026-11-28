import unittest

from fastapi.testclient import TestClient

from app.main import app
from unittest.mock import patch
import os


class FormTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_form_and_assets_are_served(self):
        for path in ['/', '/static/app.js', '/static/styles.css']:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_options_come_from_mock_backend(self):
        data = self.client.get('/agent/form-options').json()
        self.assertEqual(data['backend_mode'], 'mock')
        self.assertEqual(len(data['employees']), 7)
        self.assertEqual(sum(e['department'] == 'Engineering' for e in data['employees']), 5)
        self.assertEqual(set(data['roles']), {'ENGINEER', 'MANAGER', 'HR', 'FINANCE'})

    def test_form_and_message_routes_produce_same_plan(self):
        details = {'effective_date': '2026-11-23', 'justification': 'Leading the team',
                   'manager': 'EF-1002', 'assignment_type': 'PERMANENT'}
        form = self.client.post('/agent/role-change', json={
            'employee_code': 'EF-1001', 'target_role': 'MANAGER', 'details': details,
        })
        message = self.client.post('/agent/plan', json={
            'message': 'Move EF-1001 to MANAGER', 'details': details,
        })
        self.assertEqual(form.status_code, 200, form.text)
        self.assertEqual(form.json()['plan'], message.json()['plan'])

    def test_form_rejects_invalid_employee_and_role(self):
        for updates in [{'employee_code': 'Aarav'}, {'target_role': 'CEO'}]:
            response = self.client.post('/agent/role-change', json={
                'employee_code': 'EF-1001', 'target_role': 'MANAGER', **updates,
            })
            self.assertEqual(response.status_code, 422)

    def test_capability_metadata_contains_no_keys(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'groq', 'GROQ_API_KEY': 'NEVER-EXPOSE-THIS', 'GROQ_MODEL': 'test'}):
            for path in ['/health', '/agent/form-options']:
                response = self.client.get(path)
                self.assertEqual(response.json()['model'], {'provider': 'groq', 'configured': True})
                self.assertNotIn('NEVER-EXPOSE-THIS', response.text)

    def test_partial_response_exposes_details_for_form_prefill(self):
        response = self.client.post('/agent/plan', json={
            'message': 'Move to MANAGER', 'details': {'justification': 'Team responsibilities'},
        })
        self.assertEqual(response.json()['status'], 'needs_clarification')
        self.assertEqual(response.json()['extracted_details']['justification'], 'Team responsibilities')
