from backend.app.services.llm_service import extract_first_select_sql

def test_extract_stops_at_semicolon_before_prose():
    raw = """SELECT id FROM students WHERE id = 1;

Wait, cleaner approach:

SELECT id FROM students WHERE id = 2"""
    out = extract_first_select_sql(raw)
    assert out.upper().startswith("SELECT")
    assert "Wait" not in out
    assert "cleaner" not in out.lower()
    assert out.strip() == "SELECT id FROM students WHERE id = 1"

def test_extract_strips_leading_garbage():
    raw = "Here is the query:\nSELECT 1 AS x"
    out = extract_first_select_sql(raw)
    assert out == "SELECT 1 AS x"

def test_extract_prose_line_without_semicolon():
    raw = """SELECT name FROM students WHERE id = 5
Wait, I should use JOIN instead."""
    out = extract_first_select_sql(raw)
    assert "Wait" not in out
    assert "JOIN" not in out
