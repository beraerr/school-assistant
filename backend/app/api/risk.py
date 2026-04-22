from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.core.database import get_db
from backend.app.models.student import Student
from backend.app.models.user import User, UserRole
from backend.app.models.risk_score import StudentRiskScore

router = APIRouter(prefix="/risk", tags=["risk"])

class RiskItem(BaseModel):
    student_id: int
    student_name: str
    class_name: str
    risk_score: float
    risk_level: str
    explanation: str
    ml_risk_score: float
    ml_risk_level: str
    ml_computed_at: Optional[str] = None

class RiskListResponse(BaseModel):
    items: List[RiskItem]
    count: int

def _fetch_ml_score(db: Session, student_id: int) -> Optional[StudentRiskScore]:
    return (
        db.query(StudentRiskScore)
        .filter(StudentRiskScore.student_id == student_id)
        .one_or_none()
    )

def _student_risk(student: Student, db: Session) -> RiskItem:
    ml = _fetch_ml_score(db, student.id)
    if not ml or ml.ml_risk_score is None:
        return RiskItem(
            student_id=student.id,
            student_name=student.name,
            class_name=student.class_name,
            risk_score=0.0,
            risk_level="unknown",
            explanation="ml risk skoru bulunamadi, once score_students_ml.py calistirin",
            ml_risk_score=0.0,
            ml_risk_level="unknown",
            ml_computed_at=None,
        )

    score = round(float(ml.ml_risk_score), 2)
    level = (ml.ml_risk_level or "unknown").lower()
    ml_at = ml.computed_at.isoformat() if ml.computed_at else None

    return RiskItem(
        student_id=student.id,
        student_name=student.name,
        class_name=student.class_name,
        risk_score=score,
        risk_level=level,
        explanation=f"ml tahmin seviyesi: {level}",
        ml_risk_score=score,
        ml_risk_level=level,
        ml_computed_at=ml_at,
    )

def filter_students_for_risk(db: Session, current_user: User, class_name: Optional[str]) -> List[Student]:
    query = db.query(Student)

    if current_user.role == UserRole.PRINCIPAL:
        if class_name:
            query = query.filter(Student.class_name == class_name)
        return query.all()

    if current_user.role == UserRole.TEACHER:
        return query.filter(Student.class_name == current_user.related_class).all()

    if current_user.role in [UserRole.PARENT, UserRole.STUDENT]:
        if current_user.related_id is None:
            return []
        return query.filter(Student.id == current_user.related_id).all()

    return []

def compute_student_risk_item(db: Session, student: Student) -> RiskItem:
    """Tek öğrenci için ML tabanli risk sonucu (NL kısayolu için de kullanılır)."""
    return _student_risk(student, db)

@router.get("/students", response_model=RiskListResponse)
async def list_student_risks(
    class_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskListResponse:
    """
    Return ML-only risk scores for visible students.
    """
    students = filter_students_for_risk(db, current_user, class_name)
    items = [compute_student_risk_item(db, student) for student in students]
    items.sort(key=lambda i: i.risk_score, reverse=True)
    return RiskListResponse(items=items, count=len(items))
