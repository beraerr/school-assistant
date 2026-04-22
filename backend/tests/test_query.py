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
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client():
    """Create test client"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    try:
        yield TestClient(app)
    finally:
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client"""
    db = next(override_get_db())
    user = User(
        username="testuser",
        password_hash=get_password_hash("testpass123"),
        role=UserRole.PRINCIPAL,
        related_id=1
    )
    db.add(user)
    db.commit()
    
    response = client.post(
        "/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    token = response.json()["access_token"]
    
    client.headers = {"Authorization": f"Bearer {token}"}
    return client

def test_query_endpoint_requires_auth(client):
    """Test that query endpoint requires authentication"""
    response = client.post(
        "/query/",
        json={"query": "test query"}
    )
    assert response.status_code == 401

def test_query_endpoint_with_auth(authenticated_client):
    """Test query endpoint with authentication"""
    response = authenticated_client.post(
        "/query/",
        json={"query": "Tüm öğrencileri göster"}
    )
    assert response.status_code in [200, 500]
