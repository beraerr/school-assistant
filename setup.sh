#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Akıllı Okul Bilgi Sistemi — Tek Seferlik Kurulum Scripti
# Çalıştır: bash setup.sh
#
# Ortam değişkenleri (isteğe bağlı):
#   LLM_CONFIG_SOURCE=/yol/llm.local.json  — mevcut Claude config'i kopyalar
#   SKIP_PIP_INSTALL=1                      — pip adımını atlar (venv hazırsa)
#
# Önerilen Python: 3.11 veya 3.12. 3.14 ile pandas vb. teker teker derlenemeyebilir.
# ─────────────────────────────────────────────────────────────────────────────
set -e

cd "$(dirname "$0")"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Akıllı Okul Bilgi Sistemi — Kurulum"
echo "═══════════════════════════════════════════════════════"

# ── 1. Sanal ortam ────────────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo ""
  echo "→ Sanal ortam oluşturuluyor..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "→ Sanal ortam aktif."

PY_MINOR="$(python -c 'import sys; print(sys.version_info.minor)')"
PY_MAJOR="$(python -c 'import sys; print(sys.version_info.major)')"
if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 14 ]; then
  echo ""
  echo "UYARI: Python 3.$PY_MINOR: bazı bağımlılıkların teker derlenmesi başarısız olabilir."
  echo "    Tercih: python3.12 -m venv venv  ile yeni venv, veya SKIP_PIP_INSTALL=1"
fi

# ── 2. Bağımlılıklar ──────────────────────────────────────────────────────────
if [ "${SKIP_PIP_INSTALL:-0}" = "1" ]; then
  echo ""
  echo "→ SKIP_PIP_INSTALL=1 — pip adımı atlanıyor (mevcut paketler kullanılacak)."
else
  echo ""
  echo "→ Paketler yükleniyor (bu birkaç dakika alabilir)..."
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
  pip install -r data_science/requirements-ds.txt -q
  echo "→ Paketler yüklendi."
fi

# ── 3. .env kontrolü ──────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo ""
  echo "→ .env dosyası oluşturuluyor..."
  cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/school_db
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-6
LLM_CONFIG_PATH=config/llm.local.json
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=false
EOF
  echo "→ .env oluşturuldu."
else
  echo "→ .env zaten var, atlanıyor."
fi

# ── 4. LLM config ──────────────────────────────────────────────────────────────
# İsteğe bağlı: mevcut bir dosyadan kopyala (repoya girmez)
#   LLM_CONFIG_SOURCE=~/yol/llm.local.json bash setup.sh
if [ -n "${LLM_CONFIG_SOURCE:-}" ] && [ -f "$LLM_CONFIG_SOURCE" ]; then
  mkdir -p config
  cp "$LLM_CONFIG_SOURCE" config/llm.local.json
  echo "→ LLM config kopyalandı: $LLM_CONFIG_SOURCE → config/llm.local.json"
elif [ ! -f "config/llm.local.json" ]; then
  cp config/llm.local.example.json config/llm.local.json
  echo ""
  echo "UYARI: config/llm.local.json oluşturuldu (şablon)."
  echo "    Anahtarı gir veya yeniden çalıştır:"
  echo "    LLM_CONFIG_SOURCE=/yol/llm.local.json bash setup.sh"
  echo "    nano config/llm.local.json"
else
  echo "→ config/llm.local.json mevcut, korunuyor."
fi

# ── 5. PostgreSQL DB ──────────────────────────────────────────────────────────
echo ""
echo "→ PostgreSQL veritabanları oluşturuluyor..."
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='school_db'" | grep -q 1 \
  || psql -U postgres -c "CREATE DATABASE school_db;"
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='school_test_db'" | grep -q 1 \
  || psql -U postgres -c "CREATE DATABASE school_test_db;"
echo "→ Veritabanları hazır."

# ── 6. Data science pipeline ──────────────────────────────────────────────────
echo ""
echo "→ Data science pipeline çalışıyor (UCI verisi indirilir + modeller eğitilir)..."
export PYTHONPATH="$(pwd):$PYTHONPATH"
python data_science/src/risk_model_pipeline.py
echo "→ Pipeline tamamlandı."

# ── 7. Veritabanı seed ────────────────────────────────────────────────────────
echo ""
echo "→ Veritabanı dolduruluyor (60 öğrenci, 125 kullanıcı)..."
python database/seed_from_uci.py
echo "→ Seed tamamlandı."

# ── 8. ML risk skorları ───────────────────────────────────────────────────────
echo ""
echo "→ ML risk skorları hesaplanıyor..."
python database/score_students_ml.py
echo "→ Risk skorları yazıldı."

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Kurulum tamamlandı."
echo ""
echo "  Şimdi iki ayrı terminalde şunları çalıştır:"
echo ""
echo "    Terminal 1 (backend):"
echo "      source venv/bin/activate && ./run_backend.sh"
echo ""
echo "    Terminal 2 (frontend):"
echo "      source venv/bin/activate && ./run_frontend.sh"
echo ""
echo "  Frontend : http://localhost:8501"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo ""
echo "  Giriş    : principal / admin123"
echo "═══════════════════════════════════════════════════════"
