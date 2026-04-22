from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
from zipfile import ZipFile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore", category=FutureWarning)

UCI_ZIP_URL = (
    "https://cdn.uci-ics-mlr-prod.aws.uci.edu/320/student%2Bperformance.zip"
)

PALETTE = {"low": "#2ca02c", "medium": "#ff7f0e", "high": "#d62728"}
MODEL_COLORS = ["#4C72B0", "#DD8452", "#55A868"]
FS_COLORS = {"base": "#4C72B0", "extended": "#DD8452"}

SOCIAL_COLS: List[str] = [
    "address",    # kentsel / kırsal
    "famsize",    # aile büyüklüğü
    "Pstatus",    # ebeveynler birlikte mi?
    "Medu",       # anne eğitim seviyesi (0-4)
    "Fedu",       # baba eğitim seviyesi (0-4)
    "Mjob",       # anne mesleği
    "Fjob",       # baba mesleği
    "traveltime", # ev-okul yolculuk süresi
    "paid",       # özel ders alıyor mu?
    "activities", # okul dışı aktivite
    "nursery",    # kreşe gitti mi?
    "romantic",   # romantik ilişki var mı?
    "famrel",     # aile ilişkisi kalitesi (1-5)
    "Dalc",       # hafta içi alkol (1-5)
    "Walc",       # hafta sonu alkol (1-5)
    "health",     # genel sağlık durumu (1-5)
]

