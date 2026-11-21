import unittest

from fastapi.testclient import TestClient

from app.main import app


class DetailExtractionTests(unittest.TestCase):
    def request(self, message, details=None):
        with TestClient(app) as client:
            response = client.post('/agent/plan', json={'message': message, 'details': details or {}})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_message_extracts_all_details_and_separates_manager(self):
        data = self.request(
            'Move EF-1001 to MANAGER effective on 2026-11-23; '
            'because Leading the engineering team; manager ef1002; assignment type permanent'
        )
        self.assertEqual(data['interpretation']['employee_code'], 'EF-1001')
        self.assertEqual(data['interpretation']['target_role'], 'MANAGER')
        self.assertEqual(data['plan']['details'], {
            'effective_date': '2026-11-23', 'justification': 'Leading the engineering team',
            'manager': 'EF-1002', 'assignment_type': 'PERMANENT',
        })
        self.assertTrue(data['plan']['details_complete'])

    def test_labeled_multiline_details(self):
        data = self.request('Demote EF-1002 to ENGINEER\neffective date: 2026-11-23\n'
                            'justification: Returning to development\nmanager: EF-1001\nassignment type: PERMANENT')
        self.assertTrue(data['plan']['details_complete'])
        self.assertEqual(data['interpretation']['employee_code'], 'EF-1002')

    def test_text_and_structured_conflict_requires_correction(self):
        data = self.request('Move EF-1001 to MANAGER; manager: EF-1002', {'manager': 'EF-1003'})
        self.assertFalse(data['plan']['details_complete'])
        self.assertTrue(any('conflicts' in question for question in data['plan']['clarification_questions']))

    def test_invalid_or_repeated_text_details_require_correction(self):
        for clause in ['effective date: 2026-02-30', 'manager: Priya',
                       'assignment type: unknown', 'manager: EF-1002; manager: EF-1003']:
            with self.subTest(clause=clause):
                data = self.request('Move EF-1001 to MANAGER; ' + clause)
                self.assertFalse(data['plan']['details_complete'])
                self.assertTrue(any('invalid' in question or 'conflicting' in question
                                    for question in data['plan']['clarification_questions']))

    def test_unmarked_second_employee_is_still_ambiguous(self):
        data = self.request('Move EF-1001 and EF-1002 to MANAGER')
        self.assertEqual(data['status'], 'needs_clarification')
        self.assertIsNone(data['plan'])
