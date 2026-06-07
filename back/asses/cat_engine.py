"""
praxis/assessment/cat_engine.py

Computerized Adaptive Testing with 2-Parameter Logistic IRT.

Pure math — no LLM calls, no middleware, no Supabase writes.
The caller (assessment team agent) handles item retrieval and result persistence.

Usage:
    from assessment.cat_engine import CATEngine, CATState

    engine = CATEngine()
    state = engine.new_session(subject="math")

    # For each item:
    item = engine.select_item(state, item_bank)
    # ... present item, get response ...
    state = engine.record_response(state, item, correct=True)

    if engine.should_stop(state):
        results = engine.get_results(state)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CATItem:
    """Minimal item representation for IRT calculations."""
    item_id: str
    skill_id: str
    difficulty_b: float        # IRT difficulty (-3.0 to 3.0)
    discrimination_a: float    # IRT discrimination (0.5 to 2.5)
    subject: str = ""
    chain_step: int = 0


@dataclass
class CATState:
    """Mutable state for one CAT session."""
    subject: str
    theta: float = 0.0                     # current ability estimate
    se: float = 3.0                        # standard error of theta
    responses: list[dict] = field(default_factory=list)
    administered_ids: set[str] = field(default_factory=set)


class CATEngine:
    """2-Parameter Logistic IRT adaptive testing engine.

    P(correct | theta, a, b) = 1 / (1 + exp(-a * (theta - b)))

    Item selection: maximum Fisher information at current theta.
    Theta estimation: Newton-Raphson MLE after each response.
    Stopping: SE(theta) < SE_THRESHOLD or MAX_ITEMS reached.

    Response latency is captured separately and NEVER affects theta.
    """

    SE_THRESHOLD = 0.30
    MAX_ITEMS = 15
    THETA_MIN = -3.5
    THETA_MAX = 3.5

    # ── Core IRT math ──────────────────────────────────────────

    @staticmethod
    def probability(theta: float, a: float, b: float) -> float:
        """P(correct) under the 2PL model."""
        z = a * (theta - b)
        z = max(-20, min(20, z))  # prevent overflow
        return 1.0 / (1.0 + math.exp(-z))

    @staticmethod
    def information(theta: float, a: float, b: float) -> float:
        """Fisher information of an item at a given theta."""
        p = CATEngine.probability(theta, a, b)
        q = 1.0 - p
        return (a ** 2) * p * q

    # ── Session lifecycle ──────────────────────────────────────

    def new_session(self, subject: str, prior_theta: float = 0.0) -> CATState:
        return CATState(subject=subject, theta=prior_theta)

    def select_item(self, state: CATState, item_bank: list[CATItem]) -> CATItem | None:
        """Select the item with maximum information at current theta.
        Skips already-administered items. Applies content balancing
        by preferring items from under-represented skills."""
        candidates = [
            it for it in item_bank
            if it.item_id not in state.administered_ids
            and (not state.subject or it.subject == state.subject)
        ]
        if not candidates:
            return None

        # Score by information, with slight skill-diversity bonus
        seen_skills = {r["skill_id"] for r in state.responses}
        best, best_score = None, -1.0
        for it in candidates:
            info = self.information(state.theta, it.discrimination_a, it.difficulty_b)
            diversity_bonus = 0.05 if it.skill_id not in seen_skills else 0.0
            score = info + diversity_bonus
            if score > best_score:
                best, best_score = it, score
        return best

    def record_response(self, state: CATState, item: CATItem, correct: bool) -> CATState:
        """Record a response and update theta via Newton-Raphson MLE."""
        state.responses.append({
            "item_id": item.item_id,
            "skill_id": item.skill_id,
            "difficulty_b": item.difficulty_b,
            "discrimination_a": item.discrimination_a,
            "correct": correct,
        })
        state.administered_ids.add(item.item_id)
        state.theta = self._estimate_theta(state.responses)
        state.se = self._estimate_se(state.theta, state.responses)
        return state

    def should_stop(self, state: CATState) -> bool:
        return state.se < self.SE_THRESHOLD or len(state.responses) >= self.MAX_ITEMS

    def get_results(self, state: CATState) -> dict:
        """Final placement results."""
        total = len(state.responses)
        correct = sum(1 for r in state.responses if r["correct"])
        skill_thetas = self._per_skill_estimates(state)
        return {
            "theta": round(state.theta, 3),
            "se": round(state.se, 3),
            "items_administered": total,
            "accuracy": round(correct / total, 3) if total else 0.0,
            "subject": state.subject,
            "skill_estimates": skill_thetas,
        }

    # ── MLE estimation (Newton-Raphson) ────────────────────────

    def _estimate_theta(self, responses: list[dict], max_iter: int = 25) -> float:
        """Maximum likelihood estimate of theta via Newton-Raphson."""
        if not responses:
            return 0.0
        # Handle perfect/zero scores with Bayesian prior nudge
        n_correct = sum(1 for r in responses if r["correct"])
        if n_correct == 0:
            return self.THETA_MIN + 1.0
        if n_correct == len(responses):
            return self.THETA_MAX - 1.0

        theta = 0.0
        for _ in range(max_iter):
            numerator = 0.0
            denominator = 0.0
            for r in responses:
                a, b = r["discrimination_a"], r["difficulty_b"]
                p = self.probability(theta, a, b)
                u = 1.0 if r["correct"] else 0.0
                numerator += a * (u - p)
                denominator += (a ** 2) * p * (1.0 - p)

            if abs(denominator) < 1e-10:
                break
            delta = numerator / denominator
            theta += delta
            theta = max(self.THETA_MIN, min(self.THETA_MAX, theta))
            if abs(delta) < 0.001:
                break
        return round(theta, 4)

    def _estimate_se(self, theta: float, responses: list[dict]) -> float:
        """Standard error = 1 / sqrt(total information)."""
        total_info = sum(
            self.information(theta, r["discrimination_a"], r["difficulty_b"])
            for r in responses
        )
        if total_info < 1e-10:
            return 3.0
        return round(1.0 / math.sqrt(total_info), 4)

    def _per_skill_estimates(self, state: CATState) -> dict[str, float]:
        """Rough per-skill theta estimates using only items from that skill."""
        skills: dict[str, list[dict]] = {}
        for r in state.responses:
            skills.setdefault(r["skill_id"], []).append(r)
        result = {}
        for skill_id, resps in skills.items():
            if len(resps) >= 2:
                result[skill_id] = self._estimate_theta(resps)
            else:
                result[skill_id] = state.theta  # too few items, use global
        return result