@dataclass
class Paths:
    root: Path

    @property
    def data_raw(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def data_processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def figures(self) -> Path:
        return self.reports / "figures"

    @property
    def tables(self) -> Path:
        return self.reports / "tables"

    def ensure(self) -> None:
        for folder in [
            self.data_raw,
            self.data_processed,
            self.reports,
            self.figures,
            self.tables,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

def download_and_load_uci(paths: Paths) -> pd.DataFrame:
    """Download the UCI Student Performance zip and return a merged DataFrame."""
    zip_path = paths.data_raw / "student_performance.zip"
    if not zip_path.exists():
        resp = requests.get(UCI_ZIP_URL, timeout=60)
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)

    with ZipFile(zip_path, "r") as zf:
        zf.extractall(paths.data_raw)

    for nested_zip in paths.data_raw.glob("*.zip"):
        if nested_zip.name == zip_path.name:
            continue
        try:
            with ZipFile(nested_zip, "r") as zf:
                zf.extractall(paths.data_raw)
        except Exception:
            pass  # skip invalid inner files

    mat_candidates = list(paths.data_raw.rglob("student-mat.csv"))
    por_candidates = list(paths.data_raw.rglob("student-por.csv"))
    if not mat_candidates or not por_candidates:
        raise FileNotFoundError(
            "UCI CSV files not found after extraction. Check zip structure."
        )

    mat = pd.read_csv(mat_candidates[0], sep=";")
    por = pd.read_csv(por_candidates[0], sep=";")
    mat["course"] = "mat"
    por["course"] = "por"
    return pd.concat([mat, por], ignore_index=True)

def build_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Engineer features and create a binary risk label.

    X (features) — mid-year only, no G3:
        grade_avg_mid : mean of G1 and G2
        grade_trend   : G2 - G1  (positive = improving)
        absences_log  : log1p(absences) to reduce skew
        + studytime, failures, goout, freetime, schoolsup,
          famsup, internet, higher, course, age, sex, school

    y (label) — uses G3 to define outcome (this is intentional):
        at-risk  = high absences (≥10)  OR  low final grade (G3<10)
                   OR  falling grades mid-year and borderline finish
    """
    work = df.copy()

    work["grade_avg_mid"] = work[["G1", "G2"]].mean(axis=1)
    work["grade_trend"] = work["G2"] - work["G1"]
    work["absences_log"] = np.log1p(work["absences"])

    y = (
        (work["absences"] >= 10)
        | (work["G3"] < 10)
        | ((work["grade_trend"] < 0) & (work["G3"] < 12))
    ).astype(int)

    feature_cols = [
        "absences",
        "absences_log",
        "grade_avg_mid",
        "grade_trend",
        "studytime",
        "failures",
        "goout",
        "freetime",
        "schoolsup",
        "famsup",
        "internet",
        "higher",
        "course",
        "age",
        "sex",
        "school",
    ]

    assert "G3" not in feature_cols, "DATA LEAKAGE: G3 found in feature columns!"

    return work[feature_cols].copy(), y

def build_features_extended(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Base feature set + sosyo-ekonomik / demografik sütunlar.

    Eklenen sütunlar (SOCIAL_COLS):
        address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob,
        traveltime, paid, activities, nursery, romantic,
        famrel, Dalc, Walc, health

    Hedef y: build_features() ile aynı tanım (label leakage yok).
    G3 yine X'e dahil edilmiyor.
    """
    work = df.copy()

    work["grade_avg_mid"] = work[["G1", "G2"]].mean(axis=1)
    work["grade_trend"] = work["G2"] - work["G1"]
    work["absences_log"] = np.log1p(work["absences"])

    y = (
        (work["absences"] >= 10)
        | (work["G3"] < 10)
        | ((work["grade_trend"] < 0) & (work["G3"] < 12))
    ).astype(int)

    base_cols = [
        "absences", "absences_log", "grade_avg_mid", "grade_trend",
        "studytime", "failures", "goout", "freetime",
        "schoolsup", "famsup", "internet", "higher",
        "course", "age", "sex", "school",
    ]
    available_social = [c for c in SOCIAL_COLS if c in work.columns]
    all_cols = base_cols + available_social

    assert "G3" not in all_cols, "DATA LEAKAGE: G3 found in extended features!"
    return work[all_cols].copy(), y

def feature_set_comparison(raw_df: pd.DataFrame, paths: Paths) -> Tuple[pd.DataFrame, Dict]:
    """
    Base ve Extended feature set'i her 3 modelde çalıştır,
    sonuçları karşılaştır, kazananı seç ve pickle olarak kaydet.

    Döndürür:
        comparison_df : Base × Extended × 3 model için metrikler
        winner_meta   : kazanan modelin özet bilgisi
    """
    import json
    import pickle

    X_base, y = build_features(raw_df)
    X_ext, _ = build_features_extended(raw_df)

    records = []
    fitted: Dict[str, object] = {}

    for feat_name, X in [("base", X_base), ("extended", X_ext)]:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
        for model_name, model in model_candidates().items():
            pre = make_preprocessor(X_tr)
            clf = Pipeline([("preprocessor", pre), ("model", model)])
            clf.fit(X_tr, y_tr)

            key = f"{feat_name}__{model_name}"
            fitted[key] = clf

            preds = clf.predict(X_te)
            probs = clf.predict_proba(X_te)[:, 1]

            records.append({
                "feature_set": feat_name,
                "model": model_name,
                "accuracy": round(accuracy_score(y_te, preds), 4),
                "precision": round(precision_score(y_te, preds, zero_division=0), 4),
                "recall": round(recall_score(y_te, preds, zero_division=0), 4),
                "f1": round(f1_score(y_te, preds, zero_division=0), 4),
                "roc_auc": round(roc_auc_score(y_te, probs), 4),
            })

    cmp_df = pd.DataFrame(records)
    cmp_df.to_csv(paths.tables / "feature_set_comparison.csv", index=False)

    _feature_set_comparison_chart(cmp_df, paths)

    best = cmp_df.sort_values("f1", ascending=False).iloc[0]
    winner_key = f"{best['feature_set']}__{best['model']}"
    winner_clf = fitted[winner_key]

    winner_meta = {
        "feature_set": best["feature_set"],
        "model": best["model"],
        "f1": float(best["f1"]),
        "roc_auc": float(best["roc_auc"]),
        "accuracy": float(best["accuracy"]),
        "precision": float(best["precision"]),
        "recall": float(best["recall"]),
    }

    models_dir = paths.root / "models"
    models_dir.mkdir(exist_ok=True)
    (models_dir / "winner_meta.json").write_text(
        json.dumps(winner_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with open(models_dir / "winner_model.pkl", "wb") as fh:
        pickle.dump(winner_clf, fh)

    print(f"  Kazanan: {winner_meta['feature_set']} / {winner_meta['model']} "
          f"(F1={winner_meta['f1']:.4f}, AUC={winner_meta['roc_auc']:.4f})")

    return cmp_df, winner_meta

def _feature_set_comparison_chart(df: pd.DataFrame, paths: Paths) -> None:
    """
    Base vs Extended karşılaştırması için yan yana bar grafik.
    Her model için F1, ROC-AUC, Accuracy gösterilir.
    """
    models = df["model"].unique().tolist()
    metrics = ["f1", "roc_auc", "accuracy"]
    metric_labels = ["F1 Score", "ROC-AUC", "Accuracy"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, metric, mlabel in zip(axes, metrics, metric_labels):
        base_vals = [
            df[(df["feature_set"] == "base") & (df["model"] == m)][metric].values[0]
            for m in models
        ]
        ext_vals = [
            df[(df["feature_set"] == "extended") & (df["model"] == m)][metric].values[0]
            for m in models
        ]
        x = np.arange(len(models))
        width = 0.35

        bars1 = ax.bar(x - width / 2, base_vals, width,
                       label="Base (akademik)", color=FS_COLORS["base"], alpha=0.88)
        bars2 = ax.bar(x + width / 2, ext_vals, width,
                       label="Extended (+sosyal)", color=FS_COLORS["extended"], alpha=0.88)

        ax.set_title(mlabel, fontsize=12, fontweight="bold")
        model_labels = [m.replace("_", "\n").replace("logistic\nregression", "Logistic\nReg.")
                        .replace("random\nforest", "Random\nForest")
                        .replace("gradient\nboosting", "Gradient\nBoosting")
                        for m in models]
        ax.set_xticks(x)
        ax.set_xticklabels(model_labels, fontsize=8)
        ax.set_ylim(0.65, 1.03)
        ax.grid(axis="y", alpha=0.3)
        ax.legend(fontsize=8)

        for bar in bars1:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                    f"{bar.get_height():.3f}", ha="center", fontsize=7,
                    color=FS_COLORS["base"], fontweight="bold")
        for bar in bars2:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                    f"{bar.get_height():.3f}", ha="center", fontsize=7,
                    color=FS_COLORS["extended"], fontweight="bold")

    fig.suptitle(
        "Base (Akademik) vs Extended (+Sosyal) Feature Set — Model Karşılaştırması",
        fontsize=13, fontweight="bold", y=1.02,
    )
    plt.tight_layout()
    plt.savefig(paths.figures / "feature_set_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()

def eda_social_features(df: pd.DataFrame, y: pd.Series, paths: Paths) -> None:
    """
    Sosyo-ekonomik / demografik sütunların risk etiketiyle ilişkisini gösteren EDA grafikleri.

    Grafikler:
      1. Ebeveyn eğitim seviyesi (Medu / Fedu) → ortalama risk oranı
      2. Alkol tüketimi (Dalc / Walc) → risk dağılımı
      3. Aile ilişkisi (famrel) ve sağlık durumu (health) → risk oranı
      4. Demografik (address, Pstatus, famsize) → risk yüzdesi
    """
    work = df.copy()
    work["at_risk"] = y.values

    if "Medu" in work.columns and "Fedu" in work.columns:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for ax, col, title in zip(axes, ["Medu", "Fedu"],
                                   ["Anne Eğitim Seviyesi (Medu)", "Baba Eğitim Seviyesi (Fedu)"]):
            risk_by_edu = work.groupby(col)["at_risk"].mean() * 100
            edu_labels = {0: "Yok", 1: "İlköğretim", 2: "Orta", 3: "Lise", 4: "Üniversite"}
            colors = [PALETTE["high"] if v > 50 else PALETTE["medium"] if v > 30 else PALETTE["low"]
                      for v in risk_by_edu.values]
            ax.bar([edu_labels.get(i, str(i)) for i in risk_by_edu.index],
                   risk_by_edu.values, color=colors, edgecolor="white")
            ax.set_title(title, fontsize=11)
            ax.set_ylabel("Risk Oranı (%)")
            ax.set_ylim(0, 100)
            ax.grid(axis="y", alpha=0.3)
            for i, v in enumerate(risk_by_edu.values):
                ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9, fontweight="bold")
        plt.suptitle("Ebeveyn Eğitim Seviyesi → Öğrenci Risk Oranı", fontsize=13, y=1.02)
        plt.tight_layout()
        plt.savefig(paths.figures / "eda_social_parent_edu.png", dpi=150, bbox_inches="tight")
        plt.close()

    if "Dalc" in work.columns and "Walc" in work.columns:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for ax, col, title in zip(axes, ["Dalc", "Walc"],
                                   ["Hafta İçi Alkol (Dalc)", "Hafta Sonu Alkol (Walc)"]):
            risk_by_alc = work.groupby(col)["at_risk"].mean() * 100
            colors = [PALETTE["high"] if v > 55 else PALETTE["medium"] if v > 35 else PALETTE["low"]
                      for v in risk_by_alc.values]
            ax.bar(risk_by_alc.index.astype(str), risk_by_alc.values,
                   color=colors, edgecolor="white")
            ax.set_title(title, fontsize=11)
            ax.set_xlabel("1=Çok Az → 5=Çok Fazla")
            ax.set_ylabel("Risk Oranı (%)")
            ax.set_ylim(0, 100)
            ax.grid(axis="y", alpha=0.3)
            for i, v in enumerate(risk_by_alc.values):
                ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9, fontweight="bold")
        plt.suptitle("Alkol Tüketimi → Öğrenci Risk Oranı", fontsize=13, y=1.02)
        plt.tight_layout()
        plt.savefig(paths.figures / "eda_social_alcohol.png", dpi=150, bbox_inches="tight")
        plt.close()

    available_ordinal = [c for c in ["famrel", "health"] if c in work.columns]
    if available_ordinal:
        fig, axes = plt.subplots(1, len(available_ordinal), figsize=(5 * len(available_ordinal), 4))
        if len(available_ordinal) == 1:
            axes = [axes]
        titles = {"famrel": "Aile İlişkisi Kalitesi (famrel)",
                  "health": "Genel Sağlık Durumu (health)"}
        for ax, col in zip(axes, available_ordinal):
            risk_rate = work.groupby(col)["at_risk"].mean() * 100
            ax.plot(risk_rate.index, risk_rate.values, "o-",
                    color=PALETTE["high"], linewidth=2, markersize=8)
            ax.fill_between(risk_rate.index, risk_rate.values, alpha=0.15, color=PALETTE["high"])
            ax.set_title(titles.get(col, col), fontsize=11)
            ax.set_xlabel("1=Çok Kötü → 5=Mükemmel")
            ax.set_ylabel("Risk Oranı (%)")
            ax.set_ylim(0, 100)
            ax.grid(alpha=0.3)
            for xi, yi in zip(risk_rate.index, risk_rate.values):
                ax.text(xi, yi + 2, f"{yi:.1f}%", ha="center", fontsize=9)
        plt.suptitle("Aile ve Sağlık Faktörleri → Risk Oranı", fontsize=13, y=1.02)
        plt.tight_layout()
        plt.savefig(paths.figures / "eda_social_family_health.png", dpi=150, bbox_inches="tight")
        plt.close()

    cat_cols = [(c, t) for c, t in [
        ("address", "Adres (U=Şehir / R=Kırsal)"),
        ("Pstatus", "Ebeveyn Durumu (T=Birlikte / A=Ayrı)"),
        ("famsize", "Aile Büyüklüğü"),
    ] if c in work.columns]

    if cat_cols:
        fig, axes = plt.subplots(1, len(cat_cols), figsize=(5 * len(cat_cols), 4))
        if len(cat_cols) == 1:
            axes = [axes]
        for ax, (col, title) in zip(axes, cat_cols):
            risk_pct = work.groupby(col)["at_risk"].mean() * 100
            bar_colors = [PALETTE["high"] if v > 50 else PALETTE["medium"] if v > 30 else PALETTE["low"]
                          for v in risk_pct.values]
            ax.bar(risk_pct.index, risk_pct.values, color=bar_colors, edgecolor="white", width=0.5)
            ax.set_title(title, fontsize=10)
            ax.set_ylabel("Risk Oranı (%)")
            ax.set_ylim(0, 100)
            ax.grid(axis="y", alpha=0.3)
            for i, (cat, v) in enumerate(risk_pct.items()):
                ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
        plt.suptitle("Demografik Faktörler → Risk Oranı", fontsize=13, y=1.02)
        plt.tight_layout()
        plt.savefig(paths.figures / "eda_social_demographic.png", dpi=150, bbox_inches="tight")
        plt.close()

def make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Return an unfitted ColumnTransformer for the given DataFrame schema."""
    numeric_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
    categorical_cols = X.select_dtypes(include=["object", "string"]).columns.tolist()

    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", numeric_pipe, numeric_cols),
        ("cat", categorical_pipe, categorical_cols),
    ])

def _clean_feature_names(names: List[str]) -> List[str]:
    """Strip sklearn ColumnTransformer prefixes (num__, cat__) for readable labels."""
    cleaned = []
    for n in names:
        n = n.replace("num__", "").replace("cat__", "")
        cleaned.append(n)
    return cleaned

def model_candidates() -> Dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=8, random_state=42
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=4, random_state=42
        ),
    }

def eda_plots(df: pd.DataFrame, y: pd.Series, paths: Paths) -> None:
    """
    Exploratory data analysis plots saved to reports/figures/.

    Plots:
      1. Risk class distribution (bar)
      2. Grade distributions (G1/G2) split by risk label
      3. Absence distribution by risk label
      4. Numeric feature correlation heatmap
    """
    work = df.copy()
    work["risk"] = y.map({0: "Not at risk", 1: "At risk"})

    fig, ax = plt.subplots(figsize=(5, 3.5))
    counts = y.value_counts().rename({0: "Not at risk", 1: "At risk"})
    colors = [PALETTE["low"], PALETTE["high"]]
    bars = ax.bar(counts.index, counts.values, color=colors, edgecolor="white", width=0.5)
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 5, str(v),
                ha="center", fontsize=11, fontweight="bold")
    ax.set_title("Risk Class Distribution", fontsize=13)
    ax.set_ylabel("Number of students")
    ax.set_ylim(0, counts.max() * 1.15)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(paths.figures / "eda_class_distribution.png", dpi=150)
    plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    for ax, col, title in zip(axes, ["G1", "G2"], ["Period-1 Grade (G1)", "Period-2 Grade (G2)"]):
        for label, color in [("Not at risk", PALETTE["low"]), ("At risk", PALETTE["high"])]:
            subset = work[work["risk"] == label][col]
            ax.hist(subset, bins=15, alpha=0.6, color=color, label=label, edgecolor="white")
        ax.set_title(title, fontsize=12)
        ax.set_xlabel("Grade (0–20)")
        ax.set_ylabel("Count")
        ax.legend(fontsize=9)
        ax.grid(axis="y", alpha=0.3)
    plt.suptitle("Grade Distributions by Risk Label", fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig(paths.figures / "eda_grade_distributions.png", dpi=150, bbox_inches="tight")
    plt.close()

    fig, ax = plt.subplots(figsize=(8, 4))
    for label, color in [("Not at risk", PALETTE["low"]), ("At risk", PALETTE["high"])]:
        subset = work[work["risk"] == label]["absences"]
        ax.hist(subset, bins=20, alpha=0.65, color=color, label=label, edgecolor="white")
    ax.axvline(10, color="gray", linestyle="--", linewidth=1.2, label="threshold (10)")
    ax.set_title("Absence Count Distribution by Risk Label", fontsize=13)
    ax.set_xlabel("Absences")
    ax.set_ylabel("Count")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(paths.figures / "eda_absence_distribution.png", dpi=150)
    plt.close()

    numeric_cols = ["G1", "G2", "absences", "studytime", "failures", "goout",
                    "freetime", "age", "Dalc", "Walc", "health"]
    available = [c for c in numeric_cols if c in df.columns]
    corr = df[available].corr().round(2)

    fig, ax = plt.subplots(figsize=(9, 7))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
        center=0, ax=ax, linewidths=0.5, annot_kws={"size": 8},
    )
    ax.set_title("Feature Correlation Heatmap", fontsize=13)
    plt.tight_layout()
    plt.savefig(paths.figures / "eda_correlation_heatmap.png", dpi=150)
    plt.close()

def evaluate_models(
    X: pd.DataFrame, y: pd.Series, paths: Paths
) -> Tuple[pd.DataFrame, Dict]:
    """
    Train and evaluate each model on a 75/25 stratified split.

    Returns:
        result_df : DataFrame with per-model metrics
        fitted    : dict mapping model name → fitted sklearn Pipeline
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    results = []
    fitted: Dict[str, Pipeline] = {}

    for name, model in model_candidates().items():
        pre = make_preprocessor(X_train)
        clf = Pipeline([("preprocessor", pre), ("model", model)])
        clf.fit(X_train, y_train)
        fitted[name] = clf

        preds = clf.predict(X_test)
        probs = clf.predict_proba(X_test)[:, 1]

        results.append({
            "model": name,
            "accuracy": round(accuracy_score(y_test, preds), 4),
            "precision": round(precision_score(y_test, preds, zero_division=0), 4),
            "recall": round(recall_score(y_test, preds, zero_division=0), 4),
            "f1": round(f1_score(y_test, preds, zero_division=0), 4),
            "roc_auc": round(roc_auc_score(y_test, probs), 4),
        })

        cm = confusion_matrix(y_test, preds)
        fig, ax = plt.subplots(figsize=(4.5, 4))
        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues", ax=ax,
            xticklabels=["Not at risk", "At risk"],
            yticklabels=["Not at risk", "At risk"],
        )
        ax.set_title(f"Confusion Matrix\n{name.replace('_', ' ').title()}", fontsize=11)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        plt.tight_layout()
        plt.savefig(paths.figures / f"confusion_matrix_{name}.png", dpi=150)
        plt.close()

        (paths.tables / f"classification_report_{name}.txt").write_text(
            classification_report(y_test, preds), encoding="utf-8"
        )

    result_df = pd.DataFrame(results).sort_values("f1", ascending=False)
    result_df.to_csv(paths.tables / "model_comparison.csv", index=False)

    _roc_comparison_chart(fitted, X_test, y_test, paths)

    _precision_recall_chart(fitted, X_test, y_test, paths)

    return result_df, fitted

