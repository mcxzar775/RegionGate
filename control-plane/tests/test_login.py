from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_invalid():
    r = client.post("/api/v1/auth/login", json={"username": "nope", "password": "bad"})
    assert r.status_code == 401
