import pytest
from unittest.mock import MagicMock

from backend.app.models.user import User, UserRole
from backend.app.services.rule_engine import RuleEngine

def _user(role: UserRole, related_class=None, related_id=None) -> User:
    u = MagicMock(spec=User)
    u.role = role
    u.related_class = related_class
    u.related_id = related_id
    return u

def test_teacher_filter_uses_bind_param_not_quotes():
    eng = RuleEngine(MagicMock(), _user(UserRole.TEACHER, related_class="9-A"))
    out = eng.apply_permissions("SELECT * FROM students")
    assert ":rbac_class_name" in out["sql"]
    assert out["bindparams"] == {"rbac_class_name": "9-A"}
    assert "9-A" not in out["sql"], "class name must not be embedded as a literal"

def test_parent_filter_uses_bind_param():
    eng = RuleEngine(MagicMock(), _user(UserRole.PARENT, related_id=42))
    out = eng.apply_permissions("SELECT * FROM students WHERE 1=1")
    assert ":rbac_student_id" in out["sql"]
    assert out["bindparams"]["rbac_student_id"] == 42

def test_parent_filter_uses_table_alias_when_llm_uses_s():
    eng = RuleEngine(MagicMock(), _user(UserRole.PARENT, related_id=61))
    sql = (
        "SELECT s.name, s.total_absences, a.date, a.status FROM students s "
        "LEFT JOIN attendance a ON a.student_id = s.id WHERE s.id = 61 ORDER BY a.date DESC"
    )
    out = eng.apply_permissions(sql)
    assert "s.id = :rbac_student_id" in out["sql"]
    assert "students.id = :rbac_student_id" not in out["sql"]

def test_teacher_class_filter_uses_alias_for_students():
    eng = RuleEngine(MagicMock(), _user(UserRole.TEACHER, related_class="9-A"))
    sql = "SELECT s.name FROM students s WHERE 1=1"
    out = eng.apply_permissions(sql)
    assert "s.class_name = :rbac_class_name" in out["sql"]
    assert "students.class_name" not in out["sql"]

def test_invalid_class_name_rejected():
    eng = RuleEngine(MagicMock(), _user(UserRole.TEACHER, related_class="9-A'; DROP TABLE students;--"))
    with pytest.raises(ValueError):
        eng.apply_permissions("SELECT * FROM students")
