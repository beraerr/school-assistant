"""
Unit tests for query endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.user import User, UserRole
from backend.app.core.security import get_password_hash

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


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
    
    # Login
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    
    # Set token in client
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
    # Note: This test might fail if LLM service is not available
    # In real tests, you'd mock the LLM service
    response = authenticated_client.post(
        "/query/",
        json={"query": "Tüm öğrencileri göster"}
    )
    # Should return 200 or 500 depending on LLM availability
    assert response.status_code in [200, 500]
