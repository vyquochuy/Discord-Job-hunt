import asyncio
import logging
import sys
import redis.asyncio as aioredis
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("worker")


async def main():
    logger.info(f"Starting Job Hunter Background Worker in {settings.ENVIRONMENT} mode...")
    logger.info(f"Connecting to Redis at: {settings.REDIS_URL}")

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        pong = await r.ping()
        logger.info(f"Redis connection successful: {pong}")
        await r.aclose()
    except Exception as e:
        logger.warning(f"Could not connect to Redis during startup check: {e}")

    logger.info("Worker is ready and listening for background tasks.")

    # Vòng lặp giữ worker chạy ngầm (sẽ tích hợp task queue ARQ / RQ ở các Phase tiếp theo)
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped gracefully.")
