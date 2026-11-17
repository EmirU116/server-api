"""Smoke tests for application startup and documentation exposure."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_openapi_describes_only_the_implemented_health_endpoint(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ServerWatch tests"
    paths = response.json()["paths"]
    assert set(paths) == {"/api/v1/health"}
    assert set(paths["/api/v1/health"]) == {"get"}
    operation = paths["/api/v1/health"]["get"]
    assert {"200", "400", "404", "422", "503"} <= set(operation["responses"])
    assert operation["parameters"][0]["name"] == "server_id"
    assert operation["parameters"][0]["required"] is True


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_interactive_documentation_is_available(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_production_disables_documentation(path):
    app = create_app(Settings(environment="production"))

    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
