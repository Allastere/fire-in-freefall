"""Reuse existing SQLite cache without changing the research schema; session fallback on read-only disks."""
from si.gemini_client import GeminiClient


class AssessmentCache(dict):
    def __init__(self, db_path):
        super().__init__()
        self.storage = GeminiClient(db_path=db_path, model_name="structured-scientific-assessment-v1")

    def __contains__(self, key):
        if super().__contains__(key): return True
        value = self.storage._get_cached_response("assessment:" + key)
        if isinstance(value, dict) and value.get("cache_format") == 1 and isinstance(value.get("assessment"),dict) and all(k in value["assessment"] for k in ("route","answer","results","origin_route")):
            super().__setitem__(key, value["assessment"])
            return True
        return False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.storage._save_to_cache("assessment:" + key, {"cache_format":1, "assessment":value})
