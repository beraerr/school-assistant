import re
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from backend.app.models.user import User, UserRole
import logging

logger = logging.getLogger(__name__)

_SAFE_CLASS_NAME = re.compile(r"^[A-Za-z0-9_.\-]+$")

_SQL_KW_AFTER_STUDENTS = frozenset(
    {
        "where",
        "join",
        "left",
        "right",
        "inner",
        "full",
        "cross",
        "natural",
        "group",
        "order",
        "limit",
        "offset",
        "union",
        "except",
        "intersect",
        "on",
        "using",
        "as",
        "select",
        "from",
        "into",
    }
)

class RuleEngine:
    """Rule engine for role-based access control"""

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.role = user.role

    @staticmethod
    def _validate_class_name(class_name: str) -> str:
        if not class_name or not _SAFE_CLASS_NAME.match(class_name):
            raise ValueError("Geçersiz sınıf adı / Invalid class name")
        return class_name

    @staticmethod
    def _validate_student_id(student_id: Any) -> int:
        if student_id is None:
            raise ValueError("Öğrenci ID belirtilmedi / Student ID not specified")
        try:
            sid = int(student_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Geçersiz öğrenci ID / Invalid student ID") from exc
        if sid < 0:
            raise ValueError("Geçersiz öğrenci ID / Invalid student ID")
        return sid

    @staticmethod
    def _students_qualifier(sql_query: str) -> str:
        """
        `students` tablosu için RBAC filtresinde kullanılacak nitelik.
        LLM `FROM students s` yazdığında `students.id` geçersizdir; `s.id` kullanılmalı.
        """
        for m in re.finditer(
            r"(?:\bFROM\b|\b(?:LEFT|RIGHT|INNER|FULL)\s+JOIN\b|\bJOIN\b)\s+"
            r"(?:(?P<schema>\w+)\.)?students\b"
            r"(?:\s+AS\s+(?P<a1>\w+)|\s+(?P<a2>\w+))?",
            sql_query,
            re.IGNORECASE,
        ):
            alias = m.group("a1") or m.group("a2")
            if alias and alias.lower() not in _SQL_KW_AFTER_STUDENTS:
                return alias
        return "students"

    @staticmethod
    def _students_in_query(sql_query: str) -> bool:
        """Return True if the `students` table actually appears in a FROM/JOIN clause."""
        return bool(re.search(
            r"\b(?:FROM|(?:LEFT|RIGHT|INNER|FULL|CROSS)\s+JOIN|JOIN)\s+"
            r"(?:\w+\.)?students\b",
            sql_query,
            re.IGNORECASE,
        ))

    @staticmethod
    def _fk_student_id_qualifier(sql_query: str) -> str:
        """
        Find the alias (or bare table name) for the first table that carries a
        `student_id` FK — i.e., `grades` or `attendance`.

        Used when `students` is not in the FROM clause so we can inject
        `<alias>.student_id = :rbac_student_id` instead of the broken
        `students.id = :rbac_student_id`.
        """
        for tbl in ("grades", "attendance"):
            m = re.search(
                rf"\b(?:FROM|JOIN)\s+{tbl}\b\s*(?:AS\s+(?P<a1>\w+)|(?P<a2>\w+))?",
                sql_query,
                re.IGNORECASE,
            )
            if m:
                alias = m.group("a1") or m.group("a2")
                if alias and alias.lower() not in _SQL_KW_AFTER_STUDENTS:
                    return alias
                return tbl
        return ""

    def apply_permissions(self, sql_query: str) -> Dict[str, Any]:
        """
        Apply role-based permissions to SQL query.

        Returns:
            Dictionary with modified SQL (using bound parameter placeholders),
            bind parameter values for execution, and permission info.
        """
        original_query = sql_query.strip()

        if self.role == UserRole.PRINCIPAL:
            return {
                "sql": original_query,
                "bindparams": {},
                "permissions_applied": False,
                "reason": "Müdür tüm verilere erişebilir / Principal has full access",
            }

        if self.role == UserRole.TEACHER:
            modified_query, binds = self._restrict_to_class(original_query)
            cn = binds.get("rbac_class_name", "")
            return {
                "sql": modified_query,
                "bindparams": binds,
                "permissions_applied": True,
                "reason": (
                    f"Öğretmen sadece {cn} sınıfına erişebilir / "
                    f"Teacher restricted to class {cn}"
                ),
            }

        if self.role == UserRole.PARENT:
            sid = self._validate_student_id(self.user.related_id)
            modified_query, binds = self._restrict_to_student(original_query, sid)
            return {
                "sql": modified_query,
                "bindparams": binds,
                "permissions_applied": True,
                "reason": (
                    f"Veli sadece kendi çocuğunun (ID: {sid}) verilerine erişebilir / "
                    f"Parent restricted to student id {sid}"
                ),
            }

        if self.role == UserRole.STUDENT:
            sid = self._validate_student_id(self.user.related_id)
            modified_query, binds = self._restrict_to_student(original_query, sid)
            return {
                "sql": modified_query,
                "bindparams": binds,
                "permissions_applied": True,
                "reason": (
                    f"Öğrenci sadece kendi (ID: {sid}) verilerine erişebilir / "
                    f"Student restricted to own id {sid}"
                ),
            }

        raise ValueError(f"Unknown role: {self.role}")

    def _restrict_to_class(self, sql_query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Append class filter using a bound parameter (no string interpolation).

        If `students` is not in the FROM clause (e.g. query is just on `grades`),
        we inject a JOIN to students so we can filter by class_name safely.
        """
        class_name = self._validate_class_name(self.user.related_class or "")
        binds: Dict[str, Any] = {"rbac_class_name": class_name}

        if self._students_in_query(sql_query):
            st = self._students_qualifier(sql_query)
            suffix = f" AND {st}.class_name = :rbac_class_name"
            return self._inject_where_clause(sql_query, suffix), binds

        fk_qual = self._fk_student_id_qualifier(sql_query)
        join_clause = ""
        if fk_qual:
            join_clause = f" JOIN students rbac_s ON rbac_s.id = {fk_qual}.student_id"
        else:
            join_clause = " JOIN students rbac_s ON TRUE"

        tail = re.search(r"\s+(?:WHERE|GROUP\s+BY|ORDER\s+BY|LIMIT)\b", sql_query, re.IGNORECASE)
        if tail:
            head = sql_query[: tail.start()]
            rest = sql_query[tail.start() :]
            sql_query = f"{head}{join_clause}{rest}"
        else:
            sql_query = f"{sql_query}{join_clause}"

        suffix = " AND rbac_s.class_name = :rbac_class_name"
        return self._inject_where_clause(sql_query, suffix), binds

    def _restrict_to_student(self, sql_query: str, student_id: int) -> Tuple[str, Dict[str, Any]]:
        """
        Append a student-scoping predicate.

        Three cases:
        1. `students` is in FROM/JOIN  → use `<alias>.id = :rbac_student_id`
        2. `grades` or `attendance` is in FROM/JOIN (but not students)
           → use `<alias>.student_id = :rbac_student_id`  (FK column)
        3. None of the above  → add `JOIN students rbac_s ON TRUE` and filter
           via `rbac_s.id = :rbac_student_id`  (last-resort safety net)
        """
        binds = {"rbac_student_id": student_id}

        if self._students_in_query(sql_query):
            st = self._students_qualifier(sql_query)
            suffix = f" AND {st}.id = :rbac_student_id"
            return self._inject_where_clause(sql_query, suffix), binds

        fk_qual = self._fk_student_id_qualifier(sql_query)
        if fk_qual:
            suffix = f" AND {fk_qual}.student_id = :rbac_student_id"
            return self._inject_where_clause(sql_query, suffix), binds

        logger.warning(
            "RBAC _restrict_to_student: could not find students/grades/attendance "
            "in query — adding explicit JOIN students. SQL: %s", sql_query[:200]
        )
        tail = re.search(r"\s+(?:WHERE|GROUP\s+BY|ORDER\s+BY|LIMIT)\b", sql_query, re.IGNORECASE)
        if tail:
            head = sql_query[: tail.start()]
            rest = sql_query[tail.start() :]
            joined = f"{head} JOIN students rbac_s ON TRUE{rest}"
        else:
            joined = f"{sql_query} JOIN students rbac_s ON TRUE"
        suffix = " AND rbac_s.id = :rbac_student_id"
        return self._inject_where_clause(joined, suffix), binds

    @staticmethod
    def _inject_where_clause(sql_query: str, suffix_sql: str) -> str:
        """
        Append an RBAC predicate (suffix_sql looks like ' AND col = :rbac_x').

        Strategy
        --------
        1. If GROUP BY / ORDER BY / LIMIT exists → insert just before it,
           adding `WHERE 1=1` if there is no existing WHERE.
        2. If WHERE already exists → append at the very end of the query
           (before any trailing semicolon).
        3. Otherwise → append `WHERE 1=1 <suffix>` at the end.

        We deliberately avoid trying to parse the FROM/JOIN block because
        table aliases and ON clauses make that regex fragile.  Appending to
        the end is always safe for a single SELECT statement.
        """
        sql_upper = sql_query.upper()
        base = sql_query.rstrip().rstrip(";")

        tail = re.search(
            r"(\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT)\b)", base, re.IGNORECASE
        )
        if tail:
            head = base[: tail.start()]
            rest = base[tail.start() :]
            if "WHERE" in sql_upper:
                return f"{head}{suffix_sql}{rest}"
            return f"{head} WHERE 1=1{suffix_sql}{rest}"

        if "WHERE" in sql_upper:
            return f"{base}{suffix_sql}"

        return f"{base} WHERE 1=1{suffix_sql}"

    def sanitize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove sensitive data based on user role
        """
        if self.role == UserRole.PRINCIPAL:
            return results

        sensitive_fields = ["tc_number", "phone", "address", "email"]
        sanitized = []

        for row in results:
            sanitized_row = {k: v for k, v in row.items() if k not in sensitive_fields}
            sanitized.append(sanitized_row)

        return sanitized
