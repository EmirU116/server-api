"""Server service unit tests and HTTP contract tests use fake host metadata."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.services.errors import UnknownServer
from app.services.server import ServerInfoUnavailable, ServerService, read_host_info

HOST = {
    "hostname": "test-server",
    "os_type": "Linux",
    "os_name": "Ubuntu",
    "os_version": "24.04",
    "architecture": "x86_64",
}


@pytest.fixture
def host(monkeypatch):
    monkeypatch.setattr("app.services.server.read_host_info", lambda: HOST.copy())


@pytest.fixture
def authorized(app):
    app.state.reader_token = SecretStr("dummy-reader-token")
    return {"Authorization": "Bearer dummy-reader-token"}


def test_service_returns_configured_identity_and_host_metadata(host):
    info = ServerService(1, "Test server").get_info()

    assert info.model_dump() == {"id": 1, "name": "Test server", **HOST}


def test_native_linux_metadata_uses_distribution_not_kernel(monkeypatch):
    monkeypatch.setattr("app.services.server.Path.exists", lambda path: False)
    monkeypatch.setattr("app.services.server.platform.system", lambda: "Linux")
    monkeypatch.setattr("app.services.server.platform.node", lambda: "test-server")
    monkeypatch.setattr("app.services.server.platform.machine", lambda: "x86_64")
    monkeypatch.setattr(
        "app.services.server.platform.release", lambda: "kernel-version"
    )
    monkeypatch.setattr(
        "app.services.server.platform.freedesktop_os_release",
        lambda: {"NAME": "Ubuntu", "VERSION_ID": "24.04"},
    )

    assert read_host_info() == HOST


def test_native_windows_metadata_does_not_read_linux_files(monkeypatch):
    monkeypatch.setattr("app.services.server.Path.exists", lambda path: False)
    monkeypatch.setattr("app.services.server.platform.system", lambda: "Windows")
    monkeypatch.setattr("app.services.server.platform.node", lambda: "windows-host")
    monkeypatch.setattr("app.services.server.platform.machine", lambda: "AMD64")
    monkeypatch.setattr("app.services.server.platform.release", lambda: "11")

    assert read_host_info() == {
        "hostname": "windows-host",
        "os_type": "Windows",
        "os_name": "Windows",
        "os_version": "11",
        "architecture": "AMD64",
    }


def test_container_metadata_is_not_reported_as_host(monkeypatch):
    monkeypatch.setattr("app.services.server.Path.exists", lambda path: True)

    with pytest.raises(ServerInfoUnavailable):
        read_host_info()


def test_server_get_returns_only_identity_fields(app, client, host, authorized):
    response = client.get("/api/v1/server", headers=authorized)

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "ServerWatch server", **HOST}
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/server", headers=authorized).json() == response.json()


def test_configured_server_id_is_shared_with_health(host):
    settings = Settings(
        server_id=7,
        server_name="Configured host",
        reader_token=SecretStr("dummy-reader-token"),
    )
    with TestClient(create_app(settings)) as client:
        server = client.get(
            "/api/v1/server", headers={"Authorization": "Bearer dummy-reader-token"}
        )
        health = client.get("/api/v1/health?server_id=7")

    assert server.status_code == 200
    assert server.json()["name"] == "Configured host"
    assert server.json()["id"] == health.json()["server_id"] == 7
    assert health.status_code == 503  # Database is still deliberately unconfigured.


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Basic dummy"}, {"Authorization": "Bearer wrong-token"}],
)
def test_missing_or_invalid_authentication_returns_401(
    client, host, authorized, headers
):
    response = client.get("/api/v1/server", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "unauthorized"


def test_missing_reader_configuration_fails_closed(app, client, host):
    app.state.reader_token = None
    response = client.get("/api/v1/server", headers={"Authorization": "Bearer dummy"})

    assert response.status_code == 503


@pytest.mark.parametrize(
    "url,body",
    [
        ("/api/v1/server?verbose=true", None),
        ("/api/v1/server", b"{}"),
        ("/api/v1/server", b" "),
    ],
)
def test_unsupported_inputs_return_422(client, authorized, url, body):
    response = client.request("GET", url, content=body, headers=authorized)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
)
def test_server_accepts_get_only(client, method):
    response = client.request(method, "/api/v1/server")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"


@pytest.mark.parametrize("field", list(HOST))
def test_missing_host_information_returns_503(monkeypatch, client, authorized, field):
    metadata = HOST.copy()
    metadata[field] = " "
    monkeypatch.setattr("app.services.server.read_host_info", lambda: metadata)

    response = client.get("/api/v1/server", headers=authorized)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


@pytest.mark.parametrize("error,status", [(OSError, 503), (RuntimeError, 500)])
def test_host_failures_are_sanitized(
    monkeypatch, client, authorized, caplog, error, status
):
    def failed_source():
        raise error("dummy-sensitive-host-path")

    monkeypatch.setattr("app.services.server.read_host_info", failed_source)
    response = client.get("/api/v1/server", headers=authorized)

    assert response.status_code == status
    assert "dummy-sensitive" not in response.text
    assert "dummy-sensitive" not in caplog.text


@pytest.mark.parametrize("server_id", ["1", "+1", " 1 ", "01"])
def test_optional_server_id_returns_matching_server(
    client, host, authorized, server_id
):
    response = client.get(
        "/api/v1/server", params={"server_id": server_id}, headers=authorized
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1


@pytest.mark.parametrize("server_id", ["-1", "0", "abc", "1.5", "", " "])
def test_invalid_server_id_returns_400(client, authorized, server_id):
    response = client.get(
        "/api/v1/server", params={"server_id": server_id}, headers=authorized
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_duplicate_server_ids_return_400(client, authorized):
    response = client.get("/api/v1/server?server_id=1&server_id=2", headers=authorized)

    assert response.status_code == 400


def test_unknown_server_returns_404_before_reading_host(
    monkeypatch, client, authorized
):
    def unexpected_read():
        pytest.fail("An unknown server must not read local host metadata")

    monkeypatch.setattr("app.services.server.read_host_info", unexpected_read)
    response = client.get("/api/v1/server?server_id=2", headers=authorized)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_service_selects_configured_server(host):
    service = ServerService(7, "Configured host")

    assert service.get_info(7).id == 7
    assert service.get_info().id == 7
    with pytest.raises(UnknownServer):
        service.get_info(1)


def test_selected_server_metadata_failure_returns_503(monkeypatch, client, authorized):
    def unavailable():
        raise OSError("dummy-sensitive-path")

    monkeypatch.setattr("app.services.server.read_host_info", unavailable)
    response = client.get("/api/v1/server?server_id=1", headers=authorized)

    assert response.status_code == 503
    assert "dummy-sensitive" not in response.text
