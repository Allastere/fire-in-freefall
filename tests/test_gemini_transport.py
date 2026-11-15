"""Exercise actual SDK serialization with an offline HTTP transport."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx2 as httpx
from google import genai
from google.genai import types

from si.gemini_client import GeminiClient
from si.insights import GroundedInsight


class GeminiTransportTests(unittest.TestCase):
    def test_nested_strict_schema_uses_json_schema_on_the_wire(self):
        requests = []

        def respond(request):
            body = json.loads(request.content)
            requests.append(body)
            config = body["generationConfig"]
            self.assertNotIn("responseSchema", config)
            self.assertEqual(config["responseJsonSchema"], GroundedInsight.model_json_schema())
            return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [
                {"text": json.dumps({"observations": [], "interpretations": [],
                                     "limitations": ["No experimental evidence supplied."]})}]}},]})

        with TemporaryDirectory() as directory:
            client = GeminiClient(api_key="test-placeholder", db_path=Path(directory) / "absent.db",
                                  cache_writes=False)
            with genai.Client(api_key="test-placeholder", http_options=types.HttpOptions(
                    client_args={"transport": httpx.MockTransport(respond)})) as sdk:
                client.client = sdk
                answer = client.generate("No experimental evidence supplied.", GroundedInsight)
            self.assertIsInstance(answer, GroundedInsight)
            self.assertEqual(len(requests), 1)


if __name__ == "__main__":
    unittest.main()
