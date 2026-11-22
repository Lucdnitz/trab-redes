from fastapi.testclient import TestClient

from redes_audio.server.app import app


def test_healthcheck() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_requires_registered_client() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/demo/start")

    assert response.status_code == 202
    assert response.json() == {"accepted": False, "clients": 0}


def test_session_exposes_empty_incremental_summary() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {
        "text": "",
        "through_sequence": -1,
        "through_ms": 0,
    }
    assert "public_key" in payload


def test_tamper_endpoint_accepts_request() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/demo/tamper")

    assert response.status_code == 202
    assert response.json()["sent"] is True


def test_upload_rejects_empty_body() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/stream/upload?filename=palestra.wav&codec=opus",
            content=b"",
        )

    assert response.status_code == 400
