
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_home_page(client):
    response = client.get("/")
    assert response.status_code in (200, 302)


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200


def test_invalid_login(client):
    response = client.post(
        "/login",
        data={
            "username": "wronguser",
            "password": "wrongpassword"
        },
        follow_redirects=True
    )
    assert response.status_code == 200


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code in (302, 401, 403)
