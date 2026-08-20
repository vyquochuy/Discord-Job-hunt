import argparse
import asyncio
import logging
import sys
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.remotive_adapter import RemotiveJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.ingestion_pipeline import ingestion_pipeline
from app.services.normalization.skill_normalizer import skill_normalizer

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("worker")


async def run_collection_cycle(limit: int = 15):
    """Thực hiện một chu kỳ cào tin từ tất cả các adapters được kích hoạt."""
    logger.info("==================================================")
    logger.info("Starting Scheduled Job Collection Cycle...")
    logger.info("==================================================")

    collectors = [
        RemotiveJobCollector(),
        ITViecJobCollector(),
        CareerLinkJobCollector(),
        TopCVJobCollector(),
    ]

    async with AsyncSessionLocal() as session:
        # Seed / Sync taxonomy
        try:
            await skill_normalizer.seed_or_sync_db(session)
        except Exception as e:
            logger.warning(f"Could not sync skill taxonomy: {e}")

        for collector in collectors:
            try:
                stats = await ingestion_pipeline.run(collector, session, limit=limit)
                logger.info(
                    f"[{collector.source_name}] Ingestion Report: "
                    f"Fetched: {stats.total_fetched}, Created: {stats.created}, "
                    f"Unchanged: {stats.unchanged}, Duplicates: {stats.duplicates_detected}, Errors: {stats.errors}"
                )
            except Exception as e:
                logger.error(f"Error running collection for {collector.source_name}: {e}", exc_info=True)

    logger.info("Job Collection Cycle Completed successfully.")


async def main(run_once: bool = False, interval_seconds: int = 3600):
    logger.info(f"Starting Job Hunter Background Worker in {settings.ENVIRONMENT} mode...")
    logger.info(f"Connecting to Redis at: {settings.REDIS_URL}")

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        pong = await r.ping()
        logger.info(f"Redis connection successful: {pong}")
        await r.aclose()
    except Exception as e:
        logger.warning(f"Could not connect to Redis during startup check (running in standalone loop mode): {e}")

    if run_once:
        logger.info("Executing single collection run (--run-once)...")
        await run_collection_cycle(limit=10)
        logger.info("Run-once completed. Exiting worker.")
        return

    logger.info(f"Worker is active. Job Collection scheduled every {interval_seconds} seconds.")

    # Vòng lặp định kỳ thu thập tin tuyển dụng
    while True:
        try:
            await run_collection_cycle(limit=20)
        except Exception as e:
            logger.error(f"Error in background worker collection loop: {e}", exc_info=True)

        logger.info(f"Sleeping for {interval_seconds} seconds until next cycle...")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Hunter Background Worker")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one job collection cycle immediately and exit",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval between collection cycles in seconds (default: 3600s)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(run_once=args.run_once, interval_seconds=args.interval))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped gracefully.")
