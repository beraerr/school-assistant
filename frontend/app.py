from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional

import pandas as pd
import requests
import streamlit as st

from frontend.i18n import role_name, t

try:
    import matplotlib.pyplot as plt
    import numpy as np
    _DS_AVAILABLE = True
except ImportError:
    _DS_AVAILABLE = False

Lang = Literal["tr", "en"]

if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "tr"

st.set_page_config(
    page_title="Akıllı Okul Bilgi Sistemi / Smart School",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DS_FIGURES = PROJECT_ROOT / "data_science" / "reports" / "figures"
DS_TABLES = PROJECT_ROOT / "data_science" / "reports" / "tables"
DS_REPORTS_ROOT = PROJECT_ROOT / "data_science" / "reports"

def lang() -> Lang:
    return st.session_state.ui_lang  # type: ignore[return-value]

with st.sidebar:
    st.session_state.ui_lang = st.radio(
        "Dil / Language",
        options=["tr", "en"],
        index=0 if st.session_state.get("ui_lang", "tr") == "tr" else 1,
        horizontal=True,
        format_func=lambda x: "TR" if x == "tr" else "EN",
    )

L = lang()

st.sidebar.markdown("---")
API_BASE_URL = st.sidebar.text_input(
    t("api_url", L),
    value="http://localhost:8000",
    help="FastAPI backend URL",
)

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "query_running" not in st.session_state:
    st.session_state.query_running = False

def login(username: str, password: str) -> bool:
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data["access_token"]
            st.session_state.user = data["user"]
            return True
        detail = response.json().get("detail", "Unknown")
        st.error(f"{t('login_error', L)} / {detail}")
        return False
    except Exception as e:
        st.error(f"{t('conn_error', L)}: {e}")
        return False

def execute_query(query: str, ui_lang: Lang) -> Optional[dict]:
    if not st.session_state.access_token:
        st.error(t("need_login", L))
        return None
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        response = requests.post(
            f"{API_BASE_URL}/query/",
            json={"query": query, "ui_lang": ui_lang},
            headers=headers,
            timeout=120,
        )
        if response.status_code == 200:
            return response.json()
        detail = response.json().get("detail", "Unknown")
        st.error(f"{t('query_error', L)}: {detail}")
        return None
    except Exception as e:
        st.error(f"{t('conn_error', L)}: {e}")
        return None

def execute_query_with_spinner(query: str, ui_lang: Lang) -> Optional[dict]:
    st.session_state.query_running = True
    try:
        with st.spinner(t("chat_thinking", ui_lang)):
            return execute_query(query, ui_lang)
    finally:
        st.session_state.query_running = False

def get_student_risks(class_name: Optional[str] = None) -> Optional[dict]:
    if not st.session_state.access_token:
        st.error(t("need_login", L))
        return None
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        params = {}
        if class_name:
            params["class_name"] = class_name
        response = requests.get(
            f"{API_BASE_URL}/risk/students",
            params=params,
            headers=headers,
            timeout=60,
        )
        if response.status_code == 200:
            return response.json()
        detail = response.json().get("detail", "Unknown")
        st.error(f"{t('risk_error', L)}: {detail}")
        return None
    except Exception as e:
        st.error(f"{t('conn_error', L)}: {e}")
        return None

def example_queries_for_role(role: str, lng: Lang) -> list[str]:
    examples: dict[str, dict[str, list[str]]] = {
        "principal": {
            "tr": [
                "Bu ay devamsızlığı 5 günü geçen öğrencileri göster",
                "Devamsızlık oranı en yüksek sınıflar hangileri?",
                "Sınıfların not ortalamalarını göster",
                "Risk skoru en yüksek öğrencileri göster",
            ],
            "en": [
                "Show students with more than 5 absences this month",
                "Which classes have the highest absence rates?",
                "Show average grades for all classes",
                "Show students with the highest risk scores",
            ],
        },
        "teacher": {
            "tr": [
                "Bu ay devamsızlığı 5 günü geçen öğrencileri göster",
                "Sınıfımdaki öğrencilerin matematik notlarını listele",
                "En yüksek not alan öğrencileri göster",
                "Sınıfımda risk skoru en yüksek öğrencileri göster",
            ],
            "en": [
                "Show students with more than 5 absences this month",
                "List mathematics grades for students in my class",
                "Show the students with the highest grades",
                "Show students with the highest risk scores in my class",
            ],
        },
        "parent": {
            "tr": [
                "Çocuğumun matematik notları geçen aya göre nasıl değişti?",
                "Çocuğumun bu ayki devamsızlık durumu nedir?",
                "Çocuğumun tüm ders notlarını göster",
                "Risk skoruna göre çocuğumun dönem sonu başarı beklentisi nasıl?",
                "Matematikte başarı görme olasılığı nedir (risk skoruyla)?",
            ],
            "en": [
                "How did my child's math grades change compared to last month?",
                "What is my child's attendance situation this month?",
                "Show all of my child's course grades",
                "Based on the risk score, what is my child's end-of-term success outlook?",
                "What is the likelihood of doing well in mathematics (using the risk score)?",
            ],
        },
        "student": {
            "tr": [
                "Benim matematik notlarım geçen aya göre nasıl değişti?",
                "Bu ayki devamsızlık durumum nedir?",
                "Tüm ders notlarımı göster",
                "Risk skoruma göre dönem sonu başarı beklentim nasıl?",
                "Matematikte başarı şansım nedir (risk skoruyla)?",
            ],
            "en": [
                "How did my math grades change compared to last month?",
                "What is my attendance situation this month?",
                "Show all of my course grades",
                "Based on my risk score, what is my end-of-term success outlook?",
                "What is my chance of doing well in mathematics (using the risk score)?",
            ],
        },
    }
    block = examples.get(role) or {}
    role_examples = list(block.get(lng) or block.get("tr") or [])
    common_examples = {
        "tr": [
            "Sen kimsin?",
            "Kullanılma amacın nedir?",
            "AI workflow kullanıyor musun?",
            "Winner model risk skorunda nasıl seçiliyor?",
            "Bir öğrencinin risk skorunu değerlendirince ne önerirsin?",
        ],
        "en": [
            "Who are you?",
            "What is your purpose?",
            "How does your AI workflow operate?",
            "How is the winner model selected for risk scoring?",
            "When you evaluate a student's risk score, what recommendations do you give?",
        ],
    }
    role_examples.extend(common_examples.get(lng) or common_examples["tr"])
    return role_examples

def pack_query_assistant_turn(result: dict, lng: Lang) -> Dict[str, Any]:
    """Markdown + optional DataFrame for one assistant reply from `/query/` JSON."""
    mode = result.get("conversation_mode") or "sql"
    lines: list[str] = []
    expl = (result.get("explanation") or "").strip()
    if expl:
        lines.append(expl)
    if mode == "sql":
        if result.get("permissions_applied"):
            lines.append(
                f"\n\n> **{t('perm_label', lng)}:** {result.get('permission_reason', '')}"
            )
        if result.get("sql_query"):
            lines.append(f"\n\n```sql\n{result['sql_query'].strip()}\n```")
    rows = result.get("results") or []
    df = pd.DataFrame(rows) if rows and mode == "sql" else None
    text = "\n".join(lines).strip() or "…"
    return {"md": text, "df": df}

def report_download_candidates() -> list[Path]:
    patterns = ("*.pdf", "*.docx", "*.txt", "*.csv", "*.png")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(DS_REPORTS_ROOT.rglob(pattern))
    return sorted(files, key=lambda p: str(p).lower())

def mime_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".png": "image/png",
    }.get(suffix, "application/octet-stream")

