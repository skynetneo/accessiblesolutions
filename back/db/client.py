"""
praxis/db/client.py

Database client singleton — uses supabase-py async client.

All middleware and tools should import `adb` for async operations.
The sync `db` is kept for compatibility with tools that run in
sync contexts (LangGraph @tool functions).

Usage:
    from db.client import adb, db

    # Async (preferred — middleware, processors, session_manager):
    result = await adb.table("learner_profiles").select("*").eq("learner_id", lid).execute()

    # Sync (only in @tool functions that can't be async):
    result = db.table("learner_profiles").select("*").eq("learner_id", lid).execute()
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from supabase import create_client, Client
from supabase._async.client import create_client as create_async_client, AsyncClient


logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


@lru_cache(maxsize=1)
def _get_sync_client() -> Client:
    return create_client(
        _require_env("SUPABASE_URL"),
        _require_env("SUPABASE_SERVICE_KEY"),
    )


_async_client: AsyncClient | None = None


async def get_async_client() -> AsyncClient:
    """Get or create the async Supabase client singleton."""
    global _async_client
    if _async_client is None:
        _async_client = await create_async_client(
            _require_env("SUPABASE_URL"),
            _require_env("SUPABASE_SERVICE_KEY"),
        )
    return _async_client


class _SyncProxy:
    """Lazy proxy for the sync Supabase client."""

    @property
    def client(self) -> Client:
        return _get_sync_client()

    def table(self, name: str):
        return self.client.table(name)

    def _query_table(self, name: str, curriculum_id: str = "ged"):
        """Query a table with curriculum scoping when available."""
        try:
            return self.table(name).select("*").eq("curriculum_id", curriculum_id)
        except Exception as exc:
            logger.warning("Falling back to unscoped query for table '%s': %s", name, exc)
            return self.table(name).select("*")

    def fetch_seeds(
        self,
        subject: str,
        skill_id: str,
        curriculum_id: str = "ged",
        chain_step: int | None = None,
        fluency_probe_only: bool = False,
        difficulty_min: float | None = None,
        difficulty_max: float | None = None,
        limit: int = 5,
    ) -> list[dict]:
        """Fetch seeds filtered by parameters."""
        def _build_query(include_curriculum: bool):
            query = self.table("seed_items").select("*").eq("subject", subject).eq("skill_id", skill_id)
            if include_curriculum:
                query = query.eq("curriculum_id", curriculum_id)
            if chain_step is not None:
                query = query.eq("chain_step", chain_step)
            if fluency_probe_only:
                query = query.eq("question_type", "multiple_choice")
            if difficulty_min is not None:
                query = query.gte("difficulty_b", difficulty_min)
            if difficulty_max is not None:
                query = query.lte("difficulty_b", difficulty_max)
            return query.limit(limit)

        try:
            return _build_query(include_curriculum=True).execute().data or []
        except Exception as exc:
            logger.warning("Falling back to seed query without curriculum filter: %s", exc)
            return _build_query(include_curriculum=False).execute().data or []

    def fetch_seeds_for_step_range(
        self,
        subject: str,
        skill_id: str,
        chain_id: str,
        step_numbers: list[int],
        curriculum_id: str = "ged",
    ) -> dict[int, list[dict]]:
        """Fetch seeds for multiple chain steps, grouped by step."""
        def _build_query(include_curriculum: bool):
            query = self.table("seed_items").select("*").eq("subject", subject).eq("skill_id", skill_id)
            if include_curriculum:
                query = query.eq("curriculum_id", curriculum_id)
            if step_numbers:
                query = query.in_("chain_step", step_numbers)
            return query

        try:
            records = _build_query(include_curriculum=True).execute().data or []
        except Exception as exc:
            logger.warning("Falling back to step-range seed query without curriculum filter: %s", exc)
            records = _build_query(include_curriculum=False).execute().data or []
        
        result = {}
        for r in records:
            step = r.get("chain_step")
            if step not in result:
                result[step] = []
            result[step].append(r)
        return result

    def fetch_all_chains(
        self,
        subject: str | None = None,
        curriculum_id: str = "ged",
    ) -> list[dict]:
        try:
            query = self._query_table("skill_chains", curriculum_id=curriculum_id)
            if subject:
                query = query.eq("subject", subject)
            return query.execute().data or []
        except Exception as exc:
            logger.warning("Falling back to unscoped chain query: %s", exc)
            query = self.table("skill_chains").select("*")
            if subject:
                query = query.eq("subject", subject)
            return query.execute().data or []

    def fetch_chain(
        self,
        skill_id: str,
        curriculum_id: str = "ged",
    ) -> dict | None:
        try:
            query = self._query_table("skill_chains", curriculum_id=curriculum_id).eq("skill_id", skill_id)
            return query.maybe_single().execute().data
        except Exception as exc:
            logger.warning("Falling back to unscoped chain lookup for '%s': %s", skill_id, exc)
            return self.table("skill_chains").select("*").eq("skill_id", skill_id).maybe_single().execute().data

    def fetch_cached_items(
        self,
        skill_id: str,
        item_role: str = "target",
        theme: str | None = None,
        freeform_interest: str | None = None,
        chain_step: int | None = None,
        modality_id: str | None = None,
        min_validation_score: float = 0.75,
        limit: int = 8,
        curriculum_id: str = "ged",
    ) -> list[dict]:
        try:
            query = self._query_table("content_cache", curriculum_id=curriculum_id).eq("skill_id", skill_id)
            if chain_step is not None:
                query = query.eq("chain_step", chain_step)
            rows = query.limit(max(limit * 4, 16)).execute().data or []
        except Exception as exc:
            logger.warning("Falling back to unscoped content cache query for '%s': %s", skill_id, exc)
            query = self.table("content_cache").select("*").eq("skill_id", skill_id)
            if chain_step is not None:
                query = query.eq("chain_step", chain_step)
            rows = query.limit(max(limit * 4, 16)).execute().data or []
        filtered: list[dict] = []
        for row in rows:
            row_item_role = row.get("item_role")
            if row_item_role and row_item_role != item_role:
                continue

            if not (row.get("validated") or row.get("status") == "validated"):
                continue

            score = row.get("validation_score", 1.0)
            if score < min_validation_score:
                continue

            row_theme = row.get("theme_applied", row.get("theme"))
            if theme and row_theme != theme:
                continue

            row_interest = row.get("freeform_interest")
            if freeform_interest and row_interest != freeform_interest:
                continue

            row_modality = row.get("modality_id")
            if modality_id and row_modality != modality_id:
                continue

            normalized = dict(row)
            if "theme_applied" not in normalized and row_theme is not None:
                normalized["theme_applied"] = row_theme
            filtered.append(normalized)

        filtered.sort(key=lambda row: row.get("validation_score", 0.0), reverse=True)
        return filtered[:limit]

    def cache_miss(
        self,
        skill_id: str,
        item_role: str = "target",
        theme: str | None = None,
        freeform_interest: str | None = None,
        chain_step: int | None = None,
        modality_id: str | None = None,
        min_validation_score: float = 0.75,
        curriculum_id: str = "ged",
        min_items: int = 3,
    ) -> bool:
        items = self.fetch_cached_items(
            skill_id=skill_id,
            item_role=item_role,
            theme=theme,
            freeform_interest=freeform_interest,
            chain_step=chain_step,
            modality_id=modality_id,
            min_validation_score=min_validation_score,
            limit=min_items,
            curriculum_id=curriculum_id,
        )
        return len(items) < min_items

    def write_generated_item(self, row: dict) -> list[dict]:
        payload = dict(row)
        payload.setdefault("validated", payload.get("status") == "validated")
        payload.setdefault("curriculum_id", "ged")
        try:
            return self.table("content_cache").upsert(payload).execute().data or []
        except Exception as exc:
            logger.warning("Retrying generated-item upsert without curriculum_id: %s", exc)
            payload.pop("curriculum_id", None)
            return self.table("content_cache").upsert(payload).execute().data or []

    def fetch_learning_style_tips(self, style_id: str) -> list[dict]:
        """Load optional learning-style guidance if the table exists."""
        for table_name in ("learning_style_guidance", "learning_styles"):
            try:
                result = self.table(table_name).select("*").eq("style_id", style_id).execute()
                return result.data or []
            except Exception as exc:
                logger.warning("Learning-style table '%s' unavailable: %s", table_name, exc)
                continue
        return []


class _AsyncProxy:
    """Lazy proxy for the async Supabase client.

    Usage:
        result = await adb.table("x").select("*").execute()

    The table() call returns the async query builder which is
    natively awaitable — no asyncio.to_thread needed.
    """

    async def table(self, name: str):
        client = await get_async_client()
        return client.table(name)

    async def rpc(self, fn: str, params: dict | None = None):
        client = await get_async_client()
        return await client.rpc(fn, params or {}).execute()


# Public singletons
db = _SyncProxy()     # sync — for @tool functions
adb = _AsyncProxy()   # async — for middleware, processors, session_manager
