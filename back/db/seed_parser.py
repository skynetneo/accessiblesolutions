"""
praxis/db/seed_parser.py

Parses .txt seed files into structured seed items for the item bank.

Seed format (one item per block, separated by blank lines):

    SKILL: rla.reading.main_idea
    STEP: 1
    DIFFICULTY: -0.5
    SCAFFOLD: 3
    SUBJECT: rla
    CURRICULUM: ged

    The manager posted a notice on the break room bulletin board. It stated
    that starting next month, all employees must clock in using the new
    digital system. Paper timesheets would no longer be accepted.

    [QUESTION]
    What is the main purpose of the notice?

    [CHOICES]
    A) To announce a new employee benefit
    B) To explain a change in the attendance tracking system
    C) To describe the break room rules
    D) To introduce a new manager

    [ANSWER]
    B

    [EXPLANATION]
    The notice specifically describes a change from paper timesheets to a
    digital clock-in system, making B the correct answer.

The [QUESTION] marker is REQUIRED. It prevents the parser from being
fooled by question marks in dialogue passages (e.g., "Where are you going?").

Optional markers: [CHOICES], [ANSWER], [EXPLANATION], [RATIONALE]
If [CHOICES] is absent, the item is treated as free-response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SeedItem:
    skill_id: str
    chain_step: int
    difficulty_b: float
    scaffold_level: int  # 1-5, standardized with prompt_hierarchy.py
    subject: str
    passage: str
    question_text: str
    curriculum_id: str = "ged"
    choices: list[str] = field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    seed_id: str = ""

    def to_dict(self) -> dict:
        return {
            "seed_id": self.seed_id,
            "skill_id": self.skill_id,
            "chain_step": self.chain_step,
            "difficulty_b": self.difficulty_b,
            "scaffold_level": self.scaffold_level,
            "subject": self.subject,
            "curriculum_id": self.curriculum_id,
            "passage": self.passage,
            "question_text": self.question_text,
            "choices": self.choices,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
        }


# Header key patterns
_HEADER_RE = re.compile(
    r"^(SKILL|STEP|DIFFICULTY|SCAFFOLD|SUBJECT|CURRICULUM)\s*:\s*(.+)$",
    re.IGNORECASE,
)

# Section markers
_MARKERS = {"[QUESTION]", "[CHOICES]", "[ANSWER]", "[EXPLANATION]", "[RATIONALE]"}


def parse_seed_file(path: str | Path) -> list[SeedItem]:
    """Parse a seed .txt file into a list of SeedItem objects.

    Items are separated by double blank lines (or more).
    Each item must contain a [QUESTION] marker.
    """
    text = Path(path).read_text(encoding="utf-8")
    blocks = re.split(r"\n{3,}", text.strip())
    items: list[SeedItem] = []

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue

        item = _parse_block(block)
        if item is None:
            continue

        if not item.seed_id:
            item.seed_id = f"{item.skill_id}:{item.chain_step}:{i}"

        items.append(item)

    return items


def _parse_block(block: str) -> Optional[SeedItem]:
    """Parse a single seed block into a SeedItem."""
    lines = block.split("\n")

    # Extract headers from the top of the block
    headers: dict[str, str] = {}
    content_start = 0

    for i, line in enumerate(lines):
        m = _HEADER_RE.match(line.strip())
        if m:
            headers[m.group(1).upper()] = m.group(2).strip()
            content_start = i + 1
        elif line.strip() == "":
            content_start = i + 1
        else:
            break

    # Must have [QUESTION] marker
    remaining = "\n".join(lines[content_start:])
    if "[QUESTION]" not in remaining:
        return None

    # Split into sections by markers
    sections = _split_by_markers(remaining)

    passage = sections.get("_passage", "").strip()
    question = sections.get("[QUESTION]", "").strip()
    choices_raw = sections.get("[CHOICES]", "").strip()
    answer = sections.get("[ANSWER]", "").strip()
    explanation = (
        sections.get("[EXPLANATION]", "") or
        sections.get("[RATIONALE]", "")
    ).strip()

    if not question:
        return None

    # Parse choices: "A) ...", "B) ...", etc.
    choices: list[str] = []
    if choices_raw:
        choices = [
            line.strip()
            for line in re.split(r"\n(?=[A-Z]\))", choices_raw)
            if line.strip()
        ]
        # Strip the letter prefix for storage
        choices = [re.sub(r"^[A-Z]\)\s*", "", c) for c in choices]

    # Parse correct answer — could be just "B" or "B) full text"
    correct = answer.strip()
    if len(correct) == 1 and correct.isalpha() and choices:
        idx = ord(correct.upper()) - ord("A")
        if 0 <= idx < len(choices):
            correct = choices[idx]

    return SeedItem(
        skill_id=headers.get("SKILL", "unknown"),
        chain_step=int(headers.get("STEP", "0")),
        difficulty_b=float(headers.get("DIFFICULTY", "0.0")),
        scaffold_level=int(headers.get("SCAFFOLD", "3")),
        subject=headers.get("SUBJECT", ""),
        curriculum_id=headers.get("CURRICULUM", "ged").lower(),
        passage=passage,
        question_text=question,
        choices=choices,
        correct_answer=correct,
        explanation=explanation,
    )


def _split_by_markers(text: str) -> dict[str, str]:
    """Split text into sections by [MARKER] tags.

    Everything before the first marker goes into "_passage".
    """
    sections: dict[str, str] = {}
    current_key = "_passage"
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip().upper()
        if stripped in _MARKERS:
            # Save current section
            sections[current_key] = "\n".join(current_lines)
            current_key = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # Save final section
    sections[current_key] = "\n".join(current_lines)
    return sections
