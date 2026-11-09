"""Compose must finish the frontend build before importing backend static routes."""
from pathlib import Path

import yaml


def test_frontend_build_gates_backend_startup():
    compose = yaml.safe_load((Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    builder = services["frontend-build"]
    assert builder["image"] == "node:22-alpine"
    assert "npm ci && npm run build" in builder["command"]
    assert "./frontend:/frontend" in builder["volumes"]
    assert "frontend_node_modules:/frontend/node_modules" in builder["volumes"]
    assert services["backend"]["depends_on"]["frontend-build"]["condition"] == "service_completed_successfully"
    assert "./frontend:/frontend:ro" in services["backend"]["volumes"]
    assert "frontend_node_modules" in compose["volumes"]
