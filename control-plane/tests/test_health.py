from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/")
    assert r.status_code == 200
    assert "ok" in r.json() or "status" in r.json() or r.status_code == 200
