import asyncio
import unittest

from fastapi.testclient import TestClient

from app.backend import MockEmployeeBackend
from app.graph import build_graph
from app.main import app
from app.planner import compare_permission_sets


class PlanningTests(unittest.TestCase):
    def test_manager_to_engineer(self):
        with TestClient(app) as client:
            data = client.post('/agent/plan', json={'message': 'Demote EF-1002 to ENGINEER'}).json()
        self.assertEqual(data['status'], 'draft_plan_ready')
        plan = data['plan']
        self.assertEqual(plan['permissions'], {
            'grant': ['GIT_READ', 'GIT_WRITE'],
            'revoke': ['REPORT_VIEW', 'TEAM_DIRECTORY'],
            'retain': ['JIRA_EDIT', 'VPN_ACCESS'],
        })
        self.assertEqual(plan['status'], 'DRAFT')
        self.assertEqual(plan['required_approvals'], 2)
        self.assertFalse(plan['ready_for_submission'])
        self.assertTrue(plan['missing_details'])
        self.assertTrue(all(step['status'] == 'completed' for step in data['activity_steps']))

    def test_same_role_is_no_change(self):
        with TestClient(app) as client:
            plan = client.post('/agent/plan', json={'message': 'Move EF-1001 to ENGINEER'}).json()['plan']
        self.assertFalse(plan['has_changes'])
        self.assertEqual(plan['permissions']['grant'], [])
        self.assertEqual(plan['permissions']['revoke'], [])
        self.assertEqual(len(plan['permissions']['retain']), 4)

    def test_all_sample_transitions_reconstruct_target_permissions(self):
        async def check():
            backend = MockEmployeeBackend()
            graph = build_graph(backend)
            for code in ['EF-1001', 'EF-1002', 'EF-1003', 'EF-1004']:
                for role in ['ENGINEER', 'MANAGER', 'HR', 'FINANCE']:
                    with self.subTest(employee=code, target=role):
                        result = await graph.ainvoke({'message': f'Move {code} to {role}', 'activity_steps': []})
                        plan = result['plan']
                        current = set(result['current_employee'].permissions)
                        policy = await backend.get_role_policy(role)
                        changes = plan.permissions
                        self.assertEqual((current - set(changes.revoke)) | set(changes.grant), set(policy.permissions))
                        self.assertFalse(set(changes.grant) & current)
                        self.assertEqual(set(changes.retain) | set(changes.revoke), current)
                        unchanged = await backend.get_employee(code)
                        self.assertEqual(unchanged, result['current_employee'])
        asyncio.run(check())

    def test_missing_policy_does_not_generate_plan(self):
        class MissingPolicyBackend(MockEmployeeBackend):
            async def get_role_policy(self, role):
                return None

        result = asyncio.run(build_graph(MissingPolicyBackend()).ainvoke({
            'message': 'Move EF-1001 to MANAGER', 'activity_steps': [],
        }))
        self.assertNotIn('plan', result)
        self.assertEqual(len(result['activity_steps']), 3)
        self.assertEqual(result['activity_steps'][-1].status, 'not_found')

    def test_duplicate_permissions_are_deduplicated(self):
        changes = compare_permission_sets(['A', 'A', 'B'], ['B', 'C', 'C'])
        self.assertEqual(changes.model_dump(), {'grant': ['C'], 'revoke': ['A'], 'retain': ['B']})
