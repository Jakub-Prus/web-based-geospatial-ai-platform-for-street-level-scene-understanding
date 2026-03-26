from fastapi.testclient import TestClient

from app.main import SERVICE_NAME, SERVICE_STATUS, app


def test_health_endpoint_reports_service_metadata() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == SERVICE_NAME
    assert response.json()["status"] == SERVICE_STATUS