st.title(t("page_title", L))
st.caption("Türkçe + English UI | Aynı backend")
st.markdown("---")

if st.session_state.access_token is None:
    st.header(t("login_header", L))
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input(t("username", L), key="login_username")
        password = st.text_input(t("password", L), type="password", key="login_password")
        if st.button(t("login_btn", L), type="primary"):
            if username and password:
                if login(username, password):
                    st.session_state.chat_history = []
                    st.session_state.pop("query_pending", None)
                    st.success(t("login_ok", L))
                    st.rerun()
            else:
                st.warning(t("login_need_creds", L))
    with col2:
        st.info(t("login_ds_access_notice", L))
        st.info(t("demo_users", L))

else:
    user = st.session_state.user

    with st.sidebar:
        st.header(t("user_info", L))
        st.write(f"**{t('user_label', L)}:** {user['username']}")
        st.write(f"**{t('role_label', L)}:** {role_name(user['role'], L)}")
        if user.get("related_class"):
            st.write(f"**{t('class_label', L)}:** {user['related_class']}")
        st.markdown("---")
        if st.button(t("logout", L)):
            st.session_state.access_token = None
            st.session_state.user = None
            st.session_state.pop("chat_history", None)
            st.session_state.pop("query_pending", None)
            st.rerun()

    is_principal = user["role"] == "principal"
    tab_labels = [t("tab_query", L), t("tab_risk", L)]
    if is_principal:
        tab_labels.append(t("tab_ds", L))
    else:
        tab_labels.append(t("tab_ds_locked", L))
    query_tab, risk_tab, ds_tab = st.tabs(tab_labels)

    with query_tab:
        st.header(t("query_header", L))
        st.markdown(t("query_help", L))
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        role = user["role"]
        ex = example_queries_for_role(role, L)
        if ex:
            with st.expander(t("example_queries", L)):
                for i, example in enumerate(ex):
                    if st.button(
                        example,
                        key=f"example_{i}",
                        use_container_width=True,
                        disabled=st.session_state.query_running,
                    ):
                        st.session_state.query_pending = example
                        st.rerun()

        if st.session_state.get("query_pending"):
            pending_q = st.session_state.query_pending
            st.session_state.query_pending = None
            pending_res = execute_query_with_spinner(pending_q, L)
            if pending_res:
                st.session_state.chat_history.append({"role": "user", "content": pending_q})
                packed = pack_query_assistant_turn(pending_res, L)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": packed["md"], "df": packed["df"]}
                )
                st.rerun()

        for i, turn in enumerate(st.session_state.chat_history):
            with st.chat_message(turn["role"]):
                st.markdown(turn["content"])
                df_turn = turn.get("df")
                if df_turn is not None:
                    if df_turn.empty:
                        st.info(t("empty_results", L))
                    else:
                        st.dataframe(df_turn, use_container_width=True)
                        csv = df_turn.to_csv(index=False).encode("utf-8-sig")
                        st.download_button(
                            label=t("download_csv", L),
                            data=csv,
                            file_name="query_results.csv",
                            mime="text/csv",
                            key=f"csv_dl_{i}",
                        )

        c_clear, _ = st.columns([1, 5])
        with c_clear:
            if st.button(
                t("chat_clear", L),
                key="chat_clear_btn",
                disabled=st.session_state.query_running,
            ):
                st.session_state.chat_history = []
                st.rerun()

        if prompt := st.chat_input(
            t("chat_input_placeholder", L),
            disabled=st.session_state.query_running,
        ):
            res = execute_query_with_spinner(prompt, L)
            if res:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                packed = pack_query_assistant_turn(res, L)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": packed["md"], "df": packed["df"]}
                )
                st.rerun()

    with risk_tab:
        st.header(t("risk_header", L))

        with st.expander(t("risk_method_header", L), expanded=False):
            st.markdown(t("risk_method_ml", L))
            st.markdown(t("risk_method_target", L))

        selected_class = ""
        if user["role"] == "principal":
            selected_class = st.text_input(t("class_filter", L), value="")
        if st.button(t("risk_refresh", L), key="risk_refresh", type="primary"):
            st.session_state["risk_refresh_triggered"] = True

        if st.session_state.get("risk_refresh_triggered", True):
            with st.spinner(t("risk_loading", L)):
                risk_result = get_student_risks(selected_class if selected_class else None)

            if risk_result and risk_result.get("items"):
                items = risk_result["items"]
                has_ml = any(i.get("ml_risk_score") is not None for i in items)

                n_high   = sum(1 for i in items if i["risk_level"] == "high")
                n_medium = sum(1 for i in items if i["risk_level"] == "medium")
                n_low    = sum(1 for i in items if i["risk_level"] == "low")
                n_ml_high = sum(1 for i in items if i.get("ml_risk_level") == "high")

                mc = st.columns(4)
                mc[0].metric("High risk (ML)", n_high)
                mc[1].metric("Medium (ML)", n_medium)
                mc[2].metric("Low (ML)", n_low)
                if has_ml:
                    mc[3].metric("High risk (ML/GBM)", n_ml_high)

                rows = []
                for item in items:
                    row = {
                        t("col_student", L): item["student_name"],
                        t("col_class", L):   item["class_name"],
                        t("col_score", L):   item["risk_score"],
                        t("col_level", L):   item["risk_level"],
                        t("col_expl", L):    item["explanation"],
                    }
                    if has_ml:
                        row[t("col_ml_score", L)] = item.get("ml_risk_score")
                        row[t("col_ml_level", L)] = item.get("ml_risk_level")
                        row[t("col_ml_date", L)]  = item.get("ml_computed_at")
                    rows.append(row)

                df_risk = pd.DataFrame(rows)

                level_col = t("col_level", L)
                ml_level_col = t("col_ml_level", L)

                def _colour_level(val: str) -> str:
                    return {
                        "high":   "background-color:#ffcccc; color:#7b0000; font-weight:bold",
                        "medium": "background-color:#fff3cc; color:#7b5800; font-weight:bold",
                        "low":    "background-color:#ccffcc; color:#0a4a00; font-weight:bold",
                    }.get(str(val).lower(), "")

                style_cols = [level_col]
                if has_ml and ml_level_col in df_risk.columns:
                    style_cols.append(ml_level_col)

                styled_df = df_risk.style.map(_colour_level, subset=style_cols)
                st.dataframe(styled_df, use_container_width=True)

                if not has_ml:
                    st.caption(t("risk_ml_note", L))

                top = items[0]
                st.warning(
                    f"{top['student_name']} ({top['class_name']}) — "
                    f"ML: {top['risk_score']}/100 ({top['risk_level']})"
                    + f"  —  {top['explanation']}"
                )

            elif risk_result:
                st.info(t("risk_none", L))

    with ds_tab:
        if not is_principal:
            st.warning(t("ds_access_denied", L))
            st.stop()

        st.header(t("ds_header", L))
        st.caption(t("ds_figures_source_note", L))

        st.subheader(t("ds_download_header", L))
        st.markdown(t("ds_download_blurb", L))
        downloadable_files = report_download_candidates()
        if downloadable_files:
            for i, report_file in enumerate(downloadable_files):
                col_name, col_action = st.columns([4, 1])
                with col_name:
                    st.code(str(report_file.relative_to(PROJECT_ROOT)))
                with col_action:
                    st.download_button(
                        label=t("download_file_btn", L),
                        data=report_file.read_bytes(),
                        file_name=report_file.name,
                        mime=mime_type_for(report_file),
                        key=f"dl_report_{i}",
                        use_container_width=True,
                    )
        else:
            st.info(t("ds_no_downloadables", L))

        st.divider()

        st.subheader(t("ds_journey_header", L))
        st.markdown(t("ds_journey_body", L))
        st.caption(t("ds_leakage_note", L))

        st.divider()
        st.subheader(t("ds_dataset_header", L))
        st.markdown(t("ds_dataset_body", L))

        social_figs_early = [
            ("eda_social_parent_edu.png",
             "TR: Ebeveyn Eğitimi → Risk  /  EN: Parent Education → Risk"),
            ("eda_social_demographic.png",
             "TR: Demografik Faktörler → Risk  /  EN: Demographic Factors → Risk"),
        ]
        available_early = [(fn, cap) for fn, cap in social_figs_early
                           if (DS_FIGURES / fn).exists()]
        if available_early:
            cols_soc = st.columns(len(available_early))
            for col, (fn, cap) in zip(cols_soc, available_early):
                with col:
                    st.image(str(DS_FIGURES / fn), caption=cap, use_container_width=True)

        eda_main_figs = [
            ("eda_grade_distributions.png", "Not Dağılımı / Grade Distributions"),
            ("eda_absence_distribution.png", "Devamsızlık Dağılımı / Absence Distribution"),
        ]
        available_eda = [(fn, cap) for fn, cap in eda_main_figs
                         if (DS_FIGURES / fn).exists()]
        if available_eda:
            cols_eda = st.columns(len(available_eda))
            for col, (fn, cap) in zip(cols_eda, available_eda):
                with col:
                    st.image(str(DS_FIGURES / fn), caption=cap, use_container_width=True)

        st.divider()
        st.subheader(t("ds_why_base_won_header", L))
        st.markdown(t("ds_why_base_won_body", L))

        st.subheader(t("ds_selection_header", L))
        st.markdown(t("ds_selection_blurb", L))

        cmp_fs_path = DS_TABLES / "feature_set_comparison.csv"
        winner_meta_path = DS_FIGURES.parent.parent / "models" / "winner_meta.json"

        if not cmp_fs_path.exists():
            st.info(t("ds_no_comparison", L))
        else:
            import json as _json
            cmp_fs = pd.read_csv(cmp_fs_path)

            fs_fig_path = DS_FIGURES / "feature_set_comparison.png"
            if fs_fig_path.exists():
                st.image(str(fs_fig_path), use_container_width=True)

            st.markdown(f"**{t('ds_delta_header', L)}**")
            base_rows = cmp_fs[cmp_fs["feature_set"] == "base"].set_index("model")
            ext_rows  = cmp_fs[cmp_fs["feature_set"] == "extended"].set_index("model")
            common_idx = base_rows.index.intersection(ext_rows.index)
            if not common_idx.empty:
                delta_df = (ext_rows.loc[common_idx, ["f1", "roc_auc", "accuracy"]]
                            - base_rows.loc[common_idx, ["f1", "roc_auc", "accuracy"]]).round(4)
                delta_df.columns = ["ΔF1", "ΔROC-AUC", "ΔAccuracy"]
                delta_df.index = [i.replace("_", " ").title() for i in delta_df.index]

                def _colour_delta(v):
                    try:
                        fv = float(v)
                        if fv > 0.005:
                            return "color: #2ca02c; font-weight:bold"
                        if fv < -0.005:
                            return "color: #d62728"
                        return ""
                    except Exception:
                        return ""

                st.dataframe(
                    delta_df.style.map(_colour_delta),
                    use_container_width=True,
                )

            with st.expander(t("ds_raw_table", L) + " (Base vs Extended)"):
                st.dataframe(cmp_fs, use_container_width=True)

            if winner_meta_path.exists():
                try:
                    wm = _json.loads(winner_meta_path.read_text(encoding="utf-8"))
                    st.success(
                        f"**{t('ds_winner_header', L)}** ·  "
                        f"{t('ds_winner_feature_set', L)}: `{wm['feature_set'].upper()}`  ·  "
                        f"{t('ds_winner_algorithm', L)}: `{wm['model'].replace('_', ' ').title()}`  ·  "
                        f"F1: `{wm['f1']:.4f}`  ·  ROC-AUC: `{wm['roc_auc']:.4f}`"
                    )
                    st.caption(t("ds_winner_reason", L))
                    wm_cols = st.columns(5)
                    wm_cols[0].metric(t("ds_winner_feature_set", L), wm["feature_set"].upper())
                    wm_cols[1].metric(t("ds_winner_algorithm", L), wm["model"].replace("_", " ").title())
                    wm_cols[2].metric("F1",       f"{wm['f1']:.4f}")
                    wm_cols[3].metric("ROC-AUC",  f"{wm['roc_auc']:.4f}")
                    wm_cols[4].metric("Accuracy", f"{wm['accuracy']:.4f}")
                except Exception:
                    pass

            social_figs_remaining = [
                ("eda_social_alcohol.png",
                 "TR: Alkol Tüketimi → Risk  /  EN: Alcohol Consumption → Risk"),
                ("eda_social_family_health.png",
                 "TR: Aile & Sağlık → Risk  /  EN: Family & Health → Risk"),
            ]
            avail_remaining = [(fn, cap) for fn, cap in social_figs_remaining
                               if (DS_FIGURES / fn).exists()]
            if avail_remaining:
                st.subheader(t("ds_social_eda_header", L))
                for fn, cap in avail_remaining:
                    st.image(str(DS_FIGURES / fn), caption=cap, use_container_width=True)

        st.divider()
        st.subheader(t("ds_algo_header", L))
        st.markdown(t("ds_algo_body", L))

        st.divider()
        st.subheader(t("ds_risk_col_header", L))
        st.markdown(t("ds_risk_col_body", L))

        st.subheader(t("ds_two_scores_header", L))
        st.markdown(t("ds_two_scores_body", L))

        st.info(
            f"**{t('ds_deployed_header', L)}** — {t('ds_deployed_note', L)}"
        )

        st.divider()
        cmp_path = DS_TABLES / "model_comparison.csv"
        any_report = cmp_path.exists()

        if not any_report:
            st.warning(t("ds_pipeline_missing", L))
        else:
            st.subheader(t("ds_model_cmp", L))
            cmp_df = pd.read_csv(cmp_path)
            metrics = ["accuracy", "precision", "recall", "f1", "roc_auc"]

            best = cmp_df.iloc[0]
            card_cols = st.columns(5)
            card_cols[0].metric(t("ds_best_model", L), best["model"].replace("_", " ").title())
            card_cols[1].metric("F1", f"{best['f1']:.3f}")
            card_cols[2].metric("ROC-AUC", f"{best['roc_auc']:.3f}")
            card_cols[3].metric("Precision", f"{best['precision']:.3f}")
            card_cols[4].metric("Recall", f"{best['recall']:.3f}")

            if _DS_AVAILABLE:
                fig, ax = plt.subplots(figsize=(10, 4))
                x = np.arange(len(metrics))
                bar_width = 0.22
                palette = ["#4C72B0", "#DD8452", "#55A868"]
                for i, (_, row) in enumerate(cmp_df.iterrows()):
                    ax.bar(
                        x + i * bar_width,
                        [row[m] for m in metrics],
                        bar_width,
                        label=row["model"].replace("_", " ").title(),
                        color=palette[i % len(palette)],
                    )
                ax.set_xticks(x + bar_width)
                ax.set_xticklabels([m.upper() for m in metrics], fontsize=9)
                ax.set_ylim(0.75, 1.02)
                ax.set_ylabel("Score")
                ax.legend(fontsize=9)
                ax.grid(axis="y", alpha=0.3)
                ax.set_title(t("ds_model_cmp", L))
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            with st.expander(t("ds_raw_table", L)):
                st.dataframe(cmp_df, use_container_width=True)

            cv_path = DS_TABLES / "model_cv_scores.csv"
            if cv_path.exists():
                st.subheader(t("ds_cv", L))
                _cv_note = (
                    "5 katlı Stratified CV: veri 5 eşit parçaya bölünür, "
                    "her seferinde 4 parça eğitim, 1 parça test olarak kullanılır. "
                    "**Standart sapma (std) küçükse** model tutarlı demektir — "
                    "tek bir şanslı bölünmeye bağlı değildir."
                    if L == "tr" else
                    "5-fold Stratified CV: data is split into 5 equal parts, "
                    "4 parts train and 1 tests each time. "
                    "**Small standard deviation (std)** means the model is consistent — "
                    "not dependent on a lucky single split."
                )
                st.caption(_cv_note)
                cv_df = pd.read_csv(cv_path)
                st.dataframe(cv_df, use_container_width=True)

            cm_files = sorted(DS_FIGURES.glob("confusion_matrix_*.png")) if DS_FIGURES.is_dir() else []
            if cm_files:
                st.subheader(t("ds_conf_mat", L))
                cm_cols = st.columns(len(cm_files))
                for col, p in zip(cm_cols, cm_files):
                    model_label = (
                        p.stem.replace("confusion_matrix_", "").replace("_", " ").title()
                    )
                    with col:
                        st.image(str(p), caption=model_label, use_container_width=True)

            fi_path = DS_FIGURES / "feature_importance_risk.png"
            if fi_path.exists():
                st.subheader(t("ds_feat_imp", L))
                _fi_note = (
                    "Grafik, Random Forest pipeline'ının her özelliğe atadığı ortalama bilgi kazancını gösterir. "
                    "Yüksek değer = o özellik olmadan model çok daha kötü tahmin eder."
                    if L == "tr" else
                    "This chart shows the average information gain the Random Forest pipeline assigns each feature. "
                    "High value = the model performs much worse without that feature."
                )
                st.caption(_fi_note)
                st.image(str(fi_path), use_container_width=False, width=700)

            rsp_path = DS_TABLES / "risk_score_preview.csv"
            if rsp_path.exists():
                st.subheader(t("ds_risk_preview", L))
                _rsp_note = (
                    "Bu tablo **heuristik skoru** gösteriyor (devamsızlık %45 + not %35 + trend %20). "
                    "UCI test verisi üzerinde üretilmiştir — canlı sistemdeki ML skorundan farklıdır. "
                    "Yüksek devamsızlığa (örn. 56, 75 gün) ve düşük not ortalamasına sahip öğrencilerin "
                    "yüksek risk etiketi aldığını görebilirsiniz."
                    if L == "tr" else
                    "This table shows the **heuristic score** (absences 45% + grade 35% + trend 20%). "
                    "Generated on UCI test data — different from the live ML score in the database. "
                    "Students with high absence counts (e.g. 56, 75 days) and low grade averages "
                    "predictably receive high-risk labels."
                )
                st.caption(_rsp_note)
                rsp_df = pd.read_csv(rsp_path)

                rsp_renamed = rsp_df.rename(columns={
                    "school": "Okul/School",
                    "sex": "Cinsiyet/Sex",
                    "age": "Yaş/Age",
                    "absences": "Devamsızlık/Absences",
                    "G1": "G1 (1.Dönem)",
                    "G2": "G2 (2.Dönem)",
                    "G3": "G3 (Final)",
                    "risk_score": "Risk Skoru (0-100)",
                    "risk_level": "Risk Seviyesi",
                })

                def _style_risk_level(val: str) -> str:
                    return {
                        "high": "background-color: #ffcccc; color: #7b0000",
                        "medium": "background-color: #fff3cc; color: #7b5800",
                        "low": "background-color: #ccffcc; color: #0a4a00",
                    }.get(val, "")

                styled = rsp_renamed.style.map(_style_risk_level, subset=["Risk Seviyesi"])
                st.dataframe(styled, use_container_width=True)

            shap_files = sorted(DS_FIGURES.glob("shap_*.png")) if DS_FIGURES.is_dir() else []
            if shap_files:
                st.subheader("SHAP — Model Yorumlanabilirliği / Model Interpretability")
                _shap_note = (
                    "SHAP (SHapley Additive exPlanations) değerleri, her özelliğin bireysel tahmine "
                    "ne kadar katkı sağladığını gösterir. Sol grafik ortalama etkiyi, "
                    "sağ grafik ise hangi yönde etkilediğini (düşük/yüksek değer → risk artıyor mu azalıyor mu?) ortaya koyar."
                    if L == "tr" else
                    "SHAP (SHapley Additive exPlanations) values show how much each feature "
                    "contributes to an individual prediction. The left chart shows mean impact; "
                    "the right shows direction (low/high feature value → does risk increase or decrease?)."
                )
                st.caption(_shap_note)
                shap_cols = st.columns(min(2, len(shap_files)))
                for col, p in zip(shap_cols * 10, shap_files):
                    label = p.stem.replace("shap_", "").replace("_", " ").title()
                    with col:
                        st.image(str(p), caption=label, use_container_width=True)

            report_files = (
                sorted(DS_TABLES.glob("classification_report_*.txt"))
                if DS_TABLES.is_dir()
                else []
            )
            if report_files:
                st.subheader(t("ds_class_report", L))
                for p in report_files:
                    model_label = (
                        p.stem.replace("classification_report_", "").replace("_", " ").title()
                    )
                    with st.expander(model_label):
                        st.code(p.read_text(encoding="utf-8"), language="text")
