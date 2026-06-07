"""
back/db/seed_pipeline.py

Pipeline for importing expert-authored curriculum seeds into the database.

Usage:
    uv run db/seed_pipeline.py /path/to/seeds [--curriculum comptia_a_plus]

This script reads all .txt files in the given directory, parses them using
seed_parser.py, and upserts them into the seed_items Supabase table.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from tqdm import tqdm

from db.client import get_async_client
from db.seed_parser import parse_seed_file


async def run_pipeline(seeds_dir: Path, override_curriculum: str | None = None):
    """Parse all seed files in a directory and upsert them to Supabase."""
    if not seeds_dir.exists() or not seeds_dir.is_dir():
        print(f"Error: Directory not found: {seeds_dir}")
        return

    client = await get_async_client()
    
    print(f"Scanning {seeds_dir} for .txt seed files...")
    seed_files = list(seeds_dir.glob("**/*.txt"))
    
    if not seed_files:
        print("No .txt files found.")
        return

    total_items = 0
    errors = 0

    print("Parsing files...")
    # Read and parse everything locally first
    all_seeds = []
    for filepath in tqdm(seed_files):
        try:
            items = parse_seed_file(filepath)
            
            # Allow CLI to override the CURRICULUM: header
            if override_curriculum:
                for item in items:
                    item.curriculum_id = override_curriculum
                    
            all_seeds.extend(items)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            errors += 1

    if not all_seeds:
        print("No valid seed items found in the parsed files.")
        return

    print(f"\nParsed {len(all_seeds)} total seed items.")
    print("Upserting to Supabase (seed_items table)...")

    # Batch upsert to Supabase
    BATCH_SIZE = 50
    for i in tqdm(range(0, len(all_seeds), BATCH_SIZE)):
        batch = all_seeds[i : i + BATCH_SIZE]
        
        # Convert objects to dicts matching the DB schema
        db_rows = []
        for item in batch:
            row = item.to_dict()
            # If your Supabase schema uses JSONB for choices, ensure it's a list.
            db_rows.append(row)
            
        try:
            # Upsert using seed_id as the primary key/conflict resolution column
            await client.table("seed_items").upsert(
                db_rows, 
                on_conflict="seed_id"
            ).execute()
            total_items += len(batch)
        except Exception as e:
            print(f"\nError upserting batch starting at index {i}: {e}")
            errors += 1

    print(f"\nPipeline complete! Successfully upserted {total_items} items.")
    if errors > 0:
        print(f"Encountered {errors} error(s) during processing.")


def main():
    parser = argparse.ArgumentParser(description="Praxis Seed Sync Pipeline")
    parser.add_argument("seeds_dir", type=str, help="Directory containing .txt seed files")
    parser.add_argument(
        "--curriculum", 
        type=str, 
        help="Override curriculum_id for all imported seeds (e.g. 'comptia_a_plus')"
    )
    args = parser.parse_args()

    asyncio.run(run_pipeline(Path(args.seeds_dir), args.curriculum))


if __name__ == "__main__":
    main()
