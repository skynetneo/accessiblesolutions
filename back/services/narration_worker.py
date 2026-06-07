"""
back/services/narration_worker.py

Background worker that drains the narration_generation_queue.

Uses the atomic claim_narration_job() RPC to avoid double-processing
when multiple workers run concurrently.

Run:
    uv run services/narration_worker.py

Or as a background task launched from main.py on startup.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from db.client import get_async_client
from services.narration import NarrationService

logger = logging.getLogger(__name__)

POLL_INTERVAL = float(os.environ.get("NARRATION_WORKER_POLL_SECONDS", "2.0"))
MAX_CONSECUTIVE_EMPTY = int(os.environ.get("NARRATION_WORKER_IDLE_LIMIT", "0"))  # 0 = run forever


async def process_one(svc: NarrationService) -> bool:
    """Claim and process one queue item. Returns True if work was done."""
    client = await get_async_client()

    # Atomic claim
    result = await client.rpc("claim_narration_job", {}).execute()
    rows = result.data
    if not rows or len(rows) == 0:
        return False

    job = rows[0]
    job_id = job["id"]
    logger.info(f"Processing narration job {job_id}: {job['text'][:60]}...")

    try:
        narration = await svc.get_or_generate(
            text=job["text"],
            voice=job["voice"],
            speed=job["speed"],
            scaffold_level=job["scaffold_level"],
            skill_id=job.get("skill_id", ""),
            chain_step=job.get("chain_step", 0),
            tier=job["tier"],
        )

        # Mark done
        await (
            client.table("narration_generation_queue")
            .update({
                "status": "done",
                "content_hash": narration.content_hash,
                "processed_at": "now()",
            })
            .eq("id", job_id)
            .execute()
        )

        logger.info(
            f"Job {job_id} done: {narration.content_hash[:12]}... "
            f"({narration.duration_ms}ms, cached={narration.cached})"
        )
        return True

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        await (
            client.table("narration_generation_queue")
            .update({
                "status": "failed",
                "error_message": str(e)[:500],
                "processed_at": "now()",
            })
            .eq("id", job_id)
            .execute()
        )
        return True  # Still counts as "work done" for polling purposes


async def run_worker(svc: Optional[NarrationService] = None):
    """Main worker loop. Polls queue until empty (or forever if IDLE_LIMIT=0)."""
    svc = svc or NarrationService()
    empty_count = 0

    logger.info(f"Narration worker started (poll={POLL_INTERVAL}s)")

    while True:
        did_work = await process_one(svc)

        if did_work:
            empty_count = 0
        else:
            empty_count += 1
            if MAX_CONSECUTIVE_EMPTY > 0 and empty_count >= MAX_CONSECUTIVE_EMPTY:
                logger.info(f"Queue empty for {empty_count} polls, shutting down.")
                break
            await asyncio.sleep(POLL_INTERVAL)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [narration-worker] %(levelname)s %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
