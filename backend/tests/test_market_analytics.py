"""Isolated market API checks: no network, credentials or production database."""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 -- register relationship targets
from app.api.v1.endpoints.market import router
from app.core.database import Base, get_db
from app.models.job import Job, RawJob, Skill, JobSkill, JobStatusEnum
from app.services.analytics.stats import salary_vnd


@pytest_asyncio.fixture
async def market_client():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router, prefix='/market')

    async def db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = db
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client, sessions
    await engine.dispose()


async def seed(sessions):
    async with sessions() as db:
        skill = Skill(canonical_name='Python')
        db.add(skill)
        for index in range(4):
            raw = RawJob(source='itviec', source_url=f'https://example.com/{index}', content_hash=str(index))
            db.add(raw)
            await db.flush()
            job = Job(raw_job_id=raw.id, title='Backend Developer', normalized_title='Backend Developer',
                      company_name='Example', normalized_company='Example', normalized_location='Hanoi',
                      description='Python', posted_at=datetime(2026, 11, index + 1, tzinfo=timezone.utc),
                      min_salary=100 if index == 0 else None, max_salary=200 if index == 0 else None,
                      salary_currency='USD' if index == 0 else None,
                      status=[JobStatusEnum.ACTIVE, JobStatusEnum.ACTIVE, JobStatusEnum.EXPIRED, JobStatusEnum.MERGED][index])
            db.add(job)
            await db.flush()
            db.add(JobSkill(job_id=job.id, skill_id=skill.id))
        await db.commit()


@pytest.mark.asyncio
async def test_modules_empty_and_populated(market_client):
    client, sessions = market_client
    endpoints = ['overview', 'hiring-trends', 'salaries', 'skills', 'roles', 'geography', 'employers', 'insights']
    for endpoint in endpoints:
        response = await client.get(f'/market/{endpoint}')
        assert response.status_code == 200, response.text
        assert response.json()['meta']['status'] == 'empty'
    await seed(sessions)
    for endpoint in endpoints:
        response = await client.get(f'/market/{endpoint}')
        assert response.status_code == 200, response.text
        assert response.json()['meta']['total_jobs'] == 2
        response = await client.get(f'/market/{endpoint}?include_expired=true')
        assert response.json()['meta']['total_jobs'] == 3
    salary = (await client.get('/market/salaries')).json()
    assert salary['coverage']['with_salary'] == 1
    assert salary['normalized_vnd']['estimated'] is True
    assert salary['native'][0]['median'] == 150
    # Legacy shape must never mix USD amounts into its VND-only summary.
    legacy = (await client.get('/market/analytics')).json()
    assert legacy['salary']['max'] is None
    assert (await client.get('/market/employers')).json()['new_entrants'] == []
    skills = (await client.get('/market/skills')).json()
    assert skills['top_skills'][0]['jobs'] == 2
    assert skills['top_skills'][0]['share'] == 1
    assert (await client.get('/market/filters')).status_code == 200
    assert (await client.get('/market/analytics')).status_code == 200


@pytest.mark.asyncio
async def test_filters_and_validation(market_client):
    client, sessions = market_client
    await seed(sessions)
    for query in ['date_from=2026-12-01&date_to=2026-01-01', 'level=bad', 'category=bad', 'work_mode=bad', 'region=bad']:
        assert (await client.get('/market/overview?' + query)).status_code == 422
    for query in ['location=missing', 'skill=missing', 'company=missing', 'source=missing', 'category=data']:
        assert (await client.get('/market/overview?' + query)).json()['totals']['jobs'] == 0
    response = await client.get('/market/hiring-trends?date_from=2026-11-02&date_to=2026-11-02')
    assert response.json()['series'][0]['jobs'] == 1
    assert (await client.get('/market/skills?skill_category=bad')).status_code == 422
    assert (await client.get('/market/overview?skill=Python')).json()['totals']['jobs'] == 2
    assert (await client.get('/market/overview?location=Hanoi')).json()['totals']['jobs'] == 2
    assert (await client.get('/market/overview?company=Example')).json()['totals']['jobs'] == 2
    assert (await client.get('/market/skills?search=missing')).json()['top_skills'] == []
    assert (await client.get('/market/hiring-trends?granularity=bad')).status_code == 422


@pytest.mark.parametrize('low,high', [(float('nan'), 20), (10, float('inf')), (-10, 20), (30, 20), (0, 0)])
def test_invalid_salary_excluded(low, high):
    assert salary_vnd(low, high, 'VND') is None


