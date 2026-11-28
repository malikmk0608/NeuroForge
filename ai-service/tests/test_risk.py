import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.risk import suggest_risk
from app.schemas import PermissionChanges


class RiskTests(unittest.TestCase):
    def test_representative_plans_have_explained_risk_and_two_required_approvals(self):
        for message, expected in [
            ('Move EF-1001 to ENGINEER', 'LOW'),
            ('Move EF-1001 to MANAGER', 'MEDIUM'),
            ('Move EF-1002 to ENGINEER', 'MEDIUM'),
            ('Move EF-1001 to HR', 'HIGH'),
            ('Move EF-1001 to FINANCE', 'HIGH'),
            ('Offboard EF-1001', 'HIGH'),
        ]:
            with self.subTest(message=message), TestClient(app) as client:
                plan = client.post('/agent/plan', json={'message': message}).json()['plan']
                risk = plan['risk_suggestion']
                self.assertEqual(risk['level'], expected)
                self.assertTrue(risk['reasons'])
                self.assertTrue(risk['advisory_only'])
                self.assertEqual(risk['rules_version'], 'demo-v1')
                self.assertEqual(plan['required_approvals'], 2)
                self.assertFalse(plan['ready_for_submission'])

    def test_unknown_new_permission_is_flagged(self):
        result = suggest_risk('ROLE_CHANGE', PermissionChanges(grant=['NEW_PRIVILEGE'], revoke=[], retain=[]), True)
        self.assertEqual(result.level, 'HIGH')
        self.assertIn('NEW_PRIVILEGE', result.reasons[0])

    def test_role_only_change_is_not_mistaken_for_no_change(self):
        result = suggest_risk('ROLE_CHANGE', PermissionChanges(grant=[], revoke=[], retain=['GIT_READ']), True)
        self.assertEqual(result.level, 'MEDIUM')

    def test_retained_sensitive_access_is_not_described_as_newly_granted(self):
        result = suggest_risk('ROLE_CHANGE', PermissionChanges(grant=['GIT_READ'], revoke=[], retain=['HRIS_READ']), True)
        self.assertEqual(result.level, 'MEDIUM')
        self.assertFalse(any('New HR' in reason for reason in result.reasons))
