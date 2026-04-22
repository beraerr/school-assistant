from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models as _models  # noqa: F401
from backend.app.core.database import Base
from backend.app.models.grade import Grade
from backend.app.models.student import Student
from backend.app.models.user import User, UserRole
from backend.app.services.query_shortcuts import try_parent_student_outlook_answer

@pytest.fixture
def outlook_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Sess = sessionmaker(bind=engine, future=True)
    db = Sess()
    try:
        db.add(Student(id=2, name="Test Çocuk", class_name="9-A", total_absences=0))
        d = date(2025, 2, 1)
        db.add(Grade(student_id=2, subject="Matematik", grade=72.0, date=d))
        db.commit()
        parent = User(
            id=10,
            username="p1",
            password_hash="x",
            role=UserRole.PARENT,
            related_id=2,
            related_class=None,
        )
        yield db, parent
    finally:
        db.close()

def test_outlook_triggers_on_risk_and_probability(outlook_db):
    db, parent = outlook_db
    out = try_parent_student_outlook_answer(
        db,
        parent,
        "Risk skoruna göre dönem sonu başarı olasılığı nedir?",
        "tr",
    )
    assert out is not None
    assert out["results_count"] >= 2
    assert "risk" in (out.get("explanation") or "").lower()

def test_outlook_mathematics_focus(outlook_db):
    db, parent = outlook_db
    out = try_parent_student_outlook_answer(
        db,
        parent,
        "Matematikte başarı şansım ne risk skoruyla",
        "tr",
    )
    assert out is not None
    metrics = " ".join(str(r.get("value", "")) for r in out["results"])
    assert "72" in metrics or 72.0 in [r.get("value") for r in out["results"]]

def test_outlook_not_for_teacher(outlook_db):
    db, _ = outlook_db
    t = User(
        id=11,
        username="t",
        password_hash="x",
        role=UserRole.TEACHER,
        related_id=1,
        related_class="9-A",
    )
    assert (
        try_parent_student_outlook_answer(
            db, t, "risk skoru başarı olasılığı", "tr"
        )
        is None
    )

def test_outlook_no_false_trigger():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Sess = sessionmaker(bind=engine, future=True)
    db = Sess()
    try:
        db.add(Student(id=2, name="X", class_name="9-A", total_absences=0))
        db.commit()
        u = User(
            id=1,
            username="p",
            password_hash="x",
            role=UserRole.PARENT,
            related_id=2,
            related_class=None,
        )
        assert try_parent_student_outlook_answer(db, u, "bugün hava nasıl", "tr") is None
    finally:
        db.close()
