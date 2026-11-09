import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings
from app.core.limiter import get_client_ip


@pytest.mark.parametrize("headers, expected", [
    ([(b"cf-connecting-ip", b"203.0.113.10"),
      (b"x-forwarded-for", b"198.51.100.99, 192.0.2.1")], "203.0.113.10"),
    ([(b"x-forwarded-for", b"198.51.100.99, 192.0.2.1")], "198.51.100.99"),
    ([], "192.0.2.20"),
])
def test_client_ip_header_priority(headers, expected):
    request = Request({"type": "http", "headers": headers, "client": ("192.0.2.20", 1234)})
    assert get_client_ip(request) == expected


@pytest.mark.parametrize("environment", ["production", "staging", "test", "preview", "", " Production "])
@pytest.mark.parametrize("field, weak", [
    ("JWT_SECRET_KEY", "short"),
    ("INTERNAL_API_SECRET", "short"),
    ("JWT_SECRET_KEY", "job_hunter_platform_secret_key_web_2026_flexible_auth"),
    ("INTERNAL_API_SECRET", "change_me_to_a_secure_random_string_32_chars"),
])
def test_non_development_rejects_weak_secrets(monkeypatch, environment, field, weak):
    # Explicit settings must win over a development process environment.
    monkeypatch.setenv("ENVIRONMENT", "development")
    values = dict(ENVIRONMENT=environment, JWT_SECRET_KEY="a" * 40, INTERNAL_API_SECRET="b" * 40)
    values[field] = weak
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


@pytest.mark.parametrize("environment", ["development", " Development ", "production", "staging"])
def test_environment_accepts_appropriate_secrets(monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", "production")
    development = environment.strip().lower() == "development"
    secret = "short" if development else "strong-test-secret-" + "x" * 32
    config = Settings(_env_file=None, ENVIRONMENT=environment,
                      JWT_SECRET_KEY=secret, INTERNAL_API_SECRET=secret)
    assert config.JWT_SECRET_KEY == secret
