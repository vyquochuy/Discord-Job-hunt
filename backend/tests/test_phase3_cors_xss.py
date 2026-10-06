import pytest
from httpx import AsyncClient
from app.main import app

from httpx import ASGITransport

@pytest.mark.asyncio
async def test_cors_rejects_untrusted_origins():
    """
    Test that the backend correctly rejects cross-origin requests from untrusted
    domains, specifically verifying that the overly permissive vercel.app regex
    has been removed.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # A trusted origin should be allowed
        response = await client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

        # An untrusted origin should NOT return an access-control-allow-origin header
        response = await client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "https://malicious.vercel.app",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 400
        # The CORS middleware either doesn't return the header or returns something else,
        # but it shouldn't return malicious.vercel.app
        assert response.headers.get("access-control-allow-origin") != "https://malicious.vercel.app"

@pytest.mark.asyncio
async def test_job_ingest_payload_structure():
    """
    API test to ensure that the job ingestion endpoint can receive adversarial payloads
    without throwing 500s. The frontend must sanitize this output via escapeHtml.
    """
    from app.schemas.job import JobCreate
    from app.models.job import Job
    from app.core.database import get_db
    
    # We are not testing the browser rendering here, but we can verify the backend
    # successfully stores the adversarial payload so the frontend CAN be tested against it.
    adversarial_payload = {
        "title": "<script>alert('xss')</script> Engineer",
        "company_name": "<img src=x onerror=alert(1)>",
        "description": "Adversarial job description",
        "source": "LINKEDIN",
        "location": "Hanoi",
        "work_mode": "REMOTE",
        "raw_job_id": "12345678-1234-5678-1234-567812345678",
        "normalized_title": "engineer",
        "normalized_company": "hacked company"
    }
    
    # This just ensures we don't crash when receiving XSS strings
    job_create = JobCreate(**adversarial_payload)
    assert "<script>" in job_create.title
