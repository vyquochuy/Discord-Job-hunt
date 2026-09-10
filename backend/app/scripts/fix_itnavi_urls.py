import asyncio
import logging
import re
import sys
import httpx
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

import io
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("fix_itnavi_urls")


async def fix_all_itnavi_urls():
    async with AsyncSessionLocal() as session:
        # Lấy tất cả jobs có apply_url dạng /job/
        stmt = text("SELECT id, apply_url FROM jobs WHERE apply_url LIKE '%itnavi.com.vn/job/%'")
        res = await session.execute(stmt)
        jobs = res.fetchall()

        logger.info(f"Tìm thấy {len(jobs)} tin ITNavi có đường dẫn cũ dạng /job/...")
        if not jobs:
            logger.info("Không có tin nào cần cập nhật.")
            return

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://itnavi.com.vn/",
        }

        semaphore = asyncio.Semaphore(5)
        updated_count = 0
        fallback_count = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            for idx, (job_id, apply_url) in enumerate(jobs, 1):
                match = re.search(r"[-/](\d+)(?:\.html|\?|$)", apply_url)
                if not match:
                    continue
                num_id = match.group(1)

                canonical_url = None
                async with semaphore:
                    try:
                        ajax_url = f"https://itnavi.com.vn/ajax/get-job-by-id/{num_id}"
                        resp = await client.get(ajax_url, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json().get("data", {})
                            slug = data.get("job_slug")
                            if slug:
                                canonical_url = slug if slug.startswith("http") else f"https://itnavi.com.vn{slug}"
                    except Exception as e:
                        logger.debug(f"Lỗi gọi AJAX job {num_id}: {e}")

                if not canonical_url:
                    canonical_url = f"https://itnavi.com.vn/job-detail/{num_id}"
                    fallback_count += 1
                else:
                    updated_count += 1

                await session.execute(
                    text("UPDATE jobs SET apply_url = :new_url WHERE id = :jid"),
                    {"new_url": canonical_url, "jid": job_id},
                )
                await session.execute(
                    text("UPDATE raw_jobs SET source_url = :new_url WHERE source_url = :old_url"),
                    {"new_url": canonical_url, "old_url": apply_url},
                )

                if idx % 25 == 0 or idx == len(jobs):
                    await session.commit()
                    logger.info(f"Đã xử lý {idx}/{len(jobs)} tin (Thành công qua AJAX: {updated_count}, Fallback: {fallback_count})...")

        await session.commit()
        logger.info(f"✅ Hoàn tất sửa URL ITNavi! Tổng: {len(jobs)} tin. AJAX: {updated_count}, Fallback: {fallback_count}")


if __name__ == "__main__":
    asyncio.run(fix_all_itnavi_urls())
