from backend.app.services.query_shortcuts import _PARENT_CHILD_RE

def test_regex_matches_common_parent_questions():
    assert _PARENT_CHILD_RE.search("ben kimin velisiyim")
    assert _PARENT_CHILD_RE.search("Ben kimin velisiyim?")
    assert _PARENT_CHILD_RE.search("çocuğum kim")
    assert _PARENT_CHILD_RE.search("öğrencimin adı ne")
    assert _PARENT_CHILD_RE.search("öğrencinin adı ne")
    assert not _PARENT_CHILD_RE.search("bu ay devamsızlığı 5 günü geçen öğrenciler")
    assert not _PARENT_CHILD_RE.search("çocuğumun tüm ders notlarını göster")
