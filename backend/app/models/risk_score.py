from datetime import date

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.core.database import Base

class StudentRiskScore(Base):
    """
    Stores the GBM-predicted risk score for each student.

    Populated by:  python database/score_students_ml.py
    Refreshed:     any time the pipeline is re-run (rows are upserted).

    Columns
    -------
    ml_risk_score : float  — 0-100 (model predict_proba × 100)
    ml_risk_level : str    — "high" / "medium" / "low"
    features_json : str    — JSON snapshot of features used (audit trail)
    computed_at   : date   — date the score was computed
    """

    __tablename__ = "student_risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    ml_risk_score = Column(Float, nullable=False)   # 0 – 100
    ml_risk_level = Column(String(16), nullable=False)  # high / medium / low
    features_json = Column(Text, nullable=True)     # serialised feature dict
    computed_at = Column(Date, nullable=False, default=date.today)

    student = relationship("Student", backref="ml_risk_score_record", uselist=False)

    def __repr__(self) -> str:
        return (
            f"<StudentRiskScore(student_id={self.student_id}, "
            f"ml_risk_score={self.ml_risk_score}, "
            f"ml_risk_level={self.ml_risk_level})>"
        )
