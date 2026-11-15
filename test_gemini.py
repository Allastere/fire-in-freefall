"""Offline cache regression tests. Run with: python test_gemini.py."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import BaseModel

from database.connection import SCHEMA_DDL
from si.gemini_client import GeminiClient


class StructuredAnswer(BaseModel):
    answer: str


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "cache.db"
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.executescript(SCHEMA_DDL)
        self.client = GeminiClient(api_key="test-placeholder", db_path=self.db_path)
        self.api = Mock()
        self.api.models.generate_content.return_value = SimpleNamespace(text="Cache test successful")
        self.client.client = self.api

    def put_raw_cache(self, prompt, raw_json, schema=None):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO llm_cache (prompt_hash, model_name, response_json) VALUES (?, ?, ?)",
                (self.client._generate_hash(prompt, schema), self.client.model_name, raw_json),
            )

    def test_second_request_and_offline_client_skip_api(self):
        first = self.client.generate("cache test")
        self.assertEqual(first, "Cache test successful")
        self.assertEqual(self.client.generate("cache test"), first)
        self.api.models.generate_content.assert_called_once()
        offline = GeminiClient(model_name=self.client.model_name, db_path=self.db_path)
        offline.api_key = None
        with patch.object(offline, "_get_client", side_effect=AssertionError("API accessed")):
            self.assertEqual(offline.generate("cache test"), first)

    def test_structured_roundtrip(self):
        self.api.models.generate_content.return_value = SimpleNamespace(text='{"answer":"ok"}')
        first = self.client.generate("structured", StructuredAnswer)
        self.assertIsInstance(first, StructuredAnswer)
        self.assertEqual(self.client.generate("structured", StructuredAnswer), first)
        self.api.models.generate_content.assert_called_once()

    def test_invalid_structured_cache_is_replaced(self):
        self.put_raw_cache("structured", '{"wrong_field":1}', StructuredAnswer)
        self.api.models.generate_content.return_value = SimpleNamespace(text='{"answer":"recovered"}')
        self.assertEqual(self.client.generate("structured", StructuredAnswer).answer, "recovered")
        self.assertEqual(self.client.generate("structured", StructuredAnswer).answer, "recovered")
        self.api.models.generate_content.assert_called_once()

    def test_malformed_json_and_wrong_text_type_are_replaced(self):
        for raw in ["invalid JSON", '{"wrong_type":1}']:
            with self.subTest(raw=raw):
                self.put_raw_cache("text", raw)
                self.api.reset_mock()
                self.assertEqual(self.client.generate("text"), "Cache test successful")
                self.assertEqual(self.client.generate("text"), "Cache test successful")
                self.api.models.generate_content.assert_called_once()

    def test_cache_write_failure_preserves_generated_response(self):
        with patch("si.gemini_client.sqlite3.connect", side_effect=sqlite3.OperationalError("readonly")):
            self.assertEqual(self.client.generate("readonly"), "Cache test successful")
        self.api.models.generate_content.assert_called_once()

    def test_connections_are_closed(self):
        # Windows refuses to unlink a database while a connection is still open.
        self.client.generate("close test")
        self.client.generate("close test")
        self.db_path.unlink()
        self.assertFalse(self.db_path.exists())

    def test_private_requests_do_not_write_shared_cache(self):
        self.client.cache_writes = False
        self.client.generate("private question")
        with closing(sqlite3.connect(self.db_path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0], 0)
        self.api.models.generate_content.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
