#!/usr/bin/env python3
"""
rescue_jobs.py — Unstick jobs stranded in 'processing' state.

Usage:
    uv run python rescue_jobs.py --queued       # reset to 'queued' (workers will retry)
    uv run python rescue_jobs.py --failed       # mark as 'failed' (close them out)
    uv run python rescue_jobs.py --queued --dry-run   # preview only, no writes

Options:
    --queued      Reset stuck jobs back to 'queued' so workers pick them up again.
    --failed      Mark stuck jobs as 'failed' (terminal state, stops polling loops).
    --dry-run     Print what would be changed without writing to the DB.
    --older-than  Only target jobs older than N seconds (default: 0 = all processing jobs).
                  Example: --older-than 300  (only jobs stuck for >5 minutes)
    --db          Path to the SQLite DB (default: $RESULT_DB_PATH or data/result_db.db).
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from sqlmodel import Session, create_engine, select, col

from result_store.results_db import Result


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S,%f"[:-3],
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rescue jobs stuck in 'processing' state.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--queued",
        action="store_true",
        help="Reset stuck jobs to 'queued' so workers pick them up again.",
    )
    target_group.add_argument(
        "--failed",
        action="store_true",
        help="Mark stuck jobs as 'failed' (terminal — stops polling loops).",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to the DB.",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Only target jobs whose job_id timestamp is older than N seconds. "
             "Uses the embedded UUIDv7 timestamp. Default: 0 (all processing jobs).",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("RESULT_DB_PATH", "data/result_db.db"),
        metavar="PATH",
        help="Path to the SQLite DB file (default: $RESULT_DB_PATH or data/result_db.db).",
    )

    return parser.parse_args()


def uuid7_timestamp_ms(job_id: str) -> int | None:
    """Extract the millisecond Unix timestamp embedded in a UUIDv7 job_id.

    UUIDv7 format: tttttttt-tttt-7xxx-xxxx-xxxxxxxxxxxx
    The first 48 bits are a Unix ms timestamp.
    Returns None if the job_id doesn't look like a UUIDv7 (e.g. 'sync_...' jobs).
    """
    try:
        clean = job_id.replace("-", "")
        if len(clean) != 32:
            return None
        return int(clean[:12], 16)  # top 48 bits = ms timestamp
    except (ValueError, TypeError):
        return None


def age_seconds(job_id: str) -> float | None:
    """Return how many seconds ago this job was created, or None if unknown."""
    ms = uuid7_timestamp_ms(job_id)
    if ms is None:
        return None
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return (now_ms - ms) / 1000.0


def main() -> None:
    args = parse_args()
    new_status = "queued" if args.queued else "failed"
    dry_run = args.dry_run

    if dry_run:
        logging.info("DRY RUN — no changes will be written.")

    engine = create_engine(f"sqlite:///{args.db}")

    with Session(engine) as session:
        statement = select(Result).where(col(Result.status) == "processing")
        stuck_jobs: list[Result] = session.exec(statement).all()

    if not stuck_jobs:
        logging.info("No jobs currently in 'processing' state. Nothing to do.")
        sys.exit(0)

    # Filter by age if --older-than was specified
    targets: list[Result] = []
    skipped_age: list[Result] = []
    skipped_unknown_age: list[Result] = []

    for job in stuck_jobs:
        if args.older_than == 0:
            targets.append(job)
            continue

        age = age_seconds(job.job_id)
        if age is None:
            # Can't determine age (e.g. sync_ prefix jobs) — include them to be safe
            logging.warning(
                f"  Job {job.job_id}: cannot determine age (non-UUIDv7 ID) — including it."
            )
            skipped_unknown_age.append(job)
            targets.append(job)
        elif age >= args.older_than:
            targets.append(job)
        else:
            skipped_age.append(job)

    logging.info(
        f"Found {len(stuck_jobs)} job(s) in 'processing'. "
        f"Targeting {len(targets)}, skipping {len(skipped_age)} (not old enough)."
    )

    if not targets:
        logging.info("No jobs match the filter criteria. Nothing to do.")
        sys.exit(0)

    print()
    print(f"{'JOB ID':<42}  {'AGE':>8}  {'ACTION'}")
    print("-" * 68)

    changed = 0
    for job in targets:
        age = age_seconds(job.job_id)
        age_str = f"{age:.0f}s" if age is not None else "unknown"
        action = f"processing → {new_status}"
        print(f"  {job.job_id:<40}  {age_str:>8}  {action}")
        changed += 1

    print("-" * 68)
    print(f"  {changed} job(s) will be set to '{new_status}'.")
    print()

    if dry_run:
        logging.info("Dry run complete. Use without --dry-run to apply.")
        sys.exit(0)

    # Apply changes
    with Session(engine) as session:
        for job in targets:
            statement = select(Result).where(col(Result.job_id) == job.job_id)
            row = session.exec(statement).first()
            if row:
                row.status = new_status
                row.response = None if new_status == "queued" else "Rescued by rescue_jobs.py"
        session.commit()

    logging.info(f"Done. {changed} job(s) updated to '{new_status}'.")

    if new_status == "queued":
        logging.info(
            "Jobs are now 'queued'. Workers will pick them up automatically "
            "if RabbitMQ consumers are running — but note: the messages are NOT "
            "re-published to RabbitMQ by this script. Use this only after confirming "
            "the original messages are still in the queue (unacked/redelivered).\n"
            "If the queue is empty, you will need to re-submit the requests."
        )


if __name__ == "__main__":
    main()
