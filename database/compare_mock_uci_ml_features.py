from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("DEBUG", "false")

from sqlalchemy.orm import Session  # noqa: E402

from backend.app.core.database import SessionLocal  # noqa: E402
from backend.app.models.grade import Grade  # noqa: E402
from backend.app.models.student import Student  # noqa: E402

from database.score_students_ml import (  # noqa: E402
    _build_uci_features,
    _load_uci_df,
    _student_features,
    train_or_load_model,
    FEATURE_NAMES,
)

def _quantile_table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    qs = [0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
    rows = []
    for c in cols:
        s = df[c].astype(float)
        row = {"feature": c, "n": int(s.count()), "mean": s.mean(), "std": s.std()}
        for q in qs:
            row[f"p{int(q * 100)}"] = float(s.quantile(q))
        rows.append(row)
    return pd.DataFrame(rows)

def _mock_feature_frame(db: Session) -> pd.DataFrame:
    students = db.query(Student).order_by(Student.id).all()
    rows = []
    for st in students:
        feats = _student_features(st, db)
        feats["student_id"] = st.id
        feats["class_name"] = st.class_name
        feats["total_absences"] = float(st.total_absences or 0)
        rows.append(feats)
    return pd.DataFrame(rows)

def main() -> None:
    out_dir = _PROJECT_ROOT / "data_science" / "reports" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== UCI vs mock DB — ML feature dağılımı ===\n")

    print("UCI yükleniyor…")
    uci_raw = _load_uci_df()
    X_uci, y_uci = _build_uci_features(uci_raw)
    print(f"  UCI satır: {len(X_uci)}  |  y=1 oranı: {y_uci.mean():.1%}\n")

    print("Mock DB bağlanıyor…")
    db = SessionLocal()
    try:
        X_mock = _mock_feature_frame(db)
    finally:
        db.close()

    n_mock = len(X_mock)
    print(f"  Öğrenci sayısı: {n_mock}\n")
    if n_mock == 0:
        print("DB'de öğrenci yok. seed_from_uci.py çalıştırıldığından emin ol.")
        return

    uci_tbl = _quantile_table(X_uci, FEATURE_NAMES)
    uci_tbl.insert(0, "dataset", "uci_train")

    mock_feat_only = X_mock[FEATURE_NAMES].copy()
    mock_tbl = _quantile_table(mock_feat_only, FEATURE_NAMES)
    mock_tbl.insert(0, "dataset", "mock_db")

    summary = pd.concat([uci_tbl, mock_tbl], ignore_index=True)
    summary_path = out_dir / "feature_dist_uci_vs_mock_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Özet CSV: {summary_path}\n")

    a = uci_tbl.drop(columns=["dataset"]).add_suffix("_uci")
    a.rename(columns={"feature_uci": "feature"}, inplace=True)
    b = mock_tbl.drop(columns=["dataset"]).add_suffix("_mock")
    b.rename(columns={"feature_mock": "feature"}, inplace=True)
    merge = a.merge(b, on="feature")
    slim = merge[
        [
            "feature",
            "mean_uci",
            "mean_mock",
            "p50_uci",
            "p50_mock",
            "p90_uci",
            "p90_mock",
        ]
    ]
    print("--- mean / median / p90 karşılaştırması ---")
    print(slim.to_string(index=False))
    print()

    print("Model yüklenip mock üzerinde predict_proba hesaplanıyor…")
    model = train_or_load_model()
    db2 = SessionLocal()
    probs: list[float] = []
    try:
        for st in db2.query(Student).order_by(Student.id).all():
            feats = _student_features(st, db2)
            row = pd.DataFrame([feats], columns=FEATURE_NAMES)
            p = float(model.predict_proba(row)[0][1])
            probs.append(p)
    finally:
        db2.close()

    p_arr = np.array(probs, dtype=float)
    print(
        f"  predict_proba: min={p_arr.min():.4f} max={p_arr.max():.4f} "
        f"mean={p_arr.mean():.4f} median={np.median(p_arr):.4f}"
    )
    print(
        f"  buckets (raw prob): <0.35 → {int((p_arr < 0.35).sum())}, "
        f"0.35–0.6 → {int(((p_arr >= 0.35) & (p_arr < 0.6)).sum())}, "
        f"≥0.6 → {int((p_arr >= 0.6).sum())}"
    )
    print()

    sample = X_mock.head(200)
    sample_path = out_dir / "mock_student_features_sample.csv"
    sample.to_csv(sample_path, index=False)
    print(f"Mock örnek (ilk 200): {sample_path}")

if __name__ == "__main__":
    main()
