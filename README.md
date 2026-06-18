<div align="right">

**English** | [Türkçe](README.tr.md)

</div>

# Ders Forumu

An anonymous instructor & course review platform built for Sabancı University students.
Students can anonymously write reviews for professors and courses, apply semester-based filters, and vote comments as helpful or not helpful.

> 🌐 **Language:** This page is in English. Click **[Türkçe](README.tr.md)** above to read it in Turkish.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Database | PostgreSQL 16 |
| Frontend | React + TypeScript + Tailwind CSS + Vite |
| Auth | JWT + email OTP (Gmail SMTP) |
| Container | Docker + Docker Compose |
| Cloud (AWS) | ECS Fargate, RDS, ElastiCache, CloudFront, Cognito, Terraform IaC |

---

## Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd CS436-Project
```

### 2. Create the `.env` file

```bash
cp .env.example .env
```

Then open `.env` and fill in the following fields:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Choose based on Scenario A/B (explained inside the file) |
| `JWT_SECRET` | Generate with `openssl rand -hex 32` |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Gmail **app password** (not your regular password) |
| `SMTP_FROM` | Your Gmail address (can be the same as SMTP_USER) |

> **How to get a Gmail app password?**
> Google Account → Security → 2-Step Verification (must be enabled) → App passwords → Create new

> **What happens if SMTP is left empty?**
> OTP codes are written to the terminal logs instead of being emailed. This is sufficient for a development environment.

---

## Running the App

Three different scenarios are supported. Pick one:

---

### Scenario A — Everything in Docker (easiest)

Backend + database run in Docker, frontend runs locally.

```bash
# 1) Start the containers
docker compose up -d

# 2) Apply migrations (on first setup and whenever a new migration arrives)
docker exec ders_forumu_api alembic upgrade head

# 3) Install frontend dependencies (on first setup)
cd frontend && npm install

# 4) Start the frontend
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

### Scenario B — Only DB in Docker, backend local

If you want to quickly test code changes, you can run the backend locally.

```bash
# 1) In .env, point DATABASE_URL to localhost:
#    DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/ders_forumu

# 2) Start only the database in Docker
docker compose up -d db

# 3) Create a Python virtual environment (on first setup)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4) Apply migrations (on first setup and whenever a new migration arrives)
alembic upgrade head

# 5) Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6) In a separate terminal, start the frontend
cd frontend && npm install && npm run dev
```

---

### Scenario C — Everything local (no Docker)

```bash
# Install and start PostgreSQL
brew install postgresql@16
brew services start postgresql@16
createdb ders_forumu

# DATABASE_URL in .env:
# DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/ders_forumu

# Remaining steps are the same as Scenario B's steps 3–6
```

---

## First-Time Setup Summary (Scenario A)

```bash
git clone <repo-url> && cd CS436-Project
cp .env.example .env          # edit .env (JWT_SECRET + SMTP)
docker compose up -d
docker exec ders_forumu_api alembic upgrade head
cd frontend && npm install && npm run dev
```

---

## When a New Migration Arrives

If a teammate added a new migration and you ran `git pull`:

```bash
# Scenario A (Docker)
docker exec ders_forumu_api alembic upgrade head

# Scenario B/C (local backend)
alembic upgrade head
```

---

## Project Structure

```
CS436-Project/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Env settings
│   ├── database.py          # SQLAlchemy engine & session
│   ├── models/              # ORM models
│   ├── routes/              # API endpoints
│   ├── schemas/             # Pydantic request/response models
│   ├── auth/                # JWT & dependencies
│   └── utils/               # Helper functions
├── alembic/
│   └── versions/            # Migration files
├── frontend/
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── api/             # Backend API calls
│   │   ├── contexts/        # React contexts (Auth, etc.)
│   │   └── types/           # TypeScript type definitions
│   └── package.json
├── infra/                   # Terraform infrastructure-as-code (AWS)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example             # Copy → .env, then fill in
└── .gitignore
```

---

## Commit Format

```
feat:     new feature
fix:      bug fix
refactor: code cleanup
docs:     documentation
chore:    dependency / configuration
```
