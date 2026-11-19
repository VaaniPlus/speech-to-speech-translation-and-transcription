"""Tests for local account authentication."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def make_client(tmp_path) -> TestClient:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        jwt_secret_key="test-secret-key-with-at-least-32-chars",
        seed_default_user=False,
    )
    return TestClient(create_app(settings))


def test_register_login_and_current_user(tmp_path) -> None:
    with make_client(tmp_path) as client:
        registration = client.post(
            "/api/auth/register",
            json={"email": "User@Example.com", "password": "password123"},
        )

        assert registration.status_code == 201
        body = registration.json()
        assert body["user"] == {"id": 1, "email": "user@example.com"}
        assert body["token_type"] == "bearer"

        current_user = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        login = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        )

    assert current_user.status_code == 200
    assert current_user.json() == {"id": 1, "email": "user@example.com"}
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "user@example.com"


def test_auth_rejects_duplicate_and_invalid_credentials(tmp_path) -> None:
    with make_client(tmp_path) as client:
        payload = {"email": "user@example.com", "password": "password123"}
        assert client.post("/api/auth/register", json=payload).status_code == 201

        duplicate = client.post("/api/auth/register", json=payload)
        wrong_password = client.post(
            "/api/auth/login",
            json={"email": payload["email"], "password": "wrongpass"},
        )
        missing_token = client.get("/api/auth/me")

    assert duplicate.status_code == 409
    assert wrong_password.status_code == 401
    assert missing_token.status_code == 401


def test_default_proindra_account_can_sign_in(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'default-user.db'}",
        jwt_secret_key="test-secret-key-with-at-least-32-chars",
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/auth/login",
            json={
                "email": "proindra@example.com",
                "password": "VaaniProindra#2026",
            },
        )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "proindra@example.com"