def _roc_comparison_chart(
    fitted: Dict[str, Pipeline],
    X_test: pd.DataFrame,
    y_test: pd.Series,
    paths: Paths,
) -> None:
    """Overlay ROC curves for all models on a single axes."""
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Random (AUC=0.5)")

    for (name, clf), color in zip(fitted.items(), MODEL_COLORS):
        probs = clf.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, probs)
        auc = roc_auc_score(y_test, probs)
        label = f"{name.replace('_', ' ').title()} (AUC={auc:.3f})"
        ax.plot(fpr, tpr, color=color, linewidth=2, label=label)

    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve — Model Comparison", fontsize=13)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(paths.figures / "roc_curve_comparison.png", dpi=150)
    plt.close()

def _precision_recall_chart(
    fitted: Dict[str, Pipeline],
    X_test: pd.DataFrame,
    y_test: pd.Series,
    paths: Paths,
) -> None:
    """Overlay Precision-Recall curves for all models."""
    fig, ax = plt.subplots(figsize=(6, 5))
    baseline = y_test.mean()
    ax.axhline(baseline, color="gray", linestyle="--", linewidth=1,
               label=f"Baseline precision ({baseline:.2f})")

    for (name, clf), color in zip(fitted.items(), MODEL_COLORS):
        probs = clf.predict_proba(X_test)[:, 1]
        precision, recall, _ = precision_recall_curve(y_test, probs)
        ax.plot(recall, precision, color=color, linewidth=2,
                label=name.replace("_", " ").title())

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve — Model Comparison", fontsize=13)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(paths.figures / "precision_recall_comparison.png", dpi=150)
    plt.close()

