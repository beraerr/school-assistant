from backend.app.models.student import Student
from backend.app.services.query_shortcuts import (
    _RISK_SUCCESS_RE,
    narrow_students_by_name_mention,
)
from backend.app.services.query_shortcuts.risk_summary import _pick_highest_risk_items
from backend.app.services.query_shortcuts.risk_summary import _wants_full_list
from backend.app.api.risk import RiskItem

def test_risk_success_regex_matches_achievement_questions():
    assert _RISK_SUCCESS_RE.search("elifin başarı durumu ne")
    assert _RISK_SUCCESS_RE.search("öğrencinin akademik durumu")
    assert _RISK_SUCCESS_RE.search("risk skoru nedir")
    assert _RISK_SUCCESS_RE.search("give these risk values")
    assert _RISK_SUCCESS_RE.search("genel akademik durum nasıl")
    assert not _RISK_SUCCESS_RE.search("Bu ay devamsızlığı 5 günü geçen öğrencileri göster")

def _stu(name: str, sid: int = 1) -> Student:
    return Student(id=sid, name=name, class_name="9-A", total_absences=0)

def test_narrow_students_ascii_turkish_name_in_question():
    pool = [
        _stu("Mehmet Koç", 1),
        _stu("Elif Yılmaz", 2),
        _stu("Elif Duman", 3),
    ]
    q = "elif yilmazin risk durumu ne"
    got = narrow_students_by_name_mention(pool, q)
    assert len(got) == 1
    assert got[0].name == "Elif Yılmaz"

def test_narrow_students_turkish_chars_in_question():
    pool = [_stu("Elif Yılmaz", 2), _stu("Tarık Keskin", 9)]
    q = "Elif Yılmaz'ın risk durumu nedir"
    got = narrow_students_by_name_mention(pool, q)
    assert len(got) == 1
    assert got[0].name == "Elif Yılmaz"

def test_narrow_students_single_student_unchanged():
    one = [_stu("Elif Yılmaz", 2)]
    assert narrow_students_by_name_mention(one, "risk durumu") is one

def test_narrow_students_no_name_returns_full_pool():
    pool = [_stu("Ali Veli", 1), _stu("Zeynep Kaya", 2)]
    got = narrow_students_by_name_mention(pool, "sınıfın risk özeti")
    assert len(got) == 2

def _risk_item(name: str, score: float) -> RiskItem:
    return RiskItem(
        student_id=1,
        student_name=name,
        class_name="9-A",
        risk_score=score,
        risk_level="high",
        explanation="test",
        ml_risk_score=score,
        ml_risk_level="high",
        ml_computed_at=None,
    )

def test_pick_highest_risk_items_filters_for_highest_query():
    items = [
        _risk_item("A", 91.0),
        _risk_item("B", 89.0),
        _risk_item("C", 91.0),
    ]
    top = _pick_highest_risk_items(items, "risk skoru en yüksek öğrencileri göster")
    assert len(top) == 2
    assert {x.student_name for x in top} == {"A", "C"}

def test_pick_highest_risk_items_keeps_all_for_general_risk_query():
    items = [
        _risk_item("A", 91.0),
        _risk_item("B", 89.0),
    ]
    out = _pick_highest_risk_items(items, "risk özeti göster")
    assert len(out) == 2

def test_wants_full_list_only_when_explicit():
    assert _wants_full_list("tüm öğrencilerin risk listesini ver")
    assert _wants_full_list("show all students risk scores")
    assert not _wants_full_list("risk durumu nedir")
