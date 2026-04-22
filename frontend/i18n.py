from __future__ import annotations

from typing import Dict, Literal

Lang = Literal["tr", "en"]

MESSAGES: Dict[str, Dict[Lang, str]] = {
    "page_title": {"tr": "Akıllı Okul Bilgi Sistemi", "en": "Smart School Information System"},
    "api_url": {"tr": "API adresi", "en": "API URL"},
    "login_header": {"tr": "Giriş Yap", "en": "Sign in"},
    "username": {"tr": "Kullanıcı Adı", "en": "Username"},
    "password": {"tr": "Şifre", "en": "Password"},
    "login_btn": {"tr": "Giriş Yap", "en": "Sign in"},
    "login_ok": {"tr": "Giriş başarılı!", "en": "Signed in successfully."},
    "login_need_creds": {"tr": "Lütfen kullanıcı adı ve şifre girin", "en": "Please enter username and password."},
    "login_ds_access_notice": {
        "tr": "Veri Bilimi Raporları bölümü yalnızca Müdür rolü için görüntülenebilir ve indirilebilir durumdadır. Bilgiler gizli değildir; rapor içeriğine ilişkin sorular sistem içinde tüm roller tarafından yanıtlanabilir.",
        "en": "The Data Science Reports section is viewable and downloadable only for the Principal role. The information is not confidential; report-related knowledge questions can still be answered for all roles within the system.",
    },
    "demo_users": {
        "tr": "**Demo kullanıcılar:**\n\n- Müdür: `principal` / `admin123`\n- Öğretmen: `teacher1` / `teacher123`\n- Veli: `parent1` / `parent123`\n- Öğrenci: `student1` / `student123`",
        "en": "**Demo accounts:**\n\n- Principal: `principal` / `admin123`\n- Teacher: `teacher1` / `teacher123`\n- Parent: `parent1` / `parent123`\n- Student: `student1` / `student123`",
    },
    "user_info": {"tr": "Kullanıcı Bilgileri", "en": "User info"},
    "user_label": {"tr": "Kullanıcı", "en": "User"},
    "role_label": {"tr": "Rol", "en": "Role"},
    "class_label": {"tr": "Sınıf", "en": "Class"},
    "logout": {"tr": "Çıkış Yap", "en": "Log out"},
    "tab_query": {"tr": "Sohbet & veri sorgusu", "en": "Chat & data query"},
    "tab_risk": {"tr": "Riskli Öğrenciler", "en": "At-risk students"},
    "tab_ds": {"tr": "Veri Bilimi Raporları", "en": "Data science reports"},
    "tab_ds_locked": {"tr": "Veri Bilimi Raporları (Müdür)", "en": "Data science reports (Principal)"},
    "lang_label": {"tr": "Arayüz dili", "en": "Interface language"},
    "query_header": {"tr": "Doğal Dil Sorgusu", "en": "Natural language query"},
    "query_help": {
        "tr": "Türkçe veya İngilizce soru yazabilirsiniz. Mahmut Hoca; veri sorgusu, risk analizi ve proje/workflow sorularını yanıtlar.",
        "en": "You can ask in **Turkish or English**. Coach Mahmut answers data queries, risk-analysis questions, and project/workflow questions.",
    },
    "example_queries": {"tr": "Örnek Sorgular", "en": "Example queries"},
    "query_placeholder": {"tr": "Sorgunuzu girin:", "en": "Your question:"},
    "run_query": {"tr": "Sorguyu Çalıştır", "en": "Run query"},
    "need_login": {"tr": "Lütfen önce giriş yapın", "en": "Please sign in first."},
    "query_ok": {"tr": "Sorgu başarıyla çalıştırıldı!", "en": "Query completed successfully."},
    "results": {"tr": "Sonuçlar", "en": "Results"},
    "empty_results": {"tr": "Sorgu sonucu boş. Sonuç bulunamadı.", "en": "No rows returned."},
    "download_csv": {"tr": "CSV olarak indir", "en": "Download as CSV"},
    "ai_explain": {"tr": "AI Açıklaması", "en": "AI explanation"},
    "query_meta": {"tr": "Sorgu Bilgileri", "en": "Query details"},
    "orig_query": {"tr": "Orijinal Sorgu", "en": "Original question"},
    "result_count": {"tr": "Sonuç Sayısı", "en": "Row count"},
    "perm_full": {"tr": "Tüm verilere erişim", "en": "Full data access"},
    "perm_label": {"tr": "İzin", "en": "Permission"},
    "sql_expander": {"tr": "Oluşturulan SQL Sorgusu", "en": "Generated SQL"},
    "warn_empty_query": {"tr": "Lütfen bir sorgu girin", "en": "Please enter a question."},
    "risk_header": {"tr": "Riskli Öğrenciler", "en": "At-risk students"},
    "risk_blurb": {
        "tr": "Risk skoru ML/GBM modelinden gelir.",
        "en": "Risk score comes from the ML/GBM model.",
    },
    "class_filter": {"tr": "Sınıf filtresi (opsiyonel)", "en": "Class filter (optional)"},
    "risk_refresh": {"tr": "Risk Analizini Yenile", "en": "Refresh risk analysis"},
    "risk_loading": {"tr": "Risk verileri yükleniyor...", "en": "Loading risk data..."},
    "col_student": {"tr": "Öğrenci", "en": "Student"},
    "col_class": {"tr": "Sınıf", "en": "Class"},
    "col_score": {"tr": "Risk Skoru", "en": "Risk score"},
    "col_level": {"tr": "Seviye", "en": "Level"},
    "col_abs": {"tr": "Devamsızlık Katkısı", "en": "Absence component"},
    "col_grade": {"tr": "Not Katkısı", "en": "Grade component"},
    "col_trend": {"tr": "Trend Katkısı", "en": "Trend component"},
    "col_expl": {"tr": "Açıklama", "en": "Explanation"},
    "risk_none": {"tr": "Görüntülenecek risk kaydı bulunamadı.", "en": "No risk rows to display."},
    "col_ml_score": {"tr": "ML Skoru", "en": "ML score"},
    "col_ml_level": {"tr": "ML Seviyesi", "en": "ML level"},
    "col_ml_date": {"tr": "ML Tarihi", "en": "ML date"},
    "risk_method_header": {"tr": "Puanlama Metodolojisi", "en": "Scoring methodology"},
    "risk_method_ml": {
        "tr": "**ML skoru (GBM)** (0-100): GradientBoosting modeli 1 044 UCI Öğrenci Performansı kaydı üzerinde eğitildi. 5-kat CV ROC-AUC = **0.983**. Özellikler: devamsızlık, not ort., not trendi. Skor doğrudan model olasılığıdır (`predict_proba × 100`). `score_students_ml.py` ile yenilenir.",
        "en": "**ML score (GBM)** (0-100): GradientBoosting trained on 1 044 UCI Student Performance records. 5-fold CV ROC-AUC = **0.983**. Features: absences, grade avg, grade trend. Score is direct model probability (`predict_proba × 100`). Refresh with `score_students_ml.py`.",
    },
    "risk_method_target": {
        "tr": "**Hedef değişken:** `risk = 1` eğer devamsızlık ≥ 10 VEYA final not < 10/20 VEYA not düşüyor ve borderline.",
        "en": "**Target variable:** `risk = 1` if absences ≥ 10 OR final grade < 10/20 OR grades falling and borderline.",
    },
    "risk_ml_note": {
        "tr": "ML Skoru boşsa `python database/score_students_ml.py` çalıştırın.",
        "en": "If ML score is empty, run `python database/score_students_ml.py`.",
    },
    "ds_deployed_header": {"tr": "Canlı Sistemde Kullanılan Model", "en": "Model deployed in production"},
    "ds_deployed_note": {
        "tr": "GBM modeli (`score_students_ml.py`) öğrenci veri tabanına uygulanır ve risk skorları `student_risk_scores` tablosuna yazılır. Chatbot ve Risk sekmesi bu tabloyu kullanır.",
        "en": "The GBM model (`score_students_ml.py`) is applied to the student database and risk scores are written to the `student_risk_scores` table. The chatbot and Risk tab both consume this table.",
    },
    "ds_header": {"tr": "UCI öğrenci risk pipeline çıktıları", "en": "UCI student risk pipeline outputs"},
    "ds_access_denied": {
        "tr": "Bu bölüm yalnızca Müdür rolüne açıktır.",
        "en": "This section is available only to the Principal role.",
    },
    "ds_download_header": {"tr": "Rapor İndirme Merkezi", "en": "Report download center"},
    "ds_download_blurb": {
        "tr": "Aşağıdan tek PDF olarak tüm özet raporu indirin: biri Türkçe, biri İngilizce metin ve görsellerle (pipeline çıktılarından üretilir).",
        "en": "Download one consolidated PDF below: Turkish or English narrative with figures built from your pipeline outputs.",
    },
    "ds_no_downloadables": {
        "tr": "İndirilebilir rapor dosyası bulunamadı.",
        "en": "No downloadable report files were found.",
    },
    "download_file_btn": {"tr": "Dosyayı indir", "en": "Download file"},
    "ds_pdf_cover_title": {
        "tr": "UCI Öğrenci Riski — Veri Bilimi Raporu",
        "en": "UCI Student Risk — Data Science Report",
    },
    "ds_pdf_cover_sub": {
        "tr": "Model seçimi, EDA görselleri, karşılaştırmalar ve üretim notları (tek dosya).",
        "en": "Model selection, EDA figures, comparisons, and deployment notes (single file).",
    },
    "ds_pdf_section_eda": {
        "tr": "Sosyal faktörler — EDA (yan yana)",
        "en": "Social factors — EDA (side by side)",
    },
    "ds_pdf_section_grades_abs": {
        "tr": "Not ve devamsızlık dağılımları",
        "en": "Grade and absence distributions",
    },
    "ds_pdf_leakage_title": {
        "tr": "Hedef ve özellikler (sızıntı notu)",
        "en": "Target vs features (leakage note)",
    },
    "ds_pdf_btn_tr": {"tr": "Türkçe PDF indir", "en": "Download Turkish PDF"},
    "ds_pdf_btn_en": {"tr": "İngilizce PDF indir", "en": "Download English PDF"},
    "ds_pdf_generating": {"tr": "PDF oluşturuluyor…", "en": "Building PDF…"},
    "ds_pdf_error": {"tr": "PDF oluşturulamadı.", "en": "Could not build the PDF."},
    "ds_figures_source_note": {
        "tr": "Bu sekmedeki görseller ve CSV dosyaları yerelde `python data_science/src/risk_model_pipeline.py` "
        "çalıştırıldığında üretilir; güncel olmaları için pipeline'ı (ve gerekiyorsa notebook'u) yeniden çalıştırın.",
        "en": "Figures and CSV files in this tab are produced when you run "
        "`python data_science/src/risk_model_pipeline.py` locally; re-run the pipeline (and the notebook if needed) "
        "to refresh them.",
    },
    "ds_blurb": {
        "tr": "`data_science/reports/figures` altında üretilen görseller (notebook veya `python -m src.risk_model_pipeline` ile).",
        "en": "Figures under `data_science/reports/figures` (from the notebook or `python -m src.risk_model_pipeline`).",
    },
    "ds_no_figures": {
        "tr": "Henüz grafik yok. `data_science` klasöründe pipeline veya notebook çalıştırın.",
        "en": "No figures yet. Run the pipeline or notebook under `data_science`.",
    },
    "ds_model_cmp": {"tr": "Model Karşılaştırması", "en": "Model comparison"},
    "ds_best_model": {"tr": "En İyi Model", "en": "Best model"},
    "ds_raw_table": {"tr": "Ham tablo", "en": "Raw table"},
    "ds_cv": {"tr": "Çapraz Doğrulama (CV)", "en": "Cross-validation (CV)"},
    "ds_conf_mat": {"tr": "Confusion Matrix", "en": "Confusion matrices"},
    "ds_feat_imp": {"tr": "Feature Importance (Risk Skoru)", "en": "Feature importance (risk score)"},
    "ds_risk_preview": {"tr": "Risk Skoru Önizleme (UCI Verisi)", "en": "Risk score preview (UCI data)"},
    "ds_class_report": {"tr": "Sınıflandırma Raporları", "en": "Classification reports"},
    "ds_leakage_note": {
        "tr": "Not: y hedefi G3 içeriyor (final notu < 10 → risk). X özelliklerinde G3 yok; G1+G2 ortalaması kullanılıyor.",
        "en": "Note: target y includes G3 (final grade < 10 → risk). G3 is excluded from features X; only G1+G2 average is used.",
    },
    "ds_pipeline_missing": {
        "tr": "Raporlar bulunamadı. `python data_science/src/risk_model_pipeline.py` komutunu çalıştırın.",
        "en": "Reports not found. Run `python data_science/src/risk_model_pipeline.py` first.",
    },
    "ds_selection_header": {
        "tr": "Model Seçim Süreci — Base vs Extended",
        "en": "Model Selection — Base vs Extended",
    },
    "ds_selection_blurb": {
        "tr": (
            "İki farklı özellik seti 3 ayrı algoritmada karşılaştırıldı. "
            "**Base**: yalnızca akademik sinyaller (devamsızlık, notlar, ders çalışma). "
            "**Extended**: akademik + sosyo-ekonomik faktörler "
            "(ebeveyn eğitimi, alkol tüketimi, aile ilişkisi, sağlık, adres, vb.)."
        ),
        "en": (
            "Two feature sets were compared across 3 algorithms. "
            "**Base**: academic signals only (absences, grades, study time). "
            "**Extended**: academic + socio-economic factors "
            "(parent education, alcohol use, family relations, health, address, etc.)."
        ),
    },
    "ds_winner_header": {
        "tr": "Kazanan Model",
        "en": "Winner Model",
    },
    "ds_winner_feature_set": {"tr": "Feature Set", "en": "Feature Set"},
    "ds_winner_algorithm":   {"tr": "Algoritma", "en": "Algorithm"},
    "ds_winner_reason": {
        "tr": "**Seçim kriteri:** En yüksek F1 skoru — sınıf dengesizliği olan risk tahmininde hem precision hem recall'ü dengeler.",
        "en": "**Selection criterion:** Highest F1 score — balances precision and recall for imbalanced risk prediction.",
    },
    "ds_social_eda_header": {
        "tr": "Sosyal Faktörler EDA",
        "en": "Social Features EDA",
    },
    "ds_no_comparison": {
        "tr": "Karşılaştırma henüz çalıştırılmadı. Pipeline'ı tekrar çalıştırın.",
        "en": "Comparison not yet run. Re-run the pipeline.",
    },
    "ds_base_label":     {"tr": "Base (Akademik)", "en": "Base (Academic)"},
    "ds_extended_label": {"tr": "Extended (+Sosyal)", "en": "Extended (+Social)"},
    "ds_delta_header":   {"tr": "Gelişim (Extended − Base)", "en": "Improvement (Extended − Base)"},

    "ds_journey_header": {
        "tr": "Nasıl Buraya Geldik?",
        "en": "How We Got Here",
    },
    "ds_journey_body": {
        "tr": (
            "Bu projenin risk puanlama motoru **sıfırdan** kuruldu. "
            "Başlangıçta elimizde sadece bir soru vardı: *\"Bir öğrenci gerçekten risk altında mı, "
            "yoksa kötü bir günü mü geçiriyor?\"*\n\n"
            "İlk adımda UCI Öğrenci Performansı veri setini inceledik — "
            "Portekiz'deki iki liseden toplanan, 1 044 öğrenciye ait akademik ve sosyal yaşam kayıtları. "
            "Ham veriye baktığımızda şunu fark ettik: devamsızlık, not ortalaması ve not trendi, "
            "\"risk\" etiketini tek başına oldukça iyi açıklıyor.\n\n"
            "Ardından sosyal faktörleri (ebeveyn eğitimi, alkol kullanımı, aile yapısı, adres vb.) "
            "da ekleyip iki farklı özellik seti oluşturduk — **Base** ve **Extended**. "
            "Her iki seti üç farklı algoritmada denedik: Lojistik Regresyon, Random Forest, "
            "ve Gradient Boosting. Sonuçlar beklenmedik bir şey ortaya koydu: "
            "**sosyal veriler modele katkı sağlamadı**, hatta bazı modellerde performansı "
            "hafifçe düşürdü. Bu bulguyu kabul edip sadeliği tercih ettik.\n\n"
            "Son olarak kazanan modelin tahminlerini (`predict_proba × 100`) doğrudan veritabanına "
            "yazdık — böylece her öğretmen ve veli bu skoru anlık görebiliyor."
        ),
        "en": (
            "The risk scoring engine in this project was built **from scratch**. "
            "We started with one question: *\"Is a student genuinely at risk, "
            "or just having a bad week?\"*\n\n"
            "First we studied the UCI Student Performance dataset — academic and social records "
            "from 1 044 students at two Portuguese high schools. Looking at the raw data, "
            "one thing became clear: absences, grade average, and grade trend already explain "
            "\"risk\" labels surprisingly well on their own.\n\n"
            "We then added social factors (parent education, alcohol use, family structure, "
            "address, etc.) and created two feature sets — **Base** and **Extended** — "
            "testing each across three algorithms: Logistic Regression, Random Forest, "
            "and Gradient Boosting. The results were unexpected: "
            "**social features didn't improve the model**, and even hurt performance slightly "
            "in some cases. We accepted that finding and chose simplicity.\n\n"
            "Finally, the winning model's probabilities (`predict_proba × 100`) are written "
            "directly to the database — so every teacher and parent can see live scores."
        ),
    },

    "ds_dataset_header": {
        "tr": "Kullandığımız Veri Seti",
        "en": "The Dataset We Used",
    },
    "ds_dataset_body": {
        "tr": (
            "**UCI Student Performance** veri seti (Cortez & Silva, 2008) iki ayrı tablodan oluşur: "
            "matematik (`student-mat.csv`) ve Portekizce (`student-por.csv`). "
            "Her iki tabloyu birleştirince **1 044 satır** elde ettik.\n\n"
            "Her kayıt bir öğrenciye ait:\n"
            "- **G1, G2**: birinci ve ikinci dönem sonu notları (0–20 arası)\n"
            "- **G3**: yıl sonu final notu — *model eğitiminde kullanılmadı*, "
            "sadece risk etiketini oluşturmak için referans alındı\n"
            "- **absences**: yıl boyunca toplam devamsızlık günü sayısı\n"
            "- **studytime**: haftalık ders çalışma süresi (1–4 kategorik)\n"
            "- Sosyal değişkenler: ebeveyn eğitimi, mesleği, alkol kullanımı, "
            "aile ilişki kalitesi, sağlık durumu, adres türü vb.\n\n"
            "**Hedef değişken (y):** Bir öğrenci `risk = 1` olarak etiketlendi eğer;\n"
            "- devamsızlık ≥ 10 GÜN, *veya*\n"
            "- G3 (final notu) < 10/20, *veya*\n"
            "- G1'den G2'ye not düşüşü var ve ortalama borderline\n\n"
            "Veri setinde yaklaşık **%39** oranında riskli öğrenci var — "
            "ciddi bir sınıf dengesizliği değil, ama dikkat etmek gerekiyor."
        ),
        "en": (
            "The **UCI Student Performance** dataset (Cortez & Silva, 2008) comes in two tables: "
            "maths (`student-mat.csv`) and Portuguese (`student-por.csv`). "
            "Merging both gives us **1 044 rows**.\n\n"
            "Each record belongs to one student:\n"
            "- **G1, G2**: end-of-period grades (0–20 scale)\n"
            "- **G3**: final year grade — *not used in training*, "
            "only as a reference to define the risk label\n"
            "- **absences**: total absence days across the year\n"
            "- **studytime**: weekly study time (1–4 categorical)\n"
            "- Social variables: parent education level, job type, alcohol consumption, "
            "family relationship quality, health status, home address type, etc.\n\n"
            "**Target variable (y):** A student was labelled `risk = 1` if:\n"
            "- absences ≥ 10 DAYS, *or*\n"
            "- G3 (final grade) < 10/20, *or*\n"
            "- grade fell from G1 to G2 and average is borderline\n\n"
            "Roughly **39%** of the dataset is at-risk — "
            "not a severe class imbalance, but worth watching."
        ),
    },

    "ds_why_base_won_header": {
        "tr": "Neden Sosyal Veriler Yardımcı Olmadı?",
        "en": "Why Didn't Social Features Help?",
    },
    "ds_why_base_won_body": {
        "tr": (
            "Sosyal değişkenler eklediğimizde **Extended** modelinin her algoritmada "
            "Base modeline göre daha kötü performans gösterdiğini gördük. "
            "Bu sezgisel olarak şaşırtıcı, çünkü ebeveyn eğitimi veya alkol kullanımının "
            "akademik riskle ilişkili olduğu bilinir.\n\n"
            "Birkaç olası açıklama:\n\n"
            "**1. Bilgi zaten yansıtılmış:** Sosyal dezavantajlar zaten G1, G2 ve devamsızlığa "
            "yansıyor. Model bu değişkenleri dolaylı olarak öğreniyor; "
            "ham sosyal sütunlar ekstra bilgi taşımıyor.\n\n"
            "**2. Gürültü ekleniyor:** 16 yeni kategorik değişken dönüştürme (one-hot) sonrası "
            "özellik uzayını genişletiyor. Bu, az verili ortamda overfitting riskini artırıyor.\n\n"
            "**3. Veri kalitesi:** Sosyal veriler öz-bildirim yoluyla toplanmış — "
            "hatalı veya tutarsız cevaplar modeli yanıltıyor olabilir.\n\n"
            "Sonuç: **Ockham'ın Usturası** — daha basit model daha iyi genelliyor."
        ),
        "en": (
            "When we added social variables, **Extended** models consistently performed "
            "worse than Base models across all three algorithms. "
            "This is counterintuitive, because parent education or alcohol use "
            "are known to correlate with academic risk.\n\n"
            "A few plausible explanations:\n\n"
            "**1. Information already baked in:** Social disadvantages are already reflected "
            "in G1, G2, and absences. The model learns them indirectly; "
            "raw social columns carry no additional signal.\n\n"
            "**2. Adding noise:** 16 new categorical variables expand the feature space "
            "after one-hot encoding, increasing overfitting risk with limited data.\n\n"
            "**3. Data quality:** Social data is self-reported — "
            "incorrect or inconsistent answers may mislead the model.\n\n"
            "Conclusion: **Occam's Razor** — the simpler model generalises better."
        ),
    },

    "ds_algo_header": {
        "tr": "Neden Gradient Boosting?",
        "en": "Why Gradient Boosting?",
    },
    "ds_algo_body": {
        "tr": (
            "Üç algoritma karşılaştırdık; her birinin farklı bir felsefesi var:\n\n"
            "**Lojistik Regresyon** — Hızlı, yorumlanabilir, doğrusal sınır. "
            "F1 = 0.869, ROC-AUC = 0.946. İyi bir başlangıç noktası ama "
            "özellikler arasındaki etkileşimleri yakalamıyor.\n\n"
            "**Random Forest** — Paralel karar ağaçlarının ortalaması. "
            "F1 = 0.941, ROC-AUC = 0.990. Güçlü ve gürültüye dayanıklı, "
            "ama Gradient Boosting'in gerisinde kaldı.\n\n"
            "**Gradient Boosting (GBM)** — Ağaçları sıralı olarak inşa eder; "
            "her ağaç bir öncekinin hatalarını düzeltir. "
            "F1 = **0.956**, ROC-AUC = **0.993**. Hem precision hem recall'de öne geçti. "
            "Risk tahmini gibi sınıf dengesizliği olan problemlerde F1 kritik metrik — "
            "hem yanlış pozitifi hem yanlış negatifi minimize etmek gerekiyor.\n\n"
            "5 katlı çapraz doğrulama sonuçları da tutarlı: "
            "GBM'nin F1 ortalaması 0.914, standart sapma sadece ±0.013 — "
            "bu, modelin tek bir veri bölünmesine bağlı olmadığını gösteriyor."
        ),
        "en": (
            "We compared three algorithms, each with a different philosophy:\n\n"
            "**Logistic Regression** — Fast, interpretable, linear boundary. "
            "F1 = 0.869, ROC-AUC = 0.946. A solid baseline but misses feature interactions.\n\n"
            "**Random Forest** — Averaged parallel decision trees. "
            "F1 = 0.941, ROC-AUC = 0.990. Robust and noise-resistant, "
            "but fell short of Gradient Boosting.\n\n"
            "**Gradient Boosting (GBM)** — Trees built sequentially; "
            "each tree corrects the errors of the one before. "
            "F1 = **0.956**, ROC-AUC = **0.993**. Highest on both precision and recall. "
            "For risk prediction with class imbalance, F1 is the critical metric — "
            "we need to minimise both false positives and false negatives.\n\n"
            "5-fold cross-validation confirms stability: "
            "GBM mean F1 = 0.914, standard deviation ±0.013 — "
            "showing the model is not dependent on a single data split."
        ),
    },

    "ds_risk_col_header": {
        "tr": "Veritabanındaki risk_score Sütunu Nedir?",
        "en": "What Is the risk_score Column in the Database?",
    },
    "ds_risk_col_body": {
        "tr": (
            "Modeli eğittikten sonra onu \"dondurarak\" (`winner_model.pkl`) kaydettik. "
            "Bu dosya, `score_students_ml.py` scripti tarafından okulun gerçek "
            "öğrenci veritabanına uygulanır.\n\n"
            "Her öğrenci için süreç şöyle işliyor:\n"
            "1. Öğrencinin devamsızlık sayısı, dönem notları (G1, G2) ve not trendi hesaplanır\n"
            "2. Bu değerler eğitimde kullandığımız aynı `preprocessor` katmanından geçirilir "
            "(ölçekleme, eksik değer doldurma)\n"
            "3. GBM modeli **risk olasılığı** üretir: `predict_proba(X)[:, 1]`\n"
            "4. Bu olasılık `× 100` ile 0–100 skalasına çevrilir → **ml_risk_score**\n"
            "5. Skor `student_risk_scores` tablosuna yazılır\n\n"
            "**Yani skor ne anlama geliyor?**\n"
            "- 0–35: Düşük risk — öğrenci genellikle sorunsuz seyrediyor\n"
            "- 35–65: Orta risk — dikkat gerekebilir, trend izlenmeli\n"
            "- 65–100: Yüksek risk — müdahale önerilir\n\n"
            "**Bu skor ne değildir?** Kesin bir karar değil. "
            "Model, geçmiş verilerden öğrendiği istatistiksel bir pattern — "
            "öğretmen gözlemi ve bağlam her zaman önceliklidir."
        ),
        "en": (
            "After training, we saved the model as `winner_model.pkl`. "
            "This file is applied to the school's real student database "
            "by the `score_students_ml.py` script.\n\n"
            "For each student, the process works like this:\n"
            "1. Calculate the student's absence count, period grades (G1, G2), and grade trend\n"
            "2. Pass these through the same `preprocessor` pipeline used during training "
            "(scaling, missing-value imputation)\n"
            "3. The GBM model produces a **risk probability**: `predict_proba(X)[:, 1]`\n"
            "4. This probability is multiplied by 100 to give a 0–100 scale → **ml_risk_score**\n"
            "5. The score is written to the `student_risk_scores` table\n\n"
            "**So what does the score mean?**\n"
            "- 0–35: Low risk — student is generally on track\n"
            "- 35–65: Medium risk — worth monitoring, watch the trend\n"
            "- 65–100: High risk — intervention recommended\n\n"
            "**What this score is not:** A definitive verdict. "
            "The model learned statistical patterns from historical data — "
            "teacher observation and context always take priority."
        ),
    },

    "ds_two_scores_header": {
        "tr": "İki Farklı Skor: Heuristik vs ML",
        "en": "Two Different Scores: Heuristic vs ML",
    },
    "ds_two_scores_body": {
        "tr": (
            "Projede **iki ayrı risk skoru** var — bunları karıştırmamak önemli:\n\n"
            "| | Heuristik Skor | ML Skoru (GBM) |\n"
            "|---|---|---|\n"
            "| **Kaynak** | Elle yazılmış formül | Makine öğrenmesi modeli |\n"
            "| **Girdiler** | devamsızlık %45, not %35, trend %20 | aynı girdiler + trained weights |\n"
            "| **Çıktı** | 0–100 ağırlıklı toplam | model olasılığı × 100 |\n"
            "| **Kullanım** | UCI önizleme tablosu (bu ekran) | Canlı DB, Riskli Öğrenciler sekmesi |\n"
            "| **Yorumlanabilirlik** | Kural tabanlı, kolay anlaşılır | Daha siyah kutu, ama daha doğru |\n\n"
            "Heuristik skor, \"mantık testini\" geçmek için tasarlandı: "
            "uzun devamsızlığı, düşük notu ve gerileyen trendi sezgisel ağırlıklarla birleştirir. "
            "ML skoru ise bu ağırlıkları veriden öğrenerek daha ince ilişkileri de yakalar."
        ),
        "en": (
            "The project has **two distinct risk scores** — important not to mix them up:\n\n"
            "| | Heuristic Score | ML Score (GBM) |\n"
            "|---|---|---|\n"
            "| **Source** | Hand-crafted formula | Machine learning model |\n"
            "| **Inputs** | absences 45%, grade 35%, trend 20% | same inputs + learned weights |\n"
            "| **Output** | 0–100 weighted sum | model probability × 100 |\n"
            "| **Usage** | UCI preview table (this screen) | Live DB, At-risk students tab |\n"
            "| **Interpretability** | Rule-based, easy to explain | More black-box, but more accurate |\n\n"
            "The heuristic score was designed to pass a \"sanity check\": "
            "it combines long absences, low grades, and a declining trend with intuitive weights. "
            "The ML score learns those weights from data and captures subtler relationships."
        ),
    },

    "conn_error": {"tr": "Bağlantı hatası", "en": "Connection error"},
    "login_error": {"tr": "Giriş hatası", "en": "Login error"},
    "query_error": {"tr": "Sorgu hatası", "en": "Query error"},
    "risk_error": {"tr": "Risk verisi hatası", "en": "Risk data error"},
    "chat_thinking": {"tr": "Düşünüyorum…", "en": "Thinking…"},
    "chat_clear": {"tr": "Sohbeti temizle", "en": "Clear chat"},
    "chat_input_placeholder": {"tr": "Mesajınızı yazın…", "en": "Type your message…"},
}

def t(key: str, lang: Lang) -> str:
    row = MESSAGES.get(key)
    if not row:
        return key
    return row.get(lang) or row["en"]

ROLE_DISPLAY: Dict[str, Dict[Lang, str]] = {
    "principal": {"tr": "Müdür", "en": "Principal"},
    "teacher": {"tr": "Öğretmen", "en": "Teacher"},
    "parent": {"tr": "Veli", "en": "Parent"},
    "student": {"tr": "Öğrenci", "en": "Student"},
}

def role_name(role: str, lang: Lang) -> str:
    r = ROLE_DISPLAY.get(role, {})
    return r.get(lang) or r.get("en") or role
