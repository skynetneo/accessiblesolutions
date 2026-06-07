"""
praxis/services/narration.py

NarrationService — TTS generation with tiered caching.

Responsibilities:
  1. Chunk coaching text into TTS-safe segments (~1-3 sentences)
  2. Hash chunks for cache lookup
  3. Generate audio via Qwen3-TTS (male/female voices)
  4. Upload to Supabase Storage
  5. Persist metadata + word timings to narration_cache
  6. Serve cached audio on subsequent requests
  7. Queue batch pre-generation for curriculum publishes

Architecture:
  - Tier 1: seed narrations (permanent, pre-generated)
  - Tier 2: themed variants (LRU eviction)
  - Tier 3: dynamic coaching responses (short TTL)

  Cache key = sha256(text + voice + speed + scaffold_level)

Usage:
    from services.narration import NarrationService

    svc = NarrationService()

    # Single chunk (real-time, cache-through)
    result = await svc.get_or_generate(
        text="Let's look at this fraction problem.",
        voice="female_teaching",
        skill_id="math.fractions.common_denominator",
    )
    # result.audio_url, result.duration_ms, result.word_timings

    # Full narration plan (multiple chunks)
    results = await svc.narrate_plan(plan, skill_id="...")
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from db.client import get_async_client


# ──────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────

@dataclass
class NarrationChunk:
    """A single chunk of text to narrate."""
    text: str
    role: str = "explanation"          # setup, explanation, question, hint, encouragement
    voice: str = "female_teaching"     # female_teaching, male_workplace
    speed: float = 1.0
    highlight: Optional[str] = None    # key term to highlight during this chunk
    pause_after_ms: int = 0            # silence after chunk (for questions)


@dataclass
class NarrationResult:
    """Result of generating/fetching a single narration chunk."""
    content_hash: str
    audio_url: str
    text: str
    voice: str
    duration_ms: int
    word_timings: list[dict] = field(default_factory=list)  # [{word, start_ms, end_ms}]
    cached: bool = False


@dataclass
class NarrationPlan:
    """A full narration plan — ordered chunks with metadata."""
    chunks: list[NarrationChunk]
    skill_id: str = ""
    chain_step: int = 0
    scaffold_level: int = 3
    theme: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

STORAGE_BUCKET = os.environ.get("NARRATION_BUCKET", "narration-audio")

# Qwen3-TTS config
TTS_ENDPOINT = os.environ.get("TTS_ENDPOINT", "http://localhost:9880/tts")
MAX_CHUNK_CHARS = int(os.environ.get("TTS_MAX_CHUNK_CHARS", "300"))

# Word timing estimation (when TTS doesn't provide alignment)
WORDS_PER_MINUTE = 145  # deliberate teaching pace
MS_PER_WORD = 60_000 / WORDS_PER_MINUTE

VOICES = {
    "female_teaching": {"ref_audio": "voices/female_teaching.wav", "ref_text": ""},
    "male_workplace": {"ref_audio": "voices/male_workplace.wav", "ref_text": ""},
}


# ──────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────

class NarrationService:
    """TTS generation with tiered Supabase cache."""

    # ── Public API ────────────────────────────────────────────

    async def get_or_generate(
        self,
        text: str,
        voice: str = "female_teaching",
        speed: float = 1.0,
        scaffold_level: int = 3,
        skill_id: str = "",
        chain_step: int = 0,
        theme: Optional[str] = None,
        tier: int = 2,
    ) -> NarrationResult:
        """Get cached audio or generate + cache a new one.

        This is the main entry point for single chunks.
        Returns immediately on cache hit; generates on miss.
        """
        content_hash = self._hash(text, voice, speed, scaffold_level)

        # 1. Check cache
        cached = await self._cache_lookup(content_hash)
        if cached:
            await self._touch(content_hash)
            return cached

        # 2. Generate via TTS
        audio_bytes, raw_timings = await self._synthesize(text, voice, speed)

        # 3. Estimate word timings if TTS didn't provide them
        word_timings = raw_timings or self._estimate_timings(text, speed)

        # 4. Compute duration
        if word_timings:
            duration_ms = max(t.get("end_ms", 0) for t in word_timings)
        else:
            duration_ms = int(len(text.split()) * MS_PER_WORD / speed)

        # 5. Upload to Supabase Storage
        audio_url = await self._upload(content_hash, audio_bytes)

        # 6. Write cache row
        result = NarrationResult(
            content_hash=content_hash,
            audio_url=audio_url,
            text=text,
            voice=voice,
            duration_ms=duration_ms,
            word_timings=word_timings,
            cached=False,
        )
        await self._cache_write(result, scaffold_level, skill_id, chain_step, theme, tier)
        return result

    async def narrate_plan(
        self,
        plan: NarrationPlan,
    ) -> list[NarrationResult]:
        """Generate/fetch audio for an entire narration plan.

        Checks cache for all chunks first (batch), then generates
        only the misses. Returns results in plan order.
        """
        results: list[NarrationResult | None] = [None] * len(plan.chunks)
        to_generate: list[tuple[int, NarrationChunk, str]] = []

        # Batch cache check
        for i, chunk in enumerate(plan.chunks):
            h = self._hash(chunk.text, chunk.voice, chunk.speed, plan.scaffold_level)
            cached = await self._cache_lookup(h)
            if cached:
                await self._touch(h)
                results[i] = cached
            else:
                to_generate.append((i, chunk, h))

        # Generate misses
        for idx, chunk, h in to_generate:
            tier = 1 if plan.theme is None else 2
            result = await self.get_or_generate(
                text=chunk.text,
                voice=chunk.voice,
                speed=chunk.speed,
                scaffold_level=plan.scaffold_level,
                skill_id=plan.skill_id,
                chain_step=plan.chain_step,
                theme=plan.theme,
                tier=tier,
            )
            results[idx] = result

        return [r for r in results if r is not None]

    async def queue_batch(
        self,
        chunks: list[NarrationChunk],
        skill_id: str = "",
        chain_step: int = 0,
        scaffold_level: int = 3,
        tier: int = 1,
        priority: int = 5,
    ) -> int:
        """Queue chunks for batch pre-generation.

        Used by the curriculum webhook to pre-generate tier 1 narrations.
        Returns the number of items queued (skips already-cached).
        """
        client = await get_async_client()
        queued = 0

        for chunk in chunks:
            h = self._hash(chunk.text, chunk.voice, chunk.speed, scaffold_level)
            cached = await self._cache_lookup(h)
            if cached:
                continue

            await (
                client.table("narration_generation_queue")
                .insert({
                    "text": chunk.text,
                    "voice": chunk.voice,
                    "speed": chunk.speed,
                    "scaffold_level": scaffold_level,
                    "skill_id": skill_id,
                    "chain_step": chain_step,
                    "tier": tier,
                    "priority": priority,
                    "status": "pending",
                })
                .execute()
            )
            queued += 1

        return queued

    # ── Text chunking ─────────────────────────────────────────

    @staticmethod
    def chunk_text(
        text: str,
        max_chars: int = MAX_CHUNK_CHARS,
        role: str = "explanation",
        voice: str = "female_teaching",
    ) -> list[NarrationChunk]:
        """Split text into TTS-safe chunks on sentence boundaries.

        Respects max_chars limit for Qwen3-TTS stability.
        Never splits mid-sentence.
        """
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        chunks: list[NarrationChunk] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If single sentence exceeds max, split on clause boundaries
            if len(sentence) > max_chars:
                if current:
                    chunks.append(NarrationChunk(text=current.strip(), role=role, voice=voice))
                    current = ""
                sub_chunks = NarrationService._split_long_sentence(sentence, max_chars)
                for sc in sub_chunks:
                    chunks.append(NarrationChunk(text=sc.strip(), role=role, voice=voice))
                continue

            # Would adding this sentence exceed the limit?
            test = f"{current} {sentence}".strip() if current else sentence
            if len(test) > max_chars:
                # Flush current buffer
                if current:
                    chunks.append(NarrationChunk(text=current.strip(), role=role, voice=voice))
                current = sentence
            else:
                current = test

        if current.strip():
            chunks.append(NarrationChunk(text=current.strip(), role=role, voice=voice))

        return chunks

    @staticmethod
    def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
        """Split an oversized sentence on clause boundaries (, ; — :)."""
        parts = re.split(r'(?<=[,;:—–])\s+', sentence)
        chunks: list[str] = []
        current = ""
        for part in parts:
            test = f"{current} {part}".strip() if current else part
            if len(test) > max_chars and current:
                chunks.append(current.strip())
                current = part
            else:
                current = test
        if current.strip():
            chunks.append(current.strip())
        return chunks

    # ── Hashing ───────────────────────────────────────────────

    @staticmethod
    def _hash(text: str, voice: str, speed: float, scaffold_level: int) -> str:
        """Deterministic content hash for cache key."""
        raw = f"{text}|{voice}|{speed:.2f}|{scaffold_level}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ── TTS synthesis ─────────────────────────────────────────

    async def _synthesize(
        self,
        text: str,
        voice: str,
        speed: float,
    ) -> tuple[bytes, list[dict] | None]:
        """Call Qwen3-TTS and return (audio_bytes, word_timings_or_none).

        The TTS endpoint is expected to accept:
            POST /tts
            {
                "text": "...",
                "ref_audio": "path/to/ref.wav",
                "speed": 1.0
            }
        And return audio/wav bytes.

        If the endpoint also returns word-level alignment (via a
        separate header or JSON wrapper), parse those into timings.
        """
        import httpx

        voice_config = VOICES.get(voice, VOICES["female_teaching"])

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                TTS_ENDPOINT,
                json={
                    "text": text,
                    "ref_audio": voice_config["ref_audio"],
                    "ref_text": voice_config.get("ref_text", ""),
                    "speed": speed,
                },
            )
            response.raise_for_status()

        # Check for word timings in response headers
        word_timings: list[dict] | None = None
        timings_header = response.headers.get("X-Word-Timings")
        if timings_header:
            try:
                word_timings = json.loads(timings_header)
            except json.JSONDecodeError:
                pass

        return response.content, word_timings

    # ── Word timing estimation ────────────────────────────────

    @staticmethod
    def _estimate_timings(text: str, speed: float = 1.0) -> list[dict]:
        """Estimate per-word timestamps from text and speaking rate.

        Good enough for highlight sync when TTS doesn't provide
        forced alignment. At ~145 WPM teaching pace, each word
        averages ~414ms. We scale proportionally by character
        count for better accuracy on long vs short words.
        """
        words = text.split()
        if not words:
            return []

        total_chars = sum(len(w) for w in words)
        if total_chars == 0:
            return []

        total_duration_ms = len(words) * MS_PER_WORD / speed
        timings: list[dict] = []
        cursor_ms = 0.0

        for word in words:
            # Duration proportional to character count
            fraction = len(word) / total_chars
            word_duration = total_duration_ms * fraction
            timings.append({
                "word": word,
                "start_ms": round(cursor_ms),
                "end_ms": round(cursor_ms + word_duration),
            })
            cursor_ms += word_duration

        return timings

    # ── Supabase Storage ──────────────────────────────────────

    async def _upload(self, content_hash: str, audio_bytes: bytes) -> str:
        """Upload audio to Supabase Storage. Returns the public URL."""
        client = await get_async_client()
        path = f"{content_hash}.wav"

        # Upload (upsert: overwrite if exists)
        await client.storage.from_(STORAGE_BUCKET).upload(
            path=path,
            file=audio_bytes,
            file_options={"content-type": "audio/wav", "upsert": "true"},
        )

        # Get public URL
        url = client.storage.from_(STORAGE_BUCKET).get_public_url(path)
        return url

    # ── Cache operations ──────────────────────────────────────

    async def _cache_lookup(self, content_hash: str) -> NarrationResult | None:
        """Check narration_cache for an existing entry."""
        client = await get_async_client()
        result = await (
            client.table("narration_cache")
            .select("*")
            .eq("content_hash", content_hash)
            .maybe_single()
            .execute()
        )

        row = result.data
        if not row:
            return None

        return NarrationResult(
            content_hash=row["content_hash"],
            audio_url=row["audio_url"],
            text=row["text"],
            voice=row["voice"],
            duration_ms=row.get("duration_ms", 0),
            word_timings=row.get("word_timings") or [],
            cached=True,
        )

    async def _cache_write(
        self,
        result: NarrationResult,
        scaffold_level: int,
        skill_id: str,
        chain_step: int,
        theme: Optional[str],
        tier: int,
    ) -> None:
        """Write a narration result to the cache."""
        client = await get_async_client()
        await (
            client.table("narration_cache")
            .upsert({
                "content_hash": result.content_hash,
                "audio_url": result.audio_url,
                "text": result.text,
                "voice": result.voice,
                "speed": 1.0,
                "scaffold_level": scaffold_level,
                "duration_ms": result.duration_ms,
                "word_timings": result.word_timings,
                "tier": tier,
                "skill_id": skill_id,
                "chain_step": chain_step,
                "theme": theme,
                "use_count": 1,
                "last_used_at": "now()",
            })
            .execute()
        )

    async def _touch(self, content_hash: str) -> None:
        """Bump use stats on cache hit."""
        client = await get_async_client()
        await client.rpc("touch_narration", {"p_hash": content_hash}).execute()

    # ── Cache maintenance ─────────────────────────────────────

    async def evict_stale(
        self,
        tier: int = 2,
        min_use_count: int = 5,
        max_age_days: int = 30,
    ) -> int:
        """Evict stale tier 2 entries (LRU policy).

        Deletes rows where:
          - tier matches
          - use_count < min_use_count
          - last_used_at older than max_age_days

        Also deletes the audio files from Storage.
        Returns number of evicted entries.
        """
        client = await get_async_client()
        cutoff = f"now() - interval '{max_age_days} days'"

        # Find candidates
        result = await (
            client.table("narration_cache")
            .select("content_hash")
            .eq("tier", tier)
            .lt("use_count", min_use_count)
            .lt("last_used_at", cutoff)
            .execute()
        )

        rows = result.data or []
        if not rows:
            return 0

        hashes = [r["content_hash"] for r in rows]

        # Delete audio files from storage
        paths = [f"{h}.wav" for h in hashes]
        try:
            client.storage.from_(STORAGE_BUCKET).remove(paths)
        except Exception:
            pass  # Non-fatal; files may already be gone

        # Delete cache rows
        if hashes:
            await (
                client.table("narration_cache")
                .delete()
                .in_("content_hash", hashes)
                .execute()
    	    )

        return len(hashes)
