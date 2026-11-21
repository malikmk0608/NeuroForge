import asyncio
import json
import os
import unittest
from unittest.mock import patch

import httpx

from app.model_interpreter import ModelUnavailable, interpret_with_model
from app.schemas import RequestDetails

EXTRACTION = {
    'is_direct_request': True, 'action': 'ROLE_CHANGE', 'employee_code': 'EF-1001',
    'target_role': 'MANAGER', 'effective_date': None, 'justification': None,
    'manager': None, 'assignment_type': None, 'clarification_questions': [],
}


class GroqTests(unittest.TestCase):
    def run_model(self, handler):
        with patch.dict(os.environ, {
            'LLM_PROVIDER': 'groq', 'GROQ_API_KEY': 'test-groq-key',
            'GROQ_MODEL': 'openai/gpt-oss-20b', 'OPENAI_API_KEY': 'unused-openai-key',
        }):
            return asyncio.run(interpret_with_model(
                'Give EF-1001 the MANAGER role', RequestDetails(), transport=httpx.MockTransport(handler),
            ))

    def test_groq_uses_correct_host_key_schema_and_validation(self):
        def handler(request):
            self.assertEqual(str(request.url), 'https://api.groq.com/openai/v1/chat/completions')
            self.assertEqual(request.headers['Authorization'], 'Bearer test-groq-key')
            body = json.loads(request.content)
            self.assertEqual(body['model'], 'openai/gpt-oss-20b')
            self.assertTrue(body['response_format']['json_schema']['strict'])
            self.assertNotIn('tools', body)
            self.assertNotIn('unused-openai-key', request.content.decode())
            return httpx.Response(200, json={'choices': [{
                'finish_reason': 'stop', 'message': {'content': json.dumps(EXTRACTION)},
            }]})
        interpretation, _, issues = self.run_model(handler)
        self.assertEqual(interpretation.employee_code, 'EF-1001')
        self.assertEqual(issues, [])

    def test_incomplete_refused_malformed_and_extra_fields_are_rejected(self):
        for body in [
            {'choices': []},
            {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]},
            {'choices': [{'finish_reason': 'stop', 'message': {'refusal': 'Cannot comply'}}]},
            {'choices': [{'finish_reason': 'stop', 'message': {'content': 'not JSON'}}]},
            {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({**EXTRACTION, 'apply': True})}}]},
        ]:
            with self.subTest(body=body), self.assertRaises(ModelUnavailable):
                self.run_model(lambda request: httpx.Response(200, json=body))

    def test_groq_error_identifies_provider_without_exposing_body(self):
        with self.assertRaises(ModelUnavailable) as error:
            self.run_model(lambda request: httpx.Response(401, json={'message': 'PRIVATE'}))
        self.assertIn('Groq', str(error.exception))
        self.assertIn('GROQ_API_KEY', str(error.exception))
        self.assertNotIn('PRIVATE', str(error.exception))

    def test_missing_groq_configuration_does_not_fall_back_to_openai(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'groq', 'GROQ_API_KEY': '', 'GROQ_MODEL': ''}):
            with self.assertRaises(ModelUnavailable) as error:
                asyncio.run(interpret_with_model('Move EF-1001 to MANAGER', RequestDetails()))
        self.assertIn('not configured for Groq', str(error.exception))

    def test_unknown_provider_is_rejected(self):
        with patch.dict(os.environ, {'LLM_PROVIDER': 'unknown'}), self.assertRaises(ModelUnavailable):
            asyncio.run(interpret_with_model('Move EF-1001 to MANAGER', RequestDetails()))
