import argparse
import asyncio
import logging
import sys

from app.core.database import AsyncSessionLocal
from app.services.system_service import system_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("purge_db_cli")


async def main():
    parser = argparse.ArgumentParser(description="AI Job Hunter - Database & Storage Purge Utility")
    parser.add_argument(
        "--scope",
        type=str,
        default="jobs_and_tailoring",
        choices=["all", "jobs_and_tailoring", "tailoring_only", "matches_only"],
        help="Scope of data to purge (default: 'jobs_and_tailoring')",
    )
    parser.add_argument(
        "--no-clean-storage",
        action="store_true",
        help="Skip cleaning local files on disk (PDF, TeX, MD artifacts)",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Wipe all data and re-sync skill taxonomy + candidate profile from context.example/",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    if not args.yes:
        action_name = "RESET DEMO" if args.reset_demo else f"PURGE (scope='{args.scope}')"
        confirm = input(f"⚠️  Are you sure you want to execute {action_name}? (y/N): ")
        if confirm.strip().lower() != "y":
            logger.info("Operation aborted by user.")
            return

    async with AsyncSessionLocal() as session:
        if args.reset_demo:
            logger.info("Executing system reset demo...")
            res = await system_service.reset_demo(session)
            logger.info(f"✅ Reset demo completed: {res['message']}")
        else:
            logger.info(f"Executing database purge with scope='{args.scope}'...")
            report = await system_service.purge_database(
                session=session,
                scope=args.scope,
                clean_storage=not args.no_clean_storage,
            )
            logger.info(f"✅ Purge completed successfully!")
            logger.info(f"Deleted row counts: {report.deleted_counts}")
            logger.info(f"Cleaned storage artifacts: {report.cleaned_storage}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exited.")
