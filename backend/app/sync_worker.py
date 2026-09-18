from __future__ import annotations

import argparse
import asyncio

from app.core.config import settings
from app.db.database import SessionLocal
from app.services.scheduled_sync import (
    enqueue_due_sync_jobs,
    process_due_sync_jobs,
    recover_stale_jobs,
)


async def run_cycle(*, force: bool = False) -> dict[str, int]:
    with SessionLocal() as db:
        recovered = recover_stale_jobs(db)
        queued = enqueue_due_sync_jobs(
            db,
            interval_hours=settings.scheduled_sync_interval_hours,
            max_attempts=settings.sync_job_max_attempts,
            force=force,
        )
        processed = await process_due_sync_jobs(db, limit=settings.sync_worker_batch_size)
        return {
            "recovered": recovered,
            "queued": len(queued),
            "processed": len(processed),
        }


async def worker_loop(*, once: bool, force: bool = False) -> None:
    while True:
        stats = await run_cycle(force=force)
        print(
            "TrafficVerdict sync worker:"
            f" recovered={stats['recovered']}"
            f" queued={stats['queued']}"
            f" processed={stats['processed']}"
            f" force={'yes' if force else 'no'}"
        )
        if once:
            return
        await asyncio.sleep(settings.sync_worker_poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="TrafficVerdict scheduled sync worker")
    parser.add_argument("--once", action="store_true", help="Run one scheduling/processing cycle and exit")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Development-only: queue all ready connections once, ignoring the normal sync interval",
    )
    args = parser.parse_args()

    if args.force and settings.environment.lower() not in {"development", "dev", "local", "test"}:
        parser.error("--force is only allowed in development/local/test environments")

    asyncio.run(worker_loop(once=args.once, force=args.force))


if __name__ == "__main__":
    main()