@pytest.mark.asyncio
async def test_missing_post_dates_do_not_break_employers(market_client):
    from sqlalchemy import update
    client, sessions = market_client
    await seed(sessions)
    async with sessions() as db:
        await db.execute(update(Job).values(posted_at=None))
        await db.commit()
    for endpoint in ('employers', 'hiring-trends', 'insights'):
        response = await client.get('/market/' + endpoint)
        assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_api_date_boundaries(market_client):
    client, _ = market_client
    for query in ('date_to=9999-12-31', 'date_from=0001-01-01', 'date_from=2000-01-01&date_to=2026-01-01'):
        assert (await client.get('/market/hiring-trends?' + query)).status_code == 422


def test_percentile_and_spike_observations():
    from datetime import date
    from app.services.analytics.stats import percentile
    from app.services.analytics.buckets import detect_bulk_spikes
    assert percentile([10, 20, 30, 40], 0.5) == 25
    assert percentile([], 0.5) is None
    spikes = detect_bulk_spikes([date(2026, 11, 1)] * 2 + [date(2026, 11, 2)] * 3 + [date(2026, 11, 3)] * 100)
    assert spikes[0]['jobs'] == 100
    from app.services.analytics.taxonomy import derive_category, derive_region
    assert derive_category('Embedded Python Engineer') == 'embedded'
    assert derive_category('React Native Developer') == 'mobile'
    assert derive_region('Hanoi') == 'hanoi'
    assert derive_region(None) == 'unknown'


MARKET_SOURCES = ('itviec', 'topcv', 'saramin', 'topdev', 'vietnamworks', 'careerlink', 'itnavi', 'growupwork')
EXCLUDED_SOURCES = ('remotive', 'upwork', 'mock', 'manual', 'unknown')


@pytest_asyncio.fixture
async def mixed_market(market_client):
    client, sessions = market_client
    async with sessions() as db:
        records = [(source, 'growupwork-real-123' if source == 'growupwork' else None)
                   for source in MARKET_SOURCES + EXCLUDED_SOURCES]
        records.append(('growupwork', 'growupwork-curated-backend-developer-1'))
        for source, source_job_id in records:
            record_key = source_job_id if source_job_id and source_job_id.startswith('growupwork-curated-') else source
            skill = Skill(canonical_name=record_key)
            db.add(skill)
            for status in (JobStatusEnum.ACTIVE, JobStatusEnum.EXPIRED):
                raw = RawJob(source=source, source_job_id=source_job_id,
                             source_url=f'https://example.com/{record_key}/{status.value}',
                             content_hash=f'{record_key}-{status.value}')
                db.add(raw)
                await db.flush()
                job = Job(raw_job_id=raw.id, title='Backend Developer', normalized_title='Backend Developer',
                          company_name=source, normalized_company=source, normalized_location='Hanoi',
                          description='Python', posted_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                          min_salary=10 if source in MARKET_SOURCES else 1000,
                          max_salary=20 if source in MARKET_SOURCES else 2000,
                          salary_currency='VND', status=status)
                db.add(job)
                await db.flush()
                db.add(JobSkill(job_id=job.id, skill_id=skill.id))
        await db.commit()
    return client


@pytest.mark.asyncio
@pytest.mark.parametrize('endpoint', ['overview', 'hiring-trends', 'salaries', 'skills', 'roles', 'geography', 'employers', 'insights'])
async def test_market_source_whitelist(mixed_market, endpoint):
    for include_expired, expected in [('false', 8), ('true', 16)]:
        response = await mixed_market.get(f'/market/{endpoint}?include_expired={include_expired}')
        assert response.status_code == 200, response.text
        assert response.json()['meta']['total_jobs'] == expected
    growupwork = await mixed_market.get(f'/market/{endpoint}?source=growupwork&include_expired=true')
    assert growupwork.json()['meta']['total_jobs'] == 2
    for source in EXCLUDED_SOURCES:
        response = await mixed_market.get(f'/market/{endpoint}?source={source}&include_expired=true')
        assert response.json()['meta']['total_jobs'] == 0


@pytest.mark.asyncio
async def test_catalog_and_legacy_source_whitelist(mixed_market):
    catalog = (await mixed_market.get('/market/filters')).json()
    assert {item['value'] for item in catalog['sources']} == set(MARKET_SOURCES)
    assert {item['value'] for item in catalog['skills']} == set(MARKET_SOURCES)


@pytest.mark.asyncio
async def test_legacy_source_whitelist(mixed_market):
    legacy = (await mixed_market.get('/market/analytics')).json()
    assert legacy['total_active_jobs'] == 8
    assert legacy['total_expired_jobs'] == 8
    assert {item['source'] for item in legacy['sources']} == set(MARKET_SOURCES)
    assert {item['skill'] for item in legacy['top_skills']} == set(MARKET_SOURCES)
    assert legacy['salary'] == {'min': 10, 'average_max': 20, 'max': 20}


def test_unknown_currency_never_assumed():
    assert salary_vnd(10, 20, None) is None
    assert salary_vnd(10, 20, 'EUR') is None
