import pytest
from fastapi import Response
from httpx import AsyncClient

from app.api.v1 import health


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"
    assert "version" in body["data"]
    assert "environment" in body["data"]


@pytest.mark.asyncio
async def test_health_check_detailed(client: AsyncClient):
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "dependencies" in body["data"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("database_ok", "redis_ok", "isolation_ok", "expected_status"),
    [(True, True, True, 200), (False, True, True, 503), (True, False, True, 503), (True, True, False, 503)],
)
async def test_production_readiness(
    monkeypatch, database_ok, redis_ok, isolation_ok, expected_status,
):
    async def database_check():
        return database_ok

    async def redis_check():
        return redis_ok

    async def isolation_check():
        return isolation_ok

    monkeypatch.setattr(health.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(health, "check_db_connection", database_check)
    monkeypatch.setattr(health, "check_redis_connection", redis_check)
    monkeypatch.setattr(health, "check_tenant_isolation", isolation_check)
    response = Response()

    body = await health.readiness_check(response)

    assert response.status_code == expected_status
    assert body.success == (expected_status == 200)
    assert body.data["dependencies"] == {
        "database": "ok" if database_ok else "error",
        "redis": "ok" if redis_ok else "error",
        "tenant_isolation": "ok" if database_ok and isolation_ok else "error",
    }


@pytest.mark.asyncio
async def test_response_envelope_format(client: AsyncClient):
    response = await client.get("/api/v1/health")
    body = response.json()
    assert "success" in body
    assert "data" in body
    assert "message" in body


@pytest.mark.asyncio
async def test_404_error_format(client: AsyncClient):
    response = await client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
