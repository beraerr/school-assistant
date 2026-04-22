from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models as _models  # noqa: F401
from backend.app.core.database import Base
from backend.app.models.grade import Grade
from backend.app.models.student import Student
from backend.app.models.user import User, UserRole
from backend.app.services.query_shortcuts import try_parent_benchmark_answer
from backend.app.services.query_shortcuts.parent_benchmark import _strict_rank

@pytest.fixture
def bench_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Sess = sessionmaker(bind=engine, future=True)
    db = Sess()
    try:
        db.add_all(
            [
                Student(id=1, name="Ali A", class_name="9-A", total_absences=0),
                Student(id=2, name="Veli Çocuk", class_name="9-A", total_absences=1),
                Student(id=3, name="Zeki Z", class_name="9-A", total_absences=0),
            ]
        )
        d = date(2025, 1, 10)
        for sid, grades in [
            (1, [70, 70]),
            (2, [80, 90]),
            (3, [88, 92]),
        ]:
            for g in grades:
                db.add(Grade(student_id=sid, subject="Matematik", grade=float(g), date=d))
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

def test_strict_rank():
    means = {1: 70.0, 2: 85.0, 3: 90.0}
    r, n = _strict_rank(85.0, means, 2)
    assert n == 3
    assert r == 2  # bir öğrenci daha yüksek (90)

def test_parent_benchmark_returns_aggregate_rows_only(bench_db):
    db, parent = bench_db
    out = try_parent_benchmark_answer(
        db, parent, "çocuğum okulda kaçıncı sırada", "tr"
    )
    assert out is not None
    assert out["results_count"] >= 4
    metrics = {r["metric"]: r["value"] for r in out["results"]}
    assert metrics["Genel not ortalaması (çocuğunuz)"] == 85.0
    assert metrics["Genel nota göre okuldaki sıra"] == "2 / 3"
    assert "Genel not ortalaması" in out["explanation"]

def test_parent_benchmark_privacy_note_only_when_asked(bench_db):
    db, parent = bench_db
    out_plain = try_parent_benchmark_answer(db, parent, "okulda kaçıncı sırada", "tr")
    out_priv = try_parent_benchmark_answer(db, parent, "veri anonim mi okulda kaçıncı", "tr")
    assert out_plain is not None and out_priv is not None
    assert "anonim toplulaştırıcı" not in out_plain["explanation"].lower()
    assert "anonim toplulaştırıcı" in out_priv["explanation"].lower()

def test_parent_benchmark_rank_risk_why_returns_chat_style_explanation(bench_db):
    db, parent = bench_db
    out = try_parent_benchmark_answer(
        db,
        parent,
        "okulda 60. sırada ama yüksek riskte diyorsun, neden normal mi",
        "tr",
    )
    assert out is not None
    assert out["conversation_mode"] == "chat"
    assert out["sql_query"] == ""
    msg = out["explanation"].lower()
    assert "mümkün" in msg or "mumkun" in msg
    assert "risk" in msg and "sıra" in msg

def test_parent_benchmark_no_match_for_teacher(bench_db):
    db, _ = bench_db
    teacher = User(
        id=11,
        username="t1",
        password_hash="x",
        role=UserRole.TEACHER,
        related_id=1,
        related_class="9-A",
    )
    assert try_parent_benchmark_answer(db, teacher, "okulda kaçıncı", "tr") is None

def test_parent_benchmark_mathematics_average_question(bench_db):
    db, parent = bench_db
    out = try_parent_benchmark_answer(
        db, parent, "sınıfın matematik ortalaması nedir çocuğumla kıyasla", "tr"
    )
    assert out is not None
    fields = " ".join(r["metric"] for r in out["results"])
    assert "Matematik" in fields
