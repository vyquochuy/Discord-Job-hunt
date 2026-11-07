"""Read-only smoke check against the configured DB: python scripts/check_market_analytics.py."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.api.v1.endpoints.market import router
from app.core.database import engine


async def main():
    app = FastAPI()
    app.include_router(router, prefix='/market')
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://local') as client:
            for endpoint in ('filters', 'overview', 'hiring-trends', 'salaries', 'skills', 'roles', 'geography', 'employers', 'insights'):
                response = await client.get('/market/' + endpoint)
                assert response.status_code == 200, (endpoint, response.status_code)
                data = response.json()
                meta = data.get('meta', {})
                print(endpoint, meta.get('total_jobs', data.get('total_jobs')), meta.get('status', 'catalog'))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
