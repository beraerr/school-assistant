from __future__ import annotations

import json
import logging
import os
import pickle
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Any

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("DEBUG", "false")
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from backend.app.core.database import SessionLocal, engine, Base  # noqa: E402
from backend.app.models.student import Student                     # noqa: E402
from backend.app.models.grade import Grade                         # noqa: E402
from backend.app.models.risk_score import StudentRiskScore         # noqa: E402

from data_science.src.risk_model_pipeline import download_and_load_uci, Paths  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

GRADE_SCALE = 5.0          # UCI grades are 0-20; DB grades are 0-100
FEATURE_NAMES = ["absences", "absences_log", "grade_avg_mid", "grade_trend"]

def _load_uci_df() -> pd.DataFrame:
    """Return raw UCI merged DataFrame from local cache.

    Paths.root must be the data_science/ directory so that
    paths.data_raw resolves to data_science/data/raw/.
    """
    ds_root = _PROJECT_ROOT / "data_science"
    paths = Paths(ds_root)
    return download_and_load_uci(paths)

def _build_uci_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Extract the 4 DB-compatible features and risk label from UCI data.

    Features (UCI scale — no conversion needed here):
        absences, absences_log, grade_avg_mid (G1+G2/2), grade_trend (G2-G1)

    Label:
        at_risk = high absences (≥10 annually)
                  OR low final grade (G3 < 10 / 20)
                  OR falling mid-year AND borderline finish
    """
    work = df.copy()

    ABSENCE_CAP = 25
    work["absences"] = work["absences"].clip(upper=ABSENCE_CAP)

    grade_avg_mid = (work["G1"] + work["G2"]) / 2.0
    grade_trend   = work["G2"] - work["G1"]
    absences_log  = np.log1p(work["absences"])

    X = pd.DataFrame({
        "absences":      work["absences"],
        "absences_log":  absences_log,
        "grade_avg_mid": grade_avg_mid,
        "grade_trend":   grade_trend,
    })

    y = (
        (work["absences"] >= 10)
        | (work["G3"] < 10)
        | ((grade_trend < 0) & (work["G3"] < 12))
    ).astype(int)

    return X, y

def _load_winner_algorithm() -> tuple[object, str]:
    """
    data_science/models/winner_meta.json dosyasından kazanan algoritmayı okur.
    Reads the winning algorithm from data_science/models/winner_meta.json.

    Döndürür / Returns:
        (sklearn_estimator, algorithm_name_str)
    """
    meta_path = _PROJECT_ROOT / "data_science" / "models" / "winner_meta.json"
    if not meta_path.exists():
        logger.info("  winner_meta.json bulunamadı → varsayılan: GradientBoosting")
        return GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.08,
            subsample=0.8, random_state=42,
        ), "gradient_boosting (default)"

    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    algo_name = meta.get("model", "gradient_boosting")
    feat_set  = meta.get("feature_set", "?")

    logger.info(
        f"  Kazanan model / Winner model: {algo_name}  "
        f"(feature_set={feat_set}, F1={meta.get('f1','?')}, AUC={meta.get('roc_auc','?')})"
    )
    if feat_set == "extended":
        logger.info(
            "  Extended feature set DB şemasında tam olarak uygulanamaz. "
            "Kazanan algoritmayı 4 DB özelliğiyle eğitiyoruz."
        )

    if algo_name == "random_forest":
        return RandomForestClassifier(
            n_estimators=300, max_depth=8, random_state=42
        ), algo_name
    if algo_name == "logistic_regression":
        return LogisticRegression(max_iter=1000, random_state=42), algo_name
    return GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.08,
        subsample=0.8, random_state=42,
    ), algo_name

def _load_model_artifact_if_compatible() -> tuple[Pipeline | None, str]:
    """
    Try using data_science/models/winner_model.pkl directly.

    If the model requires features outside FEATURE_NAMES, return None and fall
    back to DB-compatible training in this script.
    """
    model_path = _PROJECT_ROOT / "data_science" / "models" / "winner_model.pkl"
    if not model_path.exists():
        return None, "winner_model.pkl not found"
    try:
        with open(model_path, "rb") as fh:
            model = pickle.load(fh)
    except Exception as exc:
        return None, f"could not load winner_model.pkl: {exc}"

    req = getattr(model, "feature_names_in_", None)
    if req is not None:
        req_set = {str(x) for x in req}
        if req_set != set(FEATURE_NAMES):
            return None, (
                "winner_model.pkl feature set differs from DB-compatible features "
                f"(required={sorted(req_set)}, available={FEATURE_NAMES})"
            )

    if not hasattr(model, "predict_proba"):
        return None, "winner_model.pkl has no predict_proba"

    return model, "winner_model.pkl"

def train_or_load_model() -> Pipeline:
    """
    Kazanan algoritmayı 4 DB-uyumlu özellik üzerinde UCI verisiyle eğitir.
    Trains the winner algorithm on UCI data using 4 DB-compatible features.

    Returns a fitted sklearn Pipeline (StandardScaler → winner algorithm).
    """
    logger.info("Loading UCI data for training …")
    df = _load_uci_df()
    logger.info(f"  UCI dataset: {len(df)} rows × {df.shape[1]} columns")

    X, y = _build_uci_features(df)
    pos_rate = y.mean()
    logger.info(f"  At-risk prevalence: {pos_rate:.1%}  ({y.sum()} / {len(y)})")

    artifact_model, artifact_label = _load_model_artifact_if_compatible()
    if artifact_model is not None:
        logger.info(f"  Using pre-trained model artifact: {artifact_label}")
        return artifact_model

    logger.info(f"  Model artifact not used: {artifact_label}")
    estimator, algo_label = _load_winner_algorithm()

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", estimator),
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    roc_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    logger.info(
        f"  CV ROC-AUC (5-fold): {roc_scores.mean():.3f} ± {roc_scores.std():.3f}"
        f"  [{algo_label}]"
    )

    model.fit(X, y)
    logger.info(f"  Model ({algo_label}) trained on full UCI dataset.")
    return model

def _student_features(student: Student, db) -> Dict[str, Any]:
    """
    Extract the 4 model features for a DB student.

    Grades are stored 0-100 in the DB; we divide by GRADE_SCALE (5) to get
    0-20 (UCI scale) before passing to the model.
    """
    grades_q = (
        db.query(Grade)
        .filter(Grade.student_id == student.id)
        .order_by(Grade.date.asc())
        .all()
    )

    if grades_q:
        raw_grades = [g.grade / GRADE_SCALE for g in grades_q]
        half = max(1, len(raw_grades) // 2)
        g1_val = float(np.mean(raw_grades[:half]))
        g2_val = float(np.mean(raw_grades[half:]))
    else:
        g1_val = g2_val = 10.0  # neutral UCI midpoint

    absences = min(float(student.total_absences or 0), 25.0)

    return {
        "absences":      absences,
        "absences_log":  float(np.log1p(absences)),
        "grade_avg_mid": (g1_val + g2_val) / 2.0,
        "grade_trend":   g2_val - g1_val,
    }

def _ml_risk_level(score_100: float) -> str:
    """Map 0-100 composite risk score to low/medium/high."""
    if score_100 >= 60:
        return "high"
    if score_100 >= 30:
        return "medium"
    return "low"

def _composite_risk_score(feats: Dict[str, Any], raw_ml_prob: float) -> float:
    """
    Kalibre edilmiş bileşik risk skoru (0-100).
    Calibrated composite risk score (0-100).

    GBM/RF'in raw predict_proba değerleri UCI verisinde aşırı güvenli olma
    eğilimindedir (0.0 veya 1.0'a yakın); bu fonksiyon bu sorunu çözer.
    Raw predict_proba from GBM/RF tends to cluster at 0.0 or 1.0 when
    trained on UCI data (the labels are constructed from the same features),
    making the scores useless for nuanced ranking.  This composite score
    produces a well-spread 0–100 range that teachers/parents can interpret.

    Bileşenler / Components
    ─────────────────────────────────────────────────────────────────────
    grade_score  (40 %) : not ortalaması → düşük not yüksek risk
                          grade average  → low grade = higher risk
    absence_score (40 %): devamsızlık oranı → fazla devamsızlık yüksek risk
                          absence rate  → more days = higher risk
    trend_score  (15 %): not düşüşü → gerileyen trend yüksek risk
                          grade decline → falling grades = higher risk
    ml_boost      (5 %): modelin ML olasılığı ek sinyal olarak (sıkıştırılmış)
                          compressed ML probability as a small extra signal

    Ölçekleme referansları / Scale references
    ─────────────────────────────────────────────────────────────────────
    - grade_avg_mid : UCI ölçeği 0–20 (DB notu ÷ 5)
    - absences      : 0–25 gün (25'te sınırlandırılmış)
    - grade_trend   : G2 − G1 (negatif = düşüş)
    """
    grade_avg_mid: float = feats["grade_avg_mid"]  # 0-20 UCI scale
    absences: float      = feats["absences"]        # 0-25 (capped)
    grade_trend: float   = feats["grade_trend"]     # G2 - G1

    grade_score = 1.0 - min(grade_avg_mid / 20.0, 1.0)

    absence_score = min(absences / 25.0, 1.0)

    trend_score = max(0.0, min(1.0, -grade_trend / 8.0))

    if 0.0 < raw_ml_prob < 1.0:
        logit_val = math.log(raw_ml_prob / (1.0 - raw_ml_prob))
        ml_compressed = 1.0 / (1.0 + math.exp(-logit_val * 0.35))
    else:
        ml_compressed = raw_ml_prob

    composite = (
        0.40 * grade_score
        + 0.40 * absence_score
        + 0.15 * trend_score
        + 0.05 * ml_compressed
    )

    return round(min(composite * 100.0, 100.0), 2)

def score_all_students(model: Pipeline, db) -> None:
    """Predict risk for all students and upsert into student_risk_scores."""
    students = db.query(Student).all()
    logger.info(f"Scoring {len(students)} students …")

    db.query(StudentRiskScore).delete()

    today = date.today()
    counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}

    all_scores: list[float] = []

    for student in students:
        feats = _student_features(student, db)
        X_row = pd.DataFrame([feats], columns=FEATURE_NAMES)

        raw_prob = float(model.predict_proba(X_row)[0][1])

        score_100 = _composite_risk_score(feats, raw_prob)
        all_scores.append(score_100)

        level = _ml_risk_level(score_100)
        counts[level] += 1

        score_record = StudentRiskScore(
            student_id=student.id,
            ml_risk_score=score_100,
            ml_risk_level=level,
            features_json=json.dumps(feats, ensure_ascii=False),
            computed_at=today,
        )
        db.add(score_record)

    db.commit()

    if all_scores:
        logger.info(
            f"  Score stats: min={min(all_scores):.1f} "
            f"max={max(all_scores):.1f} "
            f"mean={sum(all_scores)/len(all_scores):.1f}"
        )
    logger.info(
        f"  Stored scores: high={counts['high']}, "
        f"medium={counts['medium']}, low={counts['low']}"
    )

def main() -> None:
    logger.info("=== ML Risk Scoring Pipeline ===")

    Base.metadata.create_all(bind=engine)
    logger.info("  Database tables verified.")

    model = train_or_load_model()

    db = SessionLocal()
    try:
        score_all_students(model, db)
    finally:
        db.close()

    logger.info("=== Done ===")

if __name__ == "__main__":
    main()
