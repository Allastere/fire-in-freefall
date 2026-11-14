import os
import json
import time
import hashlib
import logging
import sqlite3
from contextlib import closing

from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
from pydantic import BaseModel, ValidationError

from config.settings import DB_PATH, GEMINI_MODEL
from si.prompts import SYSTEM_PROMPT


load_dotenv()

logger = logging.getLogger(__name__)

class GeminiClient:

    def __init__(
        self,
        api_key=None,
        model_name=None,
        db_path=DB_PATH
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        self.model_name = (
            model_name
            or os.getenv("GEMINI_MODEL")
            or GEMINI_MODEL
        )

        self.db_path = Path(db_path)
        self.client = None

    def _get_client(self):
        if self.client is None:
            if not self.api_key:
                raise RuntimeError("GEMINI_API_KEY is missing")

            self.client = genai.Client(
                api_key=self.api_key
            )

        return self.client

    def _generate_hash(self, prompt, response_schema=None):

        payload = {
            "model": self.model_name,
            "system_prompt": SYSTEM_PROMPT,
            "user_prompt": prompt,
            "response_schema": (
                response_schema.model_json_schema()
                if response_schema else None
            )
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def _get_cached_response(self, prompt_hash):

        if not self.db_path.exists():
            return None

        try:
            with closing(sqlite3.connect(
                self.db_path.resolve().as_uri() + "?mode=ro",
                uri=True
            )) as conn:

                result = conn.execute(
                    """
                    SELECT response_json
                    FROM llm_cache
                    WHERE prompt_hash = ?
                    """,
                    (prompt_hash,)
                ).fetchone()

                if result:
                    return json.loads(result[0])

        except (sqlite3.OperationalError, ValueError) as exc:
            logger.warning("Cache read failed: %s", exc)

        return None

    def _save_to_cache(self, prompt_hash, response):

        if not self.db_path.exists():
            return

        try:
            with closing(sqlite3.connect(
                self.db_path.resolve().as_uri() + "?mode=rw",
                uri=True
            )) as conn, conn:

                conn.execute(
                    """
                    INSERT OR REPLACE INTO llm_cache (
                        prompt_hash,
                        model_name,
                        response_json,
                        created_at
                    )
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        prompt_hash,
                        self.model_name,
                        json.dumps(
                            response,
                            ensure_ascii=False
                        )
                    )
                )

        except sqlite3.OperationalError as exc:
            logger.warning("Cache write failed: %s", exc)

    def generate(
        self,
        prompt: str,
        response_schema: type[BaseModel] | None = None
    ):

        prompt_hash = self._generate_hash(
            prompt,
            response_schema
        )

        cached = self._get_cached_response(prompt_hash)

        if cached is not None:
            if response_schema:
                try:
                    parsed = response_schema.model_validate(cached)
                except ValidationError:
                    logger.warning("Invalid structured cache entry; treating as a miss")
                else:
                    logger.info("Cache HIT")
                    return parsed
            elif isinstance(cached, str):
                logger.info("Cache HIT")
                return cached
            else:
                logger.warning("Invalid text cache entry; treating as a miss")

        logger.info("Cache MISS")

        config = {
            "system_instruction": SYSTEM_PROMPT
        }

        if response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema

        client = self._get_client()

        for attempt in range(3):

            try:
                result = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        **config
                    )
                )

                if not result.text:
                    raise RuntimeError(
                        "Gemini returned an empty response"
                    )

                if response_schema:
                    parsed = response_schema.model_validate_json(
                        result.text
                    )

                    self._save_to_cache(
                        prompt_hash,
                        parsed.model_dump(mode="json")
                    )

                    return parsed

                self._save_to_cache(
                    prompt_hash,
                    result.text
                )

                return result.text

            except errors.ServerError as exc:

                if exc.code not in (500, 502, 503, 504):
                    raise

                if attempt == 2:
                    raise

                time.sleep(2 ** attempt)
