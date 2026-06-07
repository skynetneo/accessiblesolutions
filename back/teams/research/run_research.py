"""
back/teams/research/run_research.py

CLI for batch-researching skills and writing them to the database.

Usage — single skill:
    uv run teams/research/run_research.py \\
        --skill "Network Fundamentals" \\
        --subject it_fundamentals \\
        --curriculum-id comptia_a_plus

Usage — batch from JSON file:
    uv run teams/research/run_research.py --batch skills.json

Batch file format (JSON array):
    [
        {
            "skill": "Network Fundamentals",
            "subject": "it_fundamentals",
            "curriculum_id": "comptia_a_plus"
        },
        {
            "skill": "Solve One-Step Equations",
            "subject": "math",
            "curriculum_id": "ged"
        }
    ]

The agent handles duplicate detection, web research, validation, and DB write
for each skill. Results are printed to stdout.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Ensure the back/ directory is on the path when run directly
_BACK_DIR = Path(__file__).resolve().parent.parent.parent
if str(_BACK_DIR) not in sys.path:
    sys.path.insert(0, str(_BACK_DIR))

from teams.research.research_agent import agent  # noqa: E402 — path fix must come first


def _build_prompt(skill: str, subject: str, curriculum_id: str) -> str:
    return (
        f"Research and create a skill chain for:\n"
        f"  Skill: {skill}\n"
        f"  Subject: {subject}\n"
        f"  Curriculum ID: {curriculum_id}\n\n"
        f"Follow the full workflow: check for duplicates, research, validate, and write to the database."
    )


async def research_one(skill: str, subject: str, curriculum_id: str) -> dict:
    """Invoke the research agent for a single skill and return a result summary."""
    thread_id = f"research_{uuid.uuid4().hex}"
    prompt = _build_prompt(skill, subject, curriculum_id)

    print(f"\n[→] Researching: {skill!r} ({subject}, {curriculum_id})")

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": thread_id}},
        )
        messages = result.get("messages", [])
        final = messages[-1] if messages else None
        response = final.content if final is not None and hasattr(final, "content") else str(final)
        print(f"[✓] Done: {response[:200]}")
        return {"skill": skill, "ok": True, "response": response}
    except Exception as exc:
        print(f"[✗] Error: {exc}")
        return {"skill": skill, "ok": False, "error": str(exc)}


async def run_batch(items: list[dict]) -> list[dict]:
    """Research a list of skills sequentially (one at a time to respect rate limits)."""
    results = []
    for item in items:
        skill = item.get("skill", "")
        subject = item.get("subject", "general")
        curriculum_id = item.get("curriculum_id", "ged")

        if not skill:
            print(f"[!] Skipping item with missing 'skill' key: {item}")
            results.append({"skill": skill, "ok": False, "error": "missing skill"})
            continue

        result = await research_one(skill, subject, curriculum_id)
        results.append(result)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-research skills and write skill chains to the database."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skill", type=str, help="Single skill name to research")
    group.add_argument("--batch", type=str, help="Path to a JSON batch file")

    parser.add_argument(
        "--subject",
        type=str,
        default="general",
        help="Subject slug (used with --skill). Default: general",
    )
    parser.add_argument(
        "--curriculum-id",
        type=str,
        default="ged",
        dest="curriculum_id",
        help="Curriculum ID (used with --skill). Default: ged",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to write results JSON",
    )

    args = parser.parse_args()

    if args.skill:
        items = [{"skill": args.skill, "subject": args.subject, "curriculum_id": args.curriculum_id}]
    else:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Error: batch file not found: {batch_path}")
            sys.exit(1)
        with batch_path.open() as f:
            items = json.load(f)
        if not isinstance(items, list):
            print("Error: batch file must contain a JSON array")
            sys.exit(1)

    print(f"Research queue: {len(items)} skill(s)")
    results = asyncio.run(run_batch(items))

    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    print(f"\nSummary: {ok_count} succeeded, {fail_count} failed out of {len(results)}")

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Results written to {out_path}")


if __name__ == "__main__":
    main()
