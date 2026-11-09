"""Read-only live collector probe; never writes to the database.

Run from repo root: .venv/Scripts/python scripts/check_collectors.py
Optional positional arguments select sources; defaults to the seven VN sources.
"""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.collectors.careerlink_adapter import CareerLinkJobCollector
from app.services.collectors.growupwork_adapter import GrowUpWorkJobCollector
from app.services.collectors.itnavi_adapter import ITNaviJobCollector
from app.services.collectors.itviec_adapter import ITViecJobCollector
from app.services.collectors.saramin_adapter import SaraminJobCollector
from app.services.collectors.topcv_adapter import TopCVJobCollector
from app.services.collectors.vietnamworks_adapter import VietnamWorksJobCollector


async def main():
    collectors = [cls() for cls in (
        ITViecJobCollector, TopCVJobCollector, SaraminJobCollector,
        VietnamWorksJobCollector, CareerLinkJobCollector,
        ITNaviJobCollector, GrowUpWorkJobCollector,
    )]
    requested = set(sys.argv[1:])
    unknown = requested - {collector.source_name for collector in collectors}
    if unknown:
        raise SystemExit(f"Unknown sources: {', '.join(sorted(unknown))}")

    async def probe(collector):
        try:
            jobs = await asyncio.wait_for(collector.fetch_jobs(limit=0), timeout=240)
            ids = {job.source_job_id or job.source_url for job in jobs}
            return {"source": collector.source_name, "fetched": len(jobs),
                    "unique": len(ids), "status": "ok" if jobs else "empty"}
        except Exception as exc:
            return {"source": collector.source_name,
                    "status": "blocked" if "BLOCKED:" in str(exc) else "failed",
                    "error_type": type(exc).__name__}

    results = await asyncio.gather(*(probe(c) for c in collectors
                                     if not requested or c.source_name in requested))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(result["status"] != "ok" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
