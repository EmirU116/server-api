"""Smoke tests for application startup and documentation exposure."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_openapi_describes_the_implemented_endpoints(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ServerWatch tests"
    paths = response.json()["paths"]
    assert set(paths) == {
        "/api/v1/health",
        "/api/v1/server",
        "/api/v1/metrics",
        "/api/v1/incidents",
        "/api/v1/incidents/{incident_id}",
    }
    assert set(paths["/api/v1/incidents"]) == {"get", "post"}
    assert set(paths["/api/v1/incidents/{incident_id}"]) == {"get", "patch", "delete"}
    assert set(paths["/api/v1/metrics"]) == {"get", "post"}
    assert set(paths["/api/v1/server"]) == {"get"}
    server_operation = paths["/api/v1/server"]["get"]
    assert {"400", "404"} <= set(server_operation["responses"])
    assert server_operation["parameters"][0]["name"] == "server_id"
    assert server_operation["parameters"][0]["required"] is False
    assert {"200", "401", "422", "500", "503"} <= set(
        paths["/api/v1/server"]["get"]["responses"]
    )
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


def test_production_can_opt_in_to_swagger_and_openapi():
    app = create_app(Settings(environment="production", expose_api_docs=True))

    with TestClient(app) as client:
        docs = client.get("/docs")
        assert docs.status_code == 200
        assert "/openapi.json" in docs.text
        assert "/api/v1/health" in client.get("/openapi.json").json()["paths"]
        assert client.get("/redoc").status_code == 404
