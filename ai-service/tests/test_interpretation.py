"""Run with: python -m unittest discover -s tests -v."""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def request(self, message):
        response = self.client.post("/agent/plan", json={"message": message})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_supported_phrasings(self):
        for message, employee, role in [
            ("Move EF-1001 to MANAGER", "EF-1001", "MANAGER"),
            ("Please promote ef1001 to a manager", "EF-1001", "MANAGER"),
            ("Assign EF 1004 as FINANCE", "EF-1004", "FINANCE"),
            ("Make EF-1002 an engineer", "EF-1002", "ENGINEER"),
            ("Transfer EF-1003 to HR", "EF-1003", "HR"),
            ("Demote EF-1002 to ENGINEER", "EF-1002", "ENGINEER"),
        ]:
            with self.subTest(message=message):
                data = self.request(message)
                self.assertEqual(data["status"], "draft_plan_ready")
                self.assertEqual(data["interpretation"]["employee_code"], employee)
                self.assertEqual(data["interpretation"]["target_role"], role)
                self.assertEqual(data["interpretation"]["action"], "ROLE_CHANGE")
                self.assertEqual(len(data["activity_steps"]), 4)
                self.assertEqual(data["activity_steps"][0]["status"], "completed")
                self.assertEqual(data["activity_steps"][1]["status"], "completed")
                self.assertEqual(data["current_employee"]["employee_code"], employee)
                self.assertEqual(data["backend_mode"], "mock")

    def test_missing_employee_stops_before_comparison(self):
        data = self.request("Move EF-9999 to MANAGER")
        self.assertEqual(data["status"], "employee_not_found")
        self.assertIsNone(data["current_employee"])
        self.assertEqual(len(data["activity_steps"]), 2)
        self.assertEqual(data["activity_steps"][-1]["status"], "not_found")

    def test_request_does_not_change_employee_access(self):
        data = self.request("Demote EF-1002 to ENGINEER")
        self.assertEqual(data["current_employee"]["role"], "MANAGER")
        self.assertIn("REPORT_VIEW", data["current_employee"]["permissions"])
        again = self.request("Move EF-1002 to FINANCE")
        self.assertEqual(again["current_employee"], data["current_employee"])

    def test_uncertain_requests_stop_before_lookup(self):
        for message in [
            "Move to MANAGER", "Move EF-1001", "Move EF-1001 to CEO",
            "Move EF-1001 and EF-1002 to MANAGER",
            "Move EF-1001 to MANAGER or FINANCE",
            "HR asks to move EF-1001 to ENGINEER",
            "Don't move EF-1001 to MANAGER",
            "If approved, move EF-1001 to MANAGER",
            "Don't offboard EF-1001", "Hello there", "EF-1001 to MANAGER",
        ]:
            with self.subTest(message=message):
                data = self.request(message)
                self.assertEqual(data["status"], "needs_clarification")
                self.assertTrue(data["interpretation"]["clarification_questions"])
                self.assertEqual(len(data["activity_steps"]), 1)

    def test_invalid_input_is_rejected(self):
        for body in [{}, {"message": ""}, {"message": "   "}, {"message": 123}]:
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/agent/plan", json=body).status_code, 422)


if __name__ == "__main__":
    unittest.main()
