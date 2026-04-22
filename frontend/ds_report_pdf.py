"""
UCI data-science narrative + figures as a single PDF (TR or EN), using matplotlib only.
"""
from __future__ import annotations

import io
import json
import textwrap
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

from frontend.i18n import t

Lang = Literal["tr", "en"]


def _plain(s: str) -> str:
    return (s or "").replace("**", "").replace("`", "")


def _text_pages(pdf: PdfPages, title: str, body: str, lang: Lang) -> None:
    body_plain = _plain(body)
    lines: list[str] = []
    for para in body_plain.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if p.startswith("|"):
            for ln in p.splitlines():
                lines.append(ln)
            lines.append("")
            continue
        lines.extend(textwrap.wrap(p, width=92, break_long_words=True, replace_whitespace=False))
        lines.append("")

    if not lines:
        lines = [""]

    max_lines = 36
    cont_tr, cont_en = "(devam)", "(continued)"
    cont = cont_tr if lang == "tr" else cont_en
    for start in range(0, len(lines), max_lines):
        chunk = lines[start : start + max_lines]
        page_title = title if start == 0 else f"{title} {cont}"
        fig = plt.figure(figsize=(8.27, 11.69))
        ax = fig.add_axes((0.08, 0.06, 0.84, 0.88))
        ax.axis("off")
        ax.text(
            0,
            1,
            page_title + "\n\n" + "\n".join(chunk),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            family="DejaVu Sans",
        )
        pdf.savefig(fig)
        plt.close(fig)


def _image_page(pdf: PdfPages, path: Path, subtitle: str | None = None) -> None:
    if not path.is_file():
        return
    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_axes((0.06, 0.10 if subtitle else 0.06, 0.88, 0.82 if subtitle else 0.88))
    ax.axis("off")
    img = mpimg.imread(str(path))
    ax.imshow(img, aspect="auto")
    if subtitle:
        fig.text(0.5, 0.96, subtitle, ha="center", fontsize=10, family="DejaVu Sans", wrap=True)
    pdf.savefig(fig)
    plt.close(fig)


def _two_images_page(pdf: PdfPages, left: Path, right: Path, title: str) -> None:
    if not left.is_file() and not right.is_file():
        return
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 8.27))
    ax_list = np.atleast_1d(axes).ravel()
    fig.suptitle(title, fontsize=11, family="DejaVu Sans")
    for ax, p in zip(ax_list, (left, right)):
        ax.axis("off")
        if p.is_file():
            ax.imshow(mpimg.imread(str(p)), aspect="auto")
        else:
            ax.text(0.5, 0.5, "—", ha="center", va="center", transform=ax.transAxes)
    plt.tight_layout(rect=(0, 0, 1, 0.94))
    pdf.savefig(fig)
    plt.close(fig)


def _confusion_grid_pages(pdf: PdfPages, figures_dir: Path) -> None:
    files = sorted(figures_dir.glob("confusion_matrix_*.png"))
    if not files:
        return
    batch = 4
    for start in range(0, len(files), batch):
        chunk = files[start : start + batch]
        n = len(chunk)
        if n == 1:
            fig, ax = plt.subplots(1, 1, figsize=(8.27, 8.27))
            axes_list = [ax]
        elif n == 2:
            fig, axes_list = plt.subplots(1, 2, figsize=(11.69, 5.5))
            axes_list = list(np.atleast_1d(axes_list).ravel())
        elif n == 3:
            fig, axes_list = plt.subplots(1, 3, figsize=(14, 4.5))
            axes_list = list(np.atleast_1d(axes_list).ravel())
        else:
            fig, axes_list = plt.subplots(2, 2, figsize=(11.69, 11.69))
            axes_list = list(np.atleast_1d(axes_list).ravel())
        for ax in axes_list:
            ax.axis("off")
        for ax, p in zip(axes_list, chunk):
            ax.imshow(mpimg.imread(str(p)), aspect="auto")
            label = p.stem.replace("confusion_matrix_", "").replace("_", " ").title()
            ax.set_title(label, fontsize=8, family="DejaVu Sans")
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)


