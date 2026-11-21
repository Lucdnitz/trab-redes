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
