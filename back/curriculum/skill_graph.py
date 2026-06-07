"""
praxis/curriculum/skill_graph.py

Prerequisite dependency graph for the curriculum.

Builds a directed acyclic graph (DAG) from skill_chains and skill_prerequisites
tables in Supabase. Used by the lesson sequencer, assessment team, and content
team to determine:
  - What skills can be taught next (prerequisites met)
  - The critical path from current skills to a target
  - ZPD candidates (skills just beyond current mastery)
  - Which skills to prioritize by employment relevance

The graph operates at two levels:
  1. Chain level: chain_math_percentages depends on chain_math_fractions_decimals
  2. Step level: step 5 of a chain depends on steps 1-4 of the same chain (implicit)
     AND may depend on specific steps of OTHER chains (explicit, from skill_prerequisites)

Usage:
    from curriculum.skill_graph import SkillGraph

    graph = await SkillGraph.build_from_db()

    # What can this learner work on next?
    teachable = graph.get_next_teachable(mastered={"fractions_decimals:1", "fractions_decimals:2"})

    # Critical path to a target
    path = graph.get_critical_path(
        current={"fractions_decimals:1", "fractions_decimals:2"},
        target={"percentages:5"}
    )

    # ZPD candidates
    zpd = graph.get_zpd_candidates(mastered_skills, skill_levels)
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

from db.client import db


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────

@dataclass
class SkillNode:
    """A single teachable unit: one step of one skill chain."""
    skill_id: str           # e.g. "fractions_decimals"
    chain_id: str           # e.g. "chain_math_fractions_decimals"
    chain_step: int         # e.g. 3
    subject: str            # e.g. "math"
    step_description: str = ""
    total_steps: int = 0    # total steps in this chain

    # Graph edges
    prerequisites: set[str] = field(default_factory=set)  # set of node_ids this depends on
    unlocks: set[str] = field(default_factory=set)        # set of node_ids that depend on this

    @property
    def node_id(self) -> str:
        """Canonical identifier: skill_id:step"""
        return f"{self.skill_id}:{self.chain_step}"

    @property
    def is_entry_point(self) -> bool:
        """True if this node has no prerequisites (can start immediately)."""
        return len(self.prerequisites) == 0

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if isinstance(other, SkillNode):
            return self.node_id == other.node_id
        return False


@dataclass
class ChainSummary:
    """Summary of a skill chain for high-level queries."""
    chain_id: str
    skill_id: str
    subject: str
    description: str
    total_steps: int
    depends_on_chains: list[str] = field(default_factory=list)  # chain_ids


# ──────────────────────────────────────────────────────────────
# Skill Graph
# ──────────────────────────────────────────────────────────────

class SkillGraph:
    """
    Directed acyclic graph of all teachable skills in the curriculum.

    Nodes = individual chain steps (skill_id:step)
    Edges = prerequisites (must master X before attempting Y)

    Two types of edges:
      1. Implicit intra-chain: step N depends on step N-1 within the same chain
      2. Explicit cross-chain: from skill_prerequisites table
    """

    def __init__(self):
        self.nodes: dict[str, SkillNode] = {}
        self.chains: dict[str, ChainSummary] = {}
        self._built = False

    @classmethod
    async def build_from_db(cls, curriculum_id: str = "ged") -> SkillGraph:
        """Build the complete skill graph from Supabase tables."""
        graph = cls()

        # 1. Load all skill chains
        all_chains = await asyncio.to_thread(
            db.fetch_all_chains,
            curriculum_id=curriculum_id,
        )

        for chain in all_chains:
            chain_id = chain.get("chain_id", "")
            skill_id = chain.get("skill_id", "")
            subject = chain.get("subject", "")
            description = chain.get("description", "")
            steps = chain.get("steps", [])
            total_steps = len(steps) if isinstance(steps, list) else chain.get("total_steps", 0)

            graph.chains[chain_id] = ChainSummary(
                chain_id=chain_id,
                skill_id=skill_id,
                subject=subject,
                description=description,
                total_steps=total_steps,
            )

            # Create nodes for each step
            if isinstance(steps, list):
                for i, step_data in enumerate(steps):
                    step_num = i + 1  # 1-indexed
                    step_desc = ""
                    if isinstance(step_data, dict):
                        step_desc = step_data.get("description", "")
                    elif isinstance(step_data, str):
                        step_desc = step_data

                    node = SkillNode(
                        skill_id=skill_id,
                        chain_id=chain_id,
                        chain_step=step_num,
                        subject=subject,
                        step_description=step_desc,
                        total_steps=total_steps,
                    )
                    graph.nodes[node.node_id] = node
            elif total_steps > 0:
                # steps is a count, not a list — create placeholder nodes
                for step_num in range(1, total_steps + 1):
                    node = SkillNode(
                        skill_id=skill_id,
                        chain_id=chain_id,
                        chain_step=step_num,
                        subject=subject,
                        total_steps=total_steps,
                    )
                    graph.nodes[node.node_id] = node

        # 2. Add implicit intra-chain edges (step N depends on step N-1)
        for node in graph.nodes.values():
            if node.chain_step > 1:
                prev_id = f"{node.skill_id}:{node.chain_step - 1}"
                if prev_id in graph.nodes:
                    node.prerequisites.add(prev_id)
                    graph.nodes[prev_id].unlocks.add(node.node_id)

        # 3. Load explicit cross-chain prerequisites
        try:
            def _load_prereqs():
                try:
                    return (
                        db.client.table("skill_prerequisites")
                        .select("*")
                        .eq("curriculum_id", curriculum_id)
                        .execute()
                    )
                except Exception as scoped_exc:
                    logger.warning(
                        "Falling back to unscoped skill_prerequisites query: %s",
                        scoped_exc,
                    )
                    return db.client.table("skill_prerequisites").select("*").execute()

            prereqs_result = await asyncio.to_thread(_load_prereqs)
            prereqs = prereqs_result.data or []
        except Exception as exc:
            # Table may not exist yet
            logger.warning("Could not load skill_prerequisites; continuing without explicit cross-chain edges: %s", exc)
            prereqs = []

        for prereq in prereqs:
            skill_id = prereq.get("skill_id", "")
            skill_step = prereq.get("chain_step")
            requires_skill = prereq.get("requires_skill_id", "")
            requires_step = prereq.get("requires_step")

            if skill_step and requires_step:
                # Step-level dependency
                target_id = f"{skill_id}:{skill_step}"
                source_id = f"{requires_skill}:{requires_step}"
                if target_id in graph.nodes and source_id in graph.nodes:
                    graph.nodes[target_id].prerequisites.add(source_id)
                    graph.nodes[source_id].unlocks.add(target_id)

            elif skill_step and not requires_step:
                # This step depends on the ENTIRE prerequisite chain
                target_id = f"{skill_id}:{skill_step}"
                # Find the last step of the required chain
                req_chain = next(
                    (c for c in graph.chains.values() if c.skill_id == requires_skill),
                    None,
                )
                if req_chain and target_id in graph.nodes:
                    last_step_id = f"{requires_skill}:{req_chain.total_steps}"
                    if last_step_id in graph.nodes:
                        graph.nodes[target_id].prerequisites.add(last_step_id)
                        graph.nodes[last_step_id].unlocks.add(target_id)

            elif not skill_step and requires_step:
                # The FIRST step of this chain depends on a specific prereq step
                target_id = f"{skill_id}:1"
                source_id = f"{requires_skill}:{requires_step}"
                if target_id in graph.nodes and source_id in graph.nodes:
                    graph.nodes[target_id].prerequisites.add(source_id)
                    graph.nodes[source_id].unlocks.add(target_id)

            else:
                # Whole-chain to whole-chain: first step depends on last step of prereq
                req_chain = next(
                    (c for c in graph.chains.values() if c.skill_id == requires_skill),
                    None,
                )
                target_id = f"{skill_id}:1"
                if req_chain and target_id in graph.nodes:
                    last_step_id = f"{requires_skill}:{req_chain.total_steps}"
                    if last_step_id in graph.nodes:
                        graph.nodes[target_id].prerequisites.add(last_step_id)
                        graph.nodes[last_step_id].unlocks.add(target_id)

            # Track chain-level dependencies on the summary
            target_chain = next(
                (c for c in graph.chains.values() if c.skill_id == skill_id),
                None,
            )
            if target_chain and requires_skill not in [
                graph.chains[cid].skill_id
                for cid in target_chain.depends_on_chains
                if cid in graph.chains
            ]:
                # Find the chain_id for requires_skill
                req_chain_obj = next(
                    (c for c in graph.chains.values() if c.skill_id == requires_skill),
                    None,
                )
                if req_chain_obj:
                    target_chain.depends_on_chains.append(req_chain_obj.chain_id)

        graph._built = True
        return graph

    # ──────────────────────────────────────────────────────────
    # Query methods
    # ──────────────────────────────────────────────────────────

    def get_entry_points(self, subject: Optional[str] = None) -> list[SkillNode]:
        """Get all skills that have no prerequisites (starting points).

        Args:
            subject: Filter to a specific subject area
        """
        entries = [n for n in self.nodes.values() if n.is_entry_point]
        if subject:
            entries = [n for n in entries if n.subject == subject]
        return sorted(entries, key=lambda n: (n.subject, n.skill_id, n.chain_step))

    def get_prerequisites(self, node_id: str) -> set[str]:
        """Get all prerequisites for a given skill step (transitive closure).

        Returns the complete set of node_ids that must be mastered before
        the given node can be attempted.
        """
        if node_id not in self.nodes:
            return set()

        visited = set()
        queue = deque([node_id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            node = self.nodes.get(current)
            if node:
                for prereq in node.prerequisites:
                    if prereq not in visited:
                        queue.append(prereq)

        visited.discard(node_id)  # don't include self
        return visited

    def get_next_teachable(
        self,
        mastered: set[str],
        subject: Optional[str] = None,
    ) -> list[SkillNode]:
        """Get skills whose prerequisites are ALL met by the mastered set.

        These are the frontier: skills the learner is ready to attempt.

        Args:
            mastered: Set of node_ids the learner has mastered (e.g. {"fractions_decimals:1", ...})
            subject: Filter to specific subject area
        """
        teachable = []
        for node in self.nodes.values():
            if node.node_id in mastered:
                continue  # already mastered
            if subject and node.subject != subject:
                continue
            if node.prerequisites.issubset(mastered):
                teachable.append(node)

        return sorted(teachable, key=lambda n: (n.subject, n.skill_id, n.chain_step))

    def get_critical_path(
        self,
        current: set[str],
        target: str,
    ) -> list[str]:
        """Find the shortest sequence of skills from current state to target.

        Uses reverse BFS from target, filtering out already-mastered skills.

        Args:
            current: Set of node_ids the learner has mastered
            target: The target node_id to reach

        Returns:
            Ordered list of node_ids to learn, from first to last.
            Empty list if target is already mastered or unreachable.
        """
        if target in current:
            return []
        if target not in self.nodes:
            return []

        # BFS backward from target to find all unmastered prerequisites
        needed = []
        visited = set()
        queue = deque([target])

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)

            if node_id not in current:
                needed.append(node_id)
                node = self.nodes.get(node_id)
                if node:
                    for prereq in node.prerequisites:
                        if prereq not in visited and prereq not in current:
                            queue.append(prereq)

        # Topological sort of needed skills
        return self._topo_sort(needed)

    def get_zpd_candidates(
        self,
        mastered: set[str],
        skill_levels: dict[str, float] = None,
        max_distance: int = 2,
    ) -> list[SkillNode]:
        """Get skills in the Zone of Proximal Development.

        ZPD = skills that are reachable within max_distance steps from
        the current mastery frontier. These are challenging but achievable.

        Args:
            mastered: Set of mastered node_ids
            skill_levels: Optional dict of node_id → theta (for difficulty ordering)
            max_distance: Maximum prerequisite depth from frontier (default 2)
        """
        # Start with immediately teachable skills
        frontier = self.get_next_teachable(mastered)
        zpd = set(n.node_id for n in frontier)

        # Expand by max_distance layers
        current_layer = set(n.node_id for n in frontier)
        for _ in range(max_distance - 1):
            next_layer = set()
            for node_id in current_layer:
                node = self.nodes.get(node_id)
                if node:
                    for unlocked in node.unlocks:
                        # Check if all OTHER prereqs (excluding current layer) are met
                        unlock_node = self.nodes.get(unlocked)
                        if unlock_node:
                            other_prereqs = unlock_node.prerequisites - current_layer - mastered
                            if len(other_prereqs) <= 1:  # Allow 1 unmet prereq for ZPD
                                next_layer.add(unlocked)
            zpd.update(next_layer)
            current_layer = next_layer

        zpd -= mastered
        result = [self.nodes[nid] for nid in zpd if nid in self.nodes]

        # Sort by difficulty if skill_levels provided
        if skill_levels:
            result.sort(key=lambda n: skill_levels.get(n.node_id, 0.0))
        else:
            result.sort(key=lambda n: (n.subject, n.skill_id, n.chain_step))

        return result

    def get_chain_progress(
        self,
        mastered: set[str],
        chain_id: str,
    ) -> dict:
        """Get progress through a specific skill chain.

        Args:
            mastered: Set of mastered node_ids
            chain_id: Chain to check progress for

        Returns:
            Dict with total_steps, mastered_steps, current_step, percent_complete
        """
        chain = self.chains.get(chain_id)
        if not chain:
            return {"error": f"Chain {chain_id} not found"}

        chain_nodes = [
            n for n in self.nodes.values()
            if n.chain_id == chain_id
        ]
        chain_nodes.sort(key=lambda n: n.chain_step)

        mastered_steps = [n for n in chain_nodes if n.node_id in mastered]
        highest_mastered = max((n.chain_step for n in mastered_steps), default=0)
        current_step = highest_mastered + 1 if highest_mastered < chain.total_steps else chain.total_steps

        return {
            "chain_id": chain_id,
            "skill_id": chain.skill_id,
            "subject": chain.subject,
            "total_steps": chain.total_steps,
            "mastered_steps": len(mastered_steps),
            "current_step": current_step,
            "percent_complete": round(len(mastered_steps) / max(chain.total_steps, 1) * 100, 1),
            "description": chain.description,
        }

    def get_all_progress(self, mastered: set[str]) -> list[dict]:
        """Get progress across all chains."""
        return [
            self.get_chain_progress(mastered, cid)
            for cid in self.chains
        ]

    def get_subject_readiness(
        self,
        mastered: set[str],
        subject: str,
    ) -> dict:
        """Estimate domain readiness for a subject area.

        Args:
            mastered: Set of mastered node_ids
            subject: Subject to evaluate

        Returns:
            Dict with total skills, mastered count, readiness percentage,
            and list of remaining skills to master.
        """
        subject_nodes = [n for n in self.nodes.values() if n.subject == subject]
        subject_mastered = [n for n in subject_nodes if n.node_id in mastered]
        remaining = [n for n in subject_nodes if n.node_id not in mastered]

        return {
            "subject": subject,
            "total_skills": len(subject_nodes),
            "mastered": len(subject_mastered),
            "remaining": len(remaining),
            "readiness_percent": round(
                len(subject_mastered) / max(len(subject_nodes), 1) * 100, 1
            ),
            "next_teachable": [
                n.node_id for n in self.get_next_teachable(mastered, subject)
            ][:5],
        }

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _topo_sort(self, node_ids: list[str]) -> list[str]:
        """Topological sort of a subset of nodes."""
        subset = set(node_ids)
        in_degree = defaultdict(int)
        for nid in subset:
            node = self.nodes.get(nid)
            if node:
                for prereq in node.prerequisites:
                    if prereq in subset:
                        in_degree[nid] += 1

        queue = deque([nid for nid in subset if in_degree[nid] == 0])
        result = []

        while queue:
            nid = queue.popleft()
            result.append(nid)
            node = self.nodes.get(nid)
            if node:
                for unlocked in node.unlocks:
                    if unlocked in subset:
                        in_degree[unlocked] -= 1
                        if in_degree[unlocked] == 0:
                            queue.append(unlocked)

        return result

    def __repr__(self) -> str:
        return (
            f"SkillGraph(chains={len(self.chains)}, "
            f"nodes={len(self.nodes)}, "
            f"entry_points={len(self.get_entry_points())})"
        )
