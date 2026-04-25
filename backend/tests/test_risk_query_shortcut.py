from backend.app.services.query_shortcuts import _RISK_SUCCESS_RE
from backend.app.services.query_shortcuts.risk_summary import _wants_risk_meaning

def test_risk_success_regex_matches_achievement_questions():
    assert _RISK_SUCCESS_RE.search("elifin başarı durumu ne")
    assert _RISK_SUCCESS_RE.search("öğrencinin akademik durumu")
    assert _RISK_SUCCESS_RE.search("risk skoru nedir")
    assert _RISK_SUCCESS_RE.search("give these risk values")
    assert _RISK_SUCCESS_RE.search("genel akademik durum nasıl")
    assert _RISK_SUCCESS_RE.search("kimler riskli")
    assert _RISK_SUCCESS_RE.search("hangi öğrenciler risk altında")
    assert _RISK_SUCCESS_RE.search("kimler neden riskli")
    assert _RISK_SUCCESS_RE.search("bu risk ne anlama geliyor")
    assert not _RISK_SUCCESS_RE.search("Bu ay devamsızlığı 5 günü geçen öğrencileri göster")

def test_wants_risk_meaning_query():
    assert _wants_risk_meaning("bu risk ne anlama geliyor")
    assert _wants_risk_meaning("what does this risk mean")
    assert not _wants_risk_meaning("kimler riskli")
