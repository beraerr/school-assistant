# 🚀 Railway.app Deploy Rehberi

Projenin mimarisi: **FastAPI backend + Streamlit frontend + PostgreSQL**
Firebase bu stack için uygun değil — Railway en hızlı çözüm.

---

## Adım 1 — Değişiklikleri GitHub'a gönder

```bash
git push origin main
```

---

## Adım 2 — Railway'de proje oluştur

1. [railway.app](https://railway.app) → GitHub ile giriş yap
2. **"New Project"** → **"Deploy from GitHub repo"**
3. `beraerr/smart_school_assistant` seç

---

## Adım 3 — PostgreSQL ekle

Railway dashboard'da projenin içinde:
- **"+ New"** → **"Database"** → **"Add PostgreSQL"**
- Railway `DATABASE_URL` değişkenini otomatik oluşturur

---

## Adım 4 — Backend servisi ayarla

**Settings > Build:**
```
Dockerfile Path: Dockerfile
```

**Settings > Variables** (şunları ekle):
```
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-api03-...   ← kendi key'in
SECRET_KEY=<rastgele-güçlü-string>
DEBUG=false
```
> `DATABASE_URL` zaten PostgreSQL plugin'den otomatik gelir.

---

## Adım 5 — Frontend servisi ekle

Aynı proje içinde **"+ New"** → **"GitHub Repo"** → aynı repo'yu seç.

**Settings > Build:**
```
Dockerfile Path: Dockerfile.frontend
```

**Settings > Variables:**
```
API_BASE_URL=https://<backend-service-name>.up.railway.app
```
> Backend servisinin URL'sini Railway dashboard'dan kopyala.

---

## Adım 6 — Deploy!

Her iki servisi de **"Deploy"** yap. İlk build 3–5 dakika sürer.

**Frontend URL'si** Railway dashboard'dan al → demo için paylaş.

---

## Notlar

- Railway **free tier**: 500 saat/ay + 1 GB PostgreSQL (demo için yeterli)
- API key'i sadece Railway Variables içinde tut (repo dosyalarına yazma) ✓
- Streamlit'te API URL'yi frontend sidebar'dan da değiştirebilirsin

---

## Sorun çıkarsa

```bash
# Railway CLI ile log'ları takip et
npm install -g @railway/cli
railway login
railway logs --service backend
```
