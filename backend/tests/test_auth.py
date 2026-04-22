import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app import models as _models  # noqa: F401 — register metadata
from backend.app.models.user import User, UserRole
from backend.app.core.security import get_password_hash

SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/school_test_db",
)
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    try:
        yield TestClient(app)
    finally:
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def test_user(client):
    db = next(override_get_db())
    user = User(
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.STUDENT,
        related_id=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_login_success(client, test_user):
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_failure(client, test_user):
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401
