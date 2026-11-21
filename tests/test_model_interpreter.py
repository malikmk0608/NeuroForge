import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.model_interpreter import ExtractedRequest, ModelUnavailable, interpret_with_model, validate_extraction
from app.schemas import RequestDetails

EXTRACTION = {
    'is_direct_request': True, 'action': 'ROLE_CHANGE', 'employee_code': 'EF-1001',
    'target_role': 'MANAGER', 'effective_date': None, 'justification': None,
    'manager': None, 'assignment_type': None, 'clarification_questions': [],
}


def response_body(extraction):
    return {'status': 'completed', 'output': [{'type': 'message', 'content': [
        {'type': 'output_text', 'text': json.dumps(extraction)},
    ]}]}


class ModelInterpreterTests(unittest.TestCase):
    def run_model(self, handler):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key', 'OPENAI_MODEL': 'test-model'}):
            return asyncio.run(interpret_with_model(
                'Could you give EF-1001 the MANAGER role?', RequestDetails(),
                transport=httpx.MockTransport(handler),
            ))

    def test_structured_api_request_and_response(self):
        def handler(request):
            self.assertEqual(str(request.url), 'https://api.openai.com/v1/responses')
            body = json.loads(request.content)
            self.assertFalse(body['store'])
            self.assertNotIn('tools', body)
            self.assertEqual(body['text']['format']['type'], 'json_schema')
            schema = body['text']['format']['schema']
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(set(schema['required']), set(schema['properties']))
            return httpx.Response(200, json=response_body(EXTRACTION))
        interpretation, details, issues = self.run_model(handler)
        self.assertEqual(interpretation.employee_code, 'EF-1001')
        self.assertEqual(interpretation.target_role, 'MANAGER')
        self.assertEqual(issues, [])

    def test_refusal_incomplete_and_invalid_output(self):
        for body in [
            {'status': 'incomplete', 'output': []},
            {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal'}]}]},
            {'status': 'completed', 'output': []},
            response_body({**EXTRACTION, 'permissions': ['ADMIN']}),
        ]:
            with self.subTest(body=body), self.assertRaises(ModelUnavailable):
                self.run_model(lambda request: httpx.Response(200, json=body))

    def test_provider_error_does_not_expose_response_body(self):
        with self.assertRaises(ModelUnavailable) as error:
            self.run_model(lambda request: httpx.Response(401, json={'secret': 'DO-NOT-EXPOSE'}))
        self.assertNotIn('DO-NOT-EXPOSE', str(error.exception))
        self.assertNotIn('test-key', str(error.exception))

    def test_timeout_has_safe_error(self):
        def timeout(request):
            raise httpx.ReadTimeout('private diagnostic', request=request)
        with self.assertRaises(ModelUnavailable) as error:
            self.run_model(timeout)
        self.assertNotIn('private diagnostic', str(error.exception))
        self.assertIn('timed out', str(error.exception))

    def test_provider_failure_categories_have_actionable_safe_messages(self):
        for status, code, expected in [
            (401, 'invalid_api_key', 'API key'),
            (403, 'forbidden', 'denied access'),
            (429, 'insufficient_quota', 'insufficient quota'),
            (429, 'rate_limit_exceeded', 'rate-limited'),
            (400, 'invalid_request', 'configured model'),
            (500, 'internal_error', 'service returned an error'),
        ]:
            with self.subTest(status=status, code=code), self.assertRaises(ModelUnavailable) as error:
                self.run_model(lambda request: httpx.Response(status, json={
                    'error': {'code': code, 'message': 'PRIVATE PROVIDER DETAILS'},
                }))
            self.assertIn(expected, str(error.exception))
            self.assertNotIn('PRIVATE PROVIDER DETAILS', str(error.exception))

    def test_unconfigured_model_returns_503_but_default_form_still_works(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'openai', 'OPENAI_API_KEY': '', 'OPENAI_MODEL': ''}), TestClient(app) as client:
            response = client.post('/agent/plan', json={'message': 'Move EF-1001 to MANAGER', 'use_model': True})
            self.assertEqual(response.status_code, 503)
            self.assertIn('not configured', response.json()['detail'])
            self.assertEqual(client.post('/agent/role-change', json={
                'employee_code': 'EF-1001', 'target_role': 'MANAGER',
            }).status_code, 200)

    def test_invented_employee_and_unstated_role_are_not_accepted(self):
        interpretation, _, _ = validate_extraction(
            ExtractedRequest(**EXTRACTION), 'Please change someone to a different role', RequestDetails(),
        )
        self.assertIsNone(interpretation.employee_code)
        self.assertIsNone(interpretation.target_role)
        self.assertTrue(interpretation.clarification_questions)

    def test_invented_detail_and_structured_conflict_require_clarification(self):
        _, details, issues = validate_extraction(
            ExtractedRequest(**{**EXTRACTION, 'manager': 'EF-1002', 'justification': 'Invented reason'}),
            'Move EF-1001 to MANAGER; manager EF-1002', RequestDetails(manager='EF-1003'),
        )
        self.assertEqual(details.manager, 'EF-1003')
        self.assertIsNone(details.justification)
        self.assertEqual(len(issues), 2)

    def test_model_result_uses_same_graph_and_permission_calculation(self):
        extraction = (ExtractedRequest(**EXTRACTION))
        interpreted = validate_extraction(extraction, 'Give EF-1001 the MANAGER role', RequestDetails())
        with patch('app.graph.interpret_with_model', new=AsyncMock(return_value=interpreted)), TestClient(app) as client:
            data = client.post('/agent/plan', json={
                'message': 'Give EF-1001 the MANAGER role', 'use_model': True,
            }).json()
        self.assertEqual(data['plan']['permissions']['grant'], ['REPORT_VIEW', 'TEAM_DIRECTORY'])
        self.assertFalse(data['plan']['ready_for_submission'])
        self.assertIn('model-assisted', data['activity_steps'][0]['message'])

    def test_model_cannot_override_local_negative_conditional_or_multi_employee_checks(self):
        for message in [
            'Do not move EF-1001 to MANAGER', 'If approved move EF-1001 to MANAGER',
            'How do I move EF-1001 to MANAGER?', 'Move EF-1001 and EF-1002 to MANAGER',
            'Archive EF-1001 as MANAGER',
        ]:
            with self.subTest(message=message):
                interpretation, _, _ = validate_extraction(ExtractedRequest(**EXTRACTION), message, RequestDetails())
                self.assertTrue(interpretation.clarification_questions)
