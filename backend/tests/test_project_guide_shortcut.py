from backend.app.models.user import User, UserRole
from backend.app.services.query_shortcuts import try_project_guide_answer

def _dummy_user() -> User:
    return User(
        id=1,
        username="u",
        password_hash="x",
        role=UserRole.PRINCIPAL,
        related_id=None,
        related_class=None,
    )

def test_project_guide_matches_identity_question():
    out = try_project_guide_answer(None, _dummy_user(), "Sen kimsin?", "tr")
    assert out is not None
    assert out["conversation_mode"] == "chat"
    assert "Mahmut Hoca" in out["explanation"]

def test_project_guide_matches_risk_interpretation_question():
    out = try_project_guide_answer(
        None,
        _dummy_user(),
        "Bir öğrencinin risk skoru senin için ne anlama geliyor, ne önerirsin?",
        "tr",
    )
    assert out is not None
    assert "erken uyarı" in out["explanation"].lower()
    assert out["results_count"] == 0

def test_project_guide_does_not_match_general_mahmut_hoca_risk_data_question():
    out = try_project_guide_answer(
        None,
        _dummy_user(),
        "Mahmut hoca sınıfın risk değerlerini ver",
        "tr",
    )
    assert out is None
