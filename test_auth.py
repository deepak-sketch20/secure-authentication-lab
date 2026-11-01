import pytest
from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-not-for-production",
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "SESSION_COOKIE_SECURE": True,
        "RATELIMIT_ENABLED": False,
    })


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, username="student01", password="correct-horse-battery"):
    return client.post("/register", data={"username": username, "password": password})


def test_valid_login_and_protected_dashboard(client):
    assert register(client).status_code == 302
    response = client.post("/login", data={"username": "student01", "password": "correct-horse-battery"})
    assert response.status_code == 302
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert b"student01" in page.data


def test_generic_error_for_unknown_and_wrong_password(client):
    register(client)
    wrong = client.post("/login", data={"username": "student01", "password": "wrong-password"})
    unknown = client.post("/login", data={"username": "nobody01", "password": "wrong-password"})
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert b"Invalid username or password." in wrong.data
    assert b"Invalid username or password." in unknown.data


def test_invalid_session_cannot_open_dashboard(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.location


def test_logout_clears_session(client):
    register(client)
    client.post("/login", data={"username": "student01", "password": "correct-horse-battery"})
    assert client.get("/dashboard").status_code == 200
    client.post("/logout")
    assert client.get("/dashboard").status_code == 302


def test_password_validation(client):
    response = register(client, password="short")
    assert response.status_code == 400
    assert b"between 10 and 128" in response.data


def test_session_cookie_security_flags(client):
    register(client)
    client.post("/login", data={"username": "student01", "password": "correct-horse-battery"})
    cookie = client.get_cookie("session")
    assert cookie is not None
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"] == "Lax"