def cross_validate_models(
    X: pd.DataFrame, y: pd.Series, paths: Paths, cv_splits: int = 5
) -> pd.DataFrame:
    """
    Stratified k-fold cross-validation across all models.
    More reliable than a single holdout split.
    """
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    records = []

    for name, model in model_candidates().items():
        pre = make_preprocessor(X)
        clf = Pipeline([("preprocessor", pre), ("model", model)])
        scores = cross_validate(
            clf, X, y,
            cv=cv,
            scoring=["accuracy", "f1", "roc_auc"],
            n_jobs=-1,
        )
        records.append({
            "model": name,
            "accuracy_mean": round(float(scores["test_accuracy"].mean()), 4),
            "accuracy_std": round(float(scores["test_accuracy"].std()), 4),
            "f1_mean": round(float(scores["test_f1"].mean()), 4),
            "f1_std": round(float(scores["test_f1"].std()), 4),
            "roc_auc_mean": round(float(scores["test_roc_auc"].mean()), 4),
            "roc_auc_std": round(float(scores["test_roc_auc"].std()), 4),
        })

    out = pd.DataFrame(records).sort_values("f1_mean", ascending=False)
    out.to_csv(paths.tables / "model_cv_scores.csv", index=False)
    return out

def feature_importance_chart(
    X: pd.DataFrame, y: pd.Series, paths: Paths
) -> None:
    """
    Feature importances from the same Pipeline used during evaluation
    (preprocessor + RandomForest).  Readable labels — no num__ / cat__ prefix.
    """
    X_train, _, y_train, _ = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    pre = make_preprocessor(X_train)
    clf = Pipeline([
        ("preprocessor", pre),
        ("model", RandomForestClassifier(n_estimators=300, max_depth=8, random_state=42)),
    ])
    clf.fit(X_train, y_train)

    raw_names = clf.named_steps["preprocessor"].get_feature_names_out()
    clean_names = _clean_feature_names(list(raw_names))
    importances = pd.Series(
        clf.named_steps["model"].feature_importances_, index=clean_names
    ).sort_values(ascending=False).head(20)

    fig, ax = plt.subplots(figsize=(8, 6))
    importances.sort_values(ascending=True).plot(
        kind="barh", ax=ax, color="#2c7fb8", edgecolor="white"
    )
    ax.set_title("Feature Importance — RF Pipeline (top 20)", fontsize=13)
    ax.set_xlabel("Importance")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(paths.figures / "feature_importance_risk.png", dpi=150)
    plt.close()

