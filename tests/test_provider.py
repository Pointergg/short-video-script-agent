import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from script_agent.providers import OpenAICompatibleProvider


class ProviderTests(unittest.TestCase):
    def provider(self):
        with patch.dict(os.environ, {"SCRIPT_AGENT_API_KEY": "test-not-a-real-key", "SCRIPT_AGENT_BASE_URL": "https://example.invalid/v1", "SCRIPT_AGENT_MODEL": "test-model"}):
            return OpenAICompatibleProvider()

    def test_json_action_transport(self):
        action = {"action": "search_materials", "arguments": {"query": "字幕"}, "reason": "寻找来源"}
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps(action)}}]}).encode())
        with patch("urllib.request.urlopen", return_value=response) as call:
            self.assertEqual(self.provider().decide({"request": {}}, []), action)
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.invalid/v1/chat/completions")
        self.assertNotIn("test-not-a-real-key", request.data.decode())

    def test_http_error_body_does_not_leak(self):
        error = urllib.error.HTTPError("https://example.invalid", 401, "bad", {}, io.BytesIO(b"secret-server-body"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "^MODEL_HTTP_401$"):
                self.provider().decide({}, [])

    def test_timeout_fails_instead_of_switching_to_mock(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            with self.assertRaisesRegex(RuntimeError, "MODEL_CONNECTION_FAILED"):
                self.provider().decide({}, [])

    def test_broken_response_is_explicit_failure(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b'{"choices":[]}')):
            with self.assertRaisesRegex(RuntimeError, "MODEL_INVALID_RESPONSE"):
                self.provider().decide({}, [])

    def test_missing_key_and_insecure_endpoint_rejected(self):
        with patch.dict(os.environ, {"SCRIPT_AGENT_API_KEY": ""}):
            with self.assertRaises(ValueError):
                OpenAICompatibleProvider()
        with patch.dict(os.environ, {"SCRIPT_AGENT_API_KEY": "test", "SCRIPT_AGENT_BASE_URL": "http://example.invalid"}):
            with self.assertRaises(ValueError):
                OpenAICompatibleProvider()


if __name__ == "__main__":
    unittest.main()
