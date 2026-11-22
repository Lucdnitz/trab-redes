import socket

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


def test_stream_sends_control_events_and_udp_packet() -> None:
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    receiver.settimeout(2.0)
    udp_port = receiver.getsockname()[1]

    try:
        with TestClient(app, client=("127.0.0.1", 50_000)) as client, client.websocket_connect(
            "/ws"
        ) as websocket:
            websocket.send_json({"type": "register", "udp_port": udp_port})
            assert websocket.receive_json()["type"] == "registered"

            response = client.post(
                "/api/v1/stream/start",
                json={"codec": "pcm", "enable_transcription": False},
            )
            assert response.status_code == 202
            assert response.json()["accepted"] is True
            assert websocket.receive_json()["type"] == "stream_started"

            datagram, _address = receiver.recvfrom(2_048)
            assert datagram.startswith(b"RA")

            assert client.post("/api/v1/stream/stop").status_code == 200
            assert websocket.receive_json()["type"] == "stream_ended"
    finally:
        receiver.close()