def shap_analysis(
    X: pd.DataFrame, y: pd.Series, paths: Paths, n_background: int = 100
) -> None:
    """
    SHAP TreeExplainer on the best model (Gradient Boosting).

    Produces:
      - shap_summary_bar.png   : mean absolute SHAP per feature (bar)
      - shap_summary_dot.png   : beeswarm / dot plot (value × impact)
    """
    try:
        import shap
    except ImportError:
        print("  [shap] not installed — skipping SHAP analysis")
        return

    X_train, X_test, y_train, _ = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pre = make_preprocessor(X_train)
    clf = Pipeline([
        ("preprocessor", pre),
        ("model", GradientBoostingClassifier(n_estimators=200, max_depth=4, random_state=42)),
    ])
    clf.fit(X_train, y_train)

    X_test_transformed = clf.named_steps["preprocessor"].transform(X_test)
    raw_names = clf.named_steps["preprocessor"].get_feature_names_out()
    clean_names = _clean_feature_names(list(raw_names))

    explainer = shap.TreeExplainer(clf.named_steps["model"])
    shap_values = explainer.shap_values(X_test_transformed)

    shap.summary_plot(
        shap_values, X_test_transformed,
        feature_names=clean_names,
        plot_type="bar",
        max_display=15,
        show=False,
    )
    plt.title("SHAP — Mean |Feature Impact| (Gradient Boosting)", fontsize=12)
    plt.tight_layout()
    plt.savefig(paths.figures / "shap_summary_bar.png", dpi=150, bbox_inches="tight")
    plt.close()

    shap.summary_plot(
        shap_values, X_test_transformed,
        feature_names=clean_names,
        max_display=15,
        show=False,
    )
    plt.title("SHAP — Feature Impact Direction (Gradient Boosting)", fontsize=12)
    plt.tight_layout()
    plt.savefig(paths.figures / "shap_summary_dot.png", dpi=150, bbox_inches="tight")
    plt.close()

