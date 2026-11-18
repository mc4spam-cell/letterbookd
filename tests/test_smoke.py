from django.test import Client


def test_home_ok(db):
    response = Client().get("/")
    assert response.status_code == 200
    assert "Bienvenue" in response.content.decode()