def _model_comparison_page(pdf: PdfPages, tables_dir: Path, lang: Lang) -> None:
    cmp_path = tables_dir / "model_comparison.csv"
    if not cmp_path.is_file():
        return
    cmp_df = pd.read_csv(cmp_path)
    metrics = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(metrics))
    bar_width = 0.22
    palette = ["#4C72B0", "#DD8452", "#55A868"]
    for i, (_, row) in enumerate(cmp_df.iterrows()):
        ax.bar(
            x + i * bar_width,
            [float(row[m]) for m in metrics],
            bar_width,
            label=str(row["model"]).replace("_", " ").title(),
            color=palette[i % len(palette)],
        )
    ax.set_xticks(x + bar_width)
    ax.set_xticklabels([m.upper() for m in metrics], fontsize=9)
    ax.set_ylim(0.75, 1.02)
    ax.set_ylabel("Score")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.set_title(t("ds_model_cmp", lang), fontsize=11, family="DejaVu Sans")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def build_uci_ds_report_pdf(
    *,
    lang: str,
    project_root: Path,
) -> bytes:
    lng: Lang = "en" if (lang or "").lower() == "en" else "tr"
    figures_dir = project_root / "data_science" / "reports" / "figures"
    tables_dir = project_root / "data_science" / "reports" / "tables"
    models_dir = project_root / "data_science" / "models"
    winner_meta_path = models_dir / "winner_meta.json"

    bio = io.BytesIO()
    with PdfPages(bio) as pdf:
        title = t("ds_pdf_cover_title", lng)
        subtitle = t("ds_pdf_cover_sub", lng)
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.5, 0.55, title, ha="center", va="center", fontsize=18, weight="bold", family="DejaVu Sans")
        fig.text(0.5, 0.45, subtitle, ha="center", va="center", fontsize=10, family="DejaVu Sans", wrap=True)
        fig.text(0.5, 0.12, t("ds_figures_source_note", lng), ha="center", va="center", fontsize=8, family="DejaVu Sans", wrap=True)
        pdf.savefig(fig)
        plt.close(fig)

        _text_pages(pdf, t("ds_journey_header", lng), t("ds_journey_body", lng), lng)
        _text_pages(pdf, t("ds_pdf_leakage_title", lng), t("ds_leakage_note", lng), lng)

        _text_pages(pdf, t("ds_dataset_header", lng), t("ds_dataset_body", lng), lng)

        pair_title = t("ds_pdf_section_eda", lng)
        _two_images_page(
            pdf,
            figures_dir / "eda_social_parent_edu.png",
            figures_dir / "eda_social_demographic.png",
            pair_title,
        )
        _two_images_page(
            pdf,
            figures_dir / "eda_grade_distributions.png",
            figures_dir / "eda_absence_distribution.png",
            t("ds_pdf_section_grades_abs", lng),
        )

        _text_pages(pdf, t("ds_why_base_won_header", lng), t("ds_why_base_won_body", lng), lng)
        _text_pages(pdf, t("ds_selection_header", lng), t("ds_selection_blurb", lng), lng)

        _image_page(pdf, figures_dir / "feature_set_comparison.png", t("ds_selection_header", lng))

        cmp_fs_path = tables_dir / "feature_set_comparison.csv"
        if cmp_fs_path.is_file():
            df = pd.read_csv(cmp_fs_path)
            preview = df.to_string(index=False, max_rows=24)
            _text_pages(pdf, t("ds_raw_table", lng) + " — Base vs Extended", preview, lng)

        if winner_meta_path.is_file():
            try:
                wm = json.loads(winner_meta_path.read_text(encoding="utf-8"))
                wm_txt = json.dumps(wm, indent=2, ensure_ascii=False)
                _text_pages(pdf, t("ds_winner_header", lng), wm_txt + "\n\n" + _plain(t("ds_winner_reason", lng)), lng)
            except Exception:
                pass

        _two_images_page(
            pdf,
            figures_dir / "eda_social_alcohol.png",
            figures_dir / "eda_social_family_health.png",
            t("ds_social_eda_header", lng),
        )

        _text_pages(pdf, t("ds_algo_header", lng), t("ds_algo_body", lng), lng)
        _text_pages(pdf, t("ds_risk_col_header", lng), t("ds_risk_col_body", lng), lng)
        _text_pages(pdf, t("ds_two_scores_header", lng), t("ds_two_scores_body", lng), lng)
        _text_pages(pdf, t("ds_deployed_header", lng), t("ds_deployed_note", lng), lng)

        cmp_path = tables_dir / "model_comparison.csv"
        if cmp_path.is_file():
            _model_comparison_page(pdf, tables_dir, lng)
            cmp_df = pd.read_csv(cmp_path)
            _text_pages(pdf, t("ds_model_cmp", lng), cmp_df.to_string(index=False), lng)

        cv_path = tables_dir / "model_cv_scores.csv"
        if cv_path.is_file():
            cv_df = pd.read_csv(cv_path)
            _text_pages(pdf, t("ds_cv", lng), cv_df.to_string(index=False), lng)

        _confusion_grid_pages(pdf, figures_dir)

        _image_page(pdf, figures_dir / "feature_importance_risk.png", t("ds_feat_imp", lng))

        rsp_path = tables_dir / "risk_score_preview.csv"
        if rsp_path.is_file():
            rsp_df = pd.read_csv(rsp_path)
            head = rsp_df.head(25).to_string(index=False)
            note = (
                "Heuristik önizleme (UCI) — ilk 25 satır."
                if lng == "tr"
                else "Heuristic preview (UCI) — first 25 rows."
            )
            _text_pages(pdf, t("ds_risk_preview", lng), note + "\n\n" + head, lng)

        shap_files = sorted(figures_dir.glob("shap_*.png")) if figures_dir.is_dir() else []
        for p in shap_files:
            _image_page(pdf, p, p.stem.replace("shap_", "").replace("_", " ").title())

        report_files = sorted(tables_dir.glob("classification_report_*.txt")) if tables_dir.is_dir() else []
        for p in report_files[:3]:
            label = p.stem.replace("classification_report_", "").replace("_", " ").title()
            txt = p.read_text(encoding="utf-8", errors="replace")
            if len(txt) > 12000:
                txt = txt[:12000] + "\n…"
            _text_pages(pdf, t("ds_class_report", lng) + f" — {label}", txt, lng)

    bio.seek(0)
    return bio.read()
