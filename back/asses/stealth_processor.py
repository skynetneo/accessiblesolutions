"""
praxis/assessment/stealth_processor.py

Aggregates raw stealth observations into actionable profile updates.

The middleware stack (StealthAssessmentMiddleware, EmploymentStructuralMiddleware)
collects raw behavioral signals every model call. This processor runs periodically
(end of session or on-demand) to analyze accumulated observations and update the
learner's profile, competency scores, and coaching preferences.

It does NOT affect mastery determination. Ever.

Usage:
    from assessment.stealth_processor import StealthProcessor

    processor = StealthProcessor()
    updates = await processor.process_session(learner_id, session_id)
    # updates = {
    #     "modality_weights": {"visual": 0.6, "reading": 0.3, "kinesthetic": 0.1},
    #     "coaching_tone": "encouraging",
    #     "competency_updates": [{"competency": "communication", "delta": +0.05}],
    #     "detected_misconceptions": ["fraction_ordering_by_denominator"],
    #     "fatigue_detected": False,
    # }
"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Optional

from db.client import db


class StealthProcessor:
    """Processes raw stealth observations into profile updates.

    Observation types (from stealth_observations table):
        response_latency   → session pacing, fatigue detection (NEVER mastery)
        error_pattern       → misconception clustering
        help_seeking        → coaching tone tuning
        engagement          → modality preference updates
        competency_signal   → employment competency score updates
        misconception       → specific misconception tagging
        modality_preference → explicit modality signals
        session_fatigue     → fatigue/disengagement detection
    """

    # Fatigue: if avg response time increases >40% in last 5 items vs first 5
    FATIGUE_RATIO_THRESHOLD = 1.4
    # Competency: rolling average weight for new signals
    COMPETENCY_RECENCY_WEIGHT = 0.3

    async def process_session(
        self,
        learner_id: str,
        session_id: str,
    ) -> dict:
        """Process all observations from a session and return profile updates.

        Args:
            learner_id: The learner
            session_id: The session to process

        Returns:
            Dict of profile updates to apply
        """
        observations = await self._load_observations(learner_id, session_id)
        if not observations:
            return {}

        results = {}

        # 1. Fatigue detection
        results["fatigue_detected"] = self._detect_fatigue(observations)

        # 2. Error pattern → misconception clustering
        misconceptions = self._cluster_errors(observations)
        if misconceptions:
            results["detected_misconceptions"] = misconceptions

        # 3. Help-seeking → coaching tone
        tone_suggestion = self._analyze_help_seeking(observations)
        if tone_suggestion:
            results["coaching_tone"] = tone_suggestion

        # 4. Competency signal aggregation
        competency_updates = self._aggregate_competencies(observations)
        if competency_updates:
            results["competency_updates"] = competency_updates
            await self._persist_competency_updates(learner_id, competency_updates)

        # 5. Modality preference
        modality = self._infer_modality_preference(observations)
        if modality:
            results["modality_weights"] = modality

        # 6. Apply profile updates
        profile_patch = {}
        if "coaching_tone" in results:
            profile_patch["coaching_tone"] = results["coaching_tone"]
        if "modality_weights" in results:
            profile_patch["modality_weights"] = results["modality_weights"]
        if profile_patch:
            await self._update_profile(learner_id, profile_patch)

        return results

    # ── Detection methods ──────────────────────────────────────

    def _detect_fatigue(self, observations: list[dict]) -> bool:
        """Detect session fatigue from response latency trends."""
        latencies = [
            o["data"].get("response_latency_ms", 0)
            for o in observations
            if o.get("observation_type") == "response_latency"
            and o.get("data", {}).get("response_latency_ms")
        ]
        if len(latencies) < 10:
            return False

        first_half = latencies[:len(latencies) // 2]
        second_half = latencies[len(latencies) // 2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_first == 0:
            return False
        return (avg_second / avg_first) > self.FATIGUE_RATIO_THRESHOLD

    def _cluster_errors(self, observations: list[dict]) -> list[str]:
        """Identify recurring error patterns as potential misconceptions."""
        error_types = Counter()
        for o in observations:
            if o.get("observation_type") == "error_pattern":
                pattern = o.get("data", {}).get("pattern", "")
                if pattern:
                    error_types[pattern] += 1

        # A pattern appearing 2+ times in one session is a likely misconception
        return [pattern for pattern, count in error_types.items() if count >= 2]

    def _analyze_help_seeking(self, observations: list[dict]) -> Optional[str]:
        """Infer ideal coaching tone from help-seeking behavior."""
        help_count = 0
        total_responses = 0

        for o in observations:
            data = o.get("data", {})
            if data.get("help_requested"):
                help_count += 1
            if o.get("observation_type") in ("response_latency", "engagement"):
                total_responses += 1

        if total_responses < 5:
            return None

        help_ratio = help_count / max(total_responses, 1)

        if help_ratio > 0.4:
            return "supportive"       # frequently asks for help → more warmth
        elif help_ratio < 0.1:
            return "direct"           # rarely asks → prefers efficiency
        return None                   # no strong signal → keep current

    def _aggregate_competencies(self, observations: list[dict]) -> list[dict]:
        """Aggregate competency signals into score deltas."""
        signals: dict[str, list[float]] = {}

        for o in observations:
            if o.get("observation_type") == "competency_signal":
                data = o.get("data", {})
                comp = data.get("competency", "")
                strength = data.get("strength", 0.5)
                if comp:
                    signals.setdefault(comp, []).append(strength)

        updates = []
        for comp, strengths in signals.items():
            avg_signal = sum(strengths) / len(strengths)
            # Delta is weighted toward the signal, blended with current
            delta = (avg_signal - 0.5) * self.COMPETENCY_RECENCY_WEIGHT
            updates.append({
                "competency": comp,
                "avg_signal": round(avg_signal, 3),
                "delta": round(delta, 4),
                "observations": len(strengths),
            })

        return updates

    def _infer_modality_preference(self, observations: list[dict]) -> Optional[dict]:
        """Infer modality preferences from engagement signals."""
        modality_engagement: dict[str, list[float]] = {}

        for o in observations:
            if o.get("observation_type") == "modality_preference":
                data = o.get("data", {})
                modality = data.get("modality", "")
                engagement = data.get("engagement_score", 0.5)
                if modality:
                    modality_engagement.setdefault(modality, []).append(engagement)

        if not modality_engagement:
            return None

        weights = {}
        total = 0.0
        for mod, scores in modality_engagement.items():
            avg = sum(scores) / len(scores)
            weights[mod] = avg
            total += avg

        # Normalize to sum to 1.0
        if total > 0:
            weights = {k: round(v / total, 3) for k, v in weights.items()}

        return weights if weights else None

    # ── Persistence helpers ────────────────────────────────────

    async def _load_observations(self, learner_id: str, session_id: str) -> list[dict]:
        result = await asyncio.to_thread(
            lambda: db.client.table("stealth_observations")
            .select("*")
            .eq("learner_id", learner_id)
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    async def _persist_competency_updates(
        self, learner_id: str, updates: list[dict]
    ):
        """Apply competency deltas to the learner_competencies table."""
        for u in updates:
            comp = u["competency"]
            delta = u["delta"]

            # Load current
            current = await asyncio.to_thread(
                lambda c=comp: db.client.table("learner_competencies")
                .select("*")
                .eq("learner_id", learner_id)
                .eq("competency", c)
                .maybe_single()
                .execute()
            )

            if current.data:
                new_strength = max(0.0, min(1.0, current.data["strength"] + delta))
                await asyncio.to_thread(
                    lambda c=comp, s=new_strength: db.client.table("learner_competencies")
                    .update({
                        "strength": s,
                        "demonstrated_count": current.data["demonstrated_count"] + 1,
                    })
                    .eq("learner_id", learner_id)
                    .eq("competency", c)
                    .execute()
                )
            else:
                await asyncio.to_thread(
                    lambda c=comp, d=delta: db.client.table("learner_competencies")
                    .insert({
                        "learner_id": learner_id,
                        "competency": c,
                        "strength": max(0.0, min(1.0, 0.5 + d)),
                        "demonstrated_count": 1,
                        "prompted_count": 0,
                    })
                    .execute()
                )

    async def _update_profile(self, learner_id: str, patch: dict):
        await asyncio.to_thread(
            lambda: db.client.table("learner_profiles")
            .update(patch)
            .eq("learner_id", learner_id)
            .execute()
        )
