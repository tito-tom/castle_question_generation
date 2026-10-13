from fastapi.testclient import TestClient
from src.api.main import create_app

def test_health_check():

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": "castle-qa-studio-api",
    }

def test_health_endpoint_in_openapi():

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/health" in paths
    assert "get" in paths["/api/v1/health"]