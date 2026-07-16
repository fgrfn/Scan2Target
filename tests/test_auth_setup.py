"""Authentication setup and session regression tests."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCAN2TARGET_DATABASE_PATH", str(tmp_path / "scan2target.db"))
    monkeypatch.setenv("SCAN2TARGET_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SCAN2TARGET_JWT_SECRET", "test-jwt-secret-that-is-long-and-stable")

    from core.config.settings import get_settings
    import core.auth.manager as auth_manager_module
    import core.config.runtime as runtime_module
    import core.database as database_module

    get_settings.cache_clear()
    database_module._db_instance = None
    auth_manager_module._auth_manager = None
    runtime_module._runtime_config = None

    from api.auth import router, _login_failures

    _login_failures.clear()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return TestClient(app), auth_manager_module


def test_first_user_setup_is_one_time_and_admin(tmp_path, monkeypatch):
    client, _ = _build_client(tmp_path, monkeypatch)

    assert client.get("/api/v1/auth/setup-status").json() == {"setup_required": True}

    weak = client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "short", "email": None},
    )
    assert weak.status_code == 422

    created = client.post(
        "/api/v1/auth/setup",
        json={
            "username": "admin",
            "password": "SecurePassword123",
            "email": "admin@example.invalid",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["user"]["is_admin"] is True
    assert payload["access_token"]

    assert client.get("/api/v1/auth/setup-status").json() == {"setup_required": False}
    assert client.post(
        "/api/v1/auth/setup",
        json={"username": "other", "password": "SecurePassword456"},
    ).status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "SecurePassword123"},
    )
    assert login.status_code == 200


def test_jwt_secret_survives_auth_manager_recreation(tmp_path, monkeypatch):
    client, auth_manager_module = _build_client(tmp_path, monkeypatch)
    created = client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "SecurePassword123"},
    )
    token = created.json()["access_token"]

    auth_manager_module._auth_manager = None
    assert auth_manager_module.get_auth_manager().verify_token(token) is not None


def test_admin_can_manage_account_and_runtime_auth(tmp_path, monkeypatch):
    client, _ = _build_client(tmp_path, monkeypatch)
    created = client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "SecurePassword123", "email": None},
    )
    token = created.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/auth/config").json()["enabled"] is True
    disabled = client.put(
        "/api/v1/auth/config", json={"enabled": False}, headers=headers
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    updated = client.patch(
        "/api/v1/auth/account",
        json={
            "current_password": "SecurePassword123",
            "username": "operator",
            "email": "operator@example.invalid",
            "new_password": "EvenSaferPassword456",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    rotated = updated.json()["access_token"]
    assert rotated != token
    assert updated.json()["user"]["username"] == "operator"
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "SecurePassword123"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "EvenSaferPassword456"},
    ).status_code == 200
