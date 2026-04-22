import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_db
from backend.app.core.security import get_password_hash
from backend.app.main import app
from backend.app.models.attendance import Attendance
from backend.app.models.grade import Grade
from backend.app.models.student import Student
from backend.app.models.user import User, UserRole
from backend.app.models.risk_score import StudentRiskScore

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

def _seed_data():
    db = next(override_get_db())
    principal = User(
        username="principal_test",
        password_hash=get_password_hash("admin123"),
        role=UserRole.PRINCIPAL,
    )
    teacher = User(
        username="teacher_test",
        password_hash=get_password_hash("teacher123"),
        role=UserRole.TEACHER,
        related_class="9-A",
    )
    db.add_all([principal, teacher])

    high = Student(name="High Risk", class_name="9-A", total_absences=10)
    low = Student(name="Low Risk", class_name="9-A", total_absences=1)
    other_class = Student(name="Other Class", class_name="10-B", total_absences=20)
    db.add_all([high, low, other_class])
    db.flush()

    today = date.today()
    db.add_all(
        [
            Attendance(student_id=high.id, date=today - timedelta(days=2), status="absent"),
            Attendance(student_id=high.id, date=today - timedelta(days=5), status="absent"),
            Attendance(student_id=high.id, date=today - timedelta(days=8), status="absent"),
            Attendance(student_id=low.id, date=today - timedelta(days=2), status="present"),
            Attendance(student_id=other_class.id, date=today - timedelta(days=2), status="absent"),
        ]
    )

    db.add_all(
        [
            Grade(student_id=high.id, subject="Matematik", grade=40, date=today - timedelta(days=30)),
            Grade(student_id=high.id, subject="Matematik", grade=30, date=today - timedelta(days=1)),
            Grade(student_id=low.id, subject="Matematik", grade=90, date=today - timedelta(days=30)),
            Grade(student_id=low.id, subject="Matematik", grade=92, date=today - timedelta(days=1)),
            Grade(student_id=other_class.id, subject="Matematik", grade=20, date=today - timedelta(days=1)),
        ]
    )
    db.add(
        StudentRiskScore(
            student_id=high.id,
            ml_risk_score=72.5,
            ml_risk_level="high",
            features_json="{}",
            computed_at=today,
        )
    )
    db.commit()

def _login(client: TestClient, username: str, password: str) -> str:
    res = client.post("/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_risk_endpoint_returns_ml_only_scores(client):
    _seed_data()
    token = _login(client, "principal_test", "admin123")

    res = client.get("/risk/students", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 3

    first_item = body["items"][0]
    assert 0 <= first_item["risk_score"] <= 100
    assert first_item["risk_level"] in ["low", "medium", "high", "unknown"]
    assert isinstance(first_item["explanation"], str)
    assert len(first_item["explanation"]) > 0
    high_row = next(i for i in body["items"] if i["student_name"] == "High Risk")
    assert high_row["ml_risk_score"] == 72.5
    assert high_row["ml_risk_level"] == "high"
    assert high_row.get("ml_computed_at")

def test_teacher_sees_only_own_class_risks(client):
    _seed_data()
    token = _login(client, "teacher_test", "teacher123")
    res = client.get("/risk/students", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    items = res.json()["items"]
    assert len(items) == 2
    assert all(item["class_name"] == "9-A" for item in items)