def risk_score_preview(df: pd.DataFrame, paths: Paths) -> pd.DataFrame:
    """
    Heuristic risk score (0–100) for human-readable preview.
    G3 is used here for display only — not for model training.

    Score weights:
      45% absence component   (absences / 20, capped)
      35% grade component     (how far below 20)
      20% trend component     (G1 → G2 decline)
    """
    preview = df.copy()
    score = (
        0.45 * np.clip(preview["absences"] / 20, 0, 1)
        + 0.35 * np.clip((20 - preview["G3"]) / 20, 0, 1)
        + 0.20 * np.clip((preview["G1"] - preview["G2"]) / 20, 0, 1)
    ) * 100
    preview["risk_score"] = score.round(1)
    preview["risk_level"] = pd.cut(
        preview["risk_score"],
        bins=[-1, 35, 65, 100],
        labels=["low", "medium", "high"],
    )
    cols = ["school", "sex", "age", "absences", "G1", "G2", "G3",
            "risk_score", "risk_level"]
    out = preview[cols].sort_values("risk_score", ascending=False).head(30)
    out.to_csv(paths.tables / "risk_score_preview.csv", index=False)
    return out

def run_pipeline(base_dir: Path) -> None:
    """
    Full pipeline:
      1. Download & load data
      2. Feature engineering
      3. EDA plots
      4. Model evaluation (holdout) + ROC + PR curves
      5. Cross-validation
      6. Feature importance
      7. SHAP analysis
      8. Risk score preview table
    """
    paths = Paths(root=base_dir)
    paths.ensure()

    print("── 1. Loading data ──────────────────────────────────────────")
    raw_df = download_and_load_uci(paths)
    raw_df.to_csv(paths.data_processed / "uci_merged.csv", index=False)
    print(f"   Loaded {len(raw_df)} rows × {raw_df.shape[1]} cols "
          f"(mat={len(raw_df[raw_df.course=='mat'])}, "
          f"por={len(raw_df[raw_df.course=='por'])})")

    print("── 2. Feature engineering ───────────────────────────────────")
    X, y = build_features(raw_df)
    print(f"   X: {X.shape}  |  y positives: {y.sum()} / {len(y)} "
          f"({y.mean():.1%})")

    print("── 3. EDA plots ─────────────────────────────────────────────")
    eda_plots(raw_df, y, paths)

    print("── 4. Model evaluation (holdout) ────────────────────────────")
    model_table, fitted_models = evaluate_models(X, y, paths)
    print(model_table.to_string(index=False))

    print("── 5. Cross-validation ──────────────────────────────────────")
    cv_table = cross_validate_models(X, y, paths)
    print(cv_table[["model", "f1_mean", "f1_std"]].to_string(index=False))

    print("── 6. Feature importance ─────────────────────────────────────")
    feature_importance_chart(X, y, paths)

    print("── 7. SHAP analysis ──────────────────────────────────────────")
    shap_analysis(X, y, paths)

    print("── 8. Risk score preview ─────────────────────────────────────")
    risk_preview = risk_score_preview(raw_df, paths)

    print("── 9. Social EDA (extended features) ────────────────────────")
    eda_social_features(raw_df, y, paths)

    print("── 10. Base vs Extended feature set comparison ───────────────")
    cmp_df, winner_meta = feature_set_comparison(raw_df, paths)
    print(cmp_df[["feature_set", "model", "f1", "roc_auc"]].to_string(index=False))

    print("\nPipeline complete.")
    print(f"   Figures saved to : {paths.figures}")
    print(f"   Tables saved to  : {paths.tables}")
    print("\nTop 10 at-risk students (heuristic score):")
    print(risk_preview.head(10).to_string(index=False))

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    run_pipeline(project_root)
