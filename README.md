# Audito

**LLM Data Memorization & Privacy Leakage Auditing Platform**

Audito lets you audit AI model outputs for privacy risks. Upload a reference dataset (potential training data) and a generated dataset (model outputs), and Audito runs a 6-engine analysis pipeline to detect memorization, PII leakage, and training data exposure — returning a single risk score with a full breakdown and downloadable PDF report.

---

## Demo

<!-- Add demo video here -->
> 📹 [DEMO VIDEO](https://drive.google.com/file/d/1cwdHXxpTOd-u3bJhVL3aAaCk80ej7SlP/view?usp=drive_link)

---

## Architecture

<!-- Add architecture diagram here -->
> 🗺️ ![Architecture Diagram](https://drive.google.com/file/d/1P_gyUleos3tvafLmG1fQ46YWHkq8yJmx/view?usp=drive_link)

**High-level flow:**

```
User → Next.js Frontend
         ↓ REST API (JWT auth)
     FastAPI Backend
         ↓ enqueues task
     Celery Worker  ←→  Redis (broker)
         ↓ runs pipeline
     6-Engine Audit Orchestrator
         ↓ persists results
     PostgreSQL
```

---

## How It Works

Each audit runs 6 independent engines in sequence, each contributing a weighted component to the final 0–100 risk score:

| Engine | Weight | What it detects |
|---|---|---|
| Exact Match | 25% | Verbatim string matches + Levenshtein similarity (>0.85) + n-gram overlap |
| Semantic Similarity | 25% | Dense vector similarity via `sentence-transformers` + FAISS nearest-neighbor search |
| Membership Inference | 20% | Token frequency analysis + 4-gram phrase overlap to estimate training data membership |
| Canary Exposure | 15% | Detects user-defined canary strings and common secret patterns in outputs |
| Sensitive Data Detection | 15% | Regex scanning for PII: emails, phone numbers, SSNs, credit cards, API keys, JWTs, AWS keys, private keys, passwords |
| Risk Scoring | — | Weighted combination → 0–100 score → Low / Medium / High / Critical |

---

## Features

- **Project management** — group audits by AI model under named projects
- **Dataset upload** — upload reference and generated datasets as CSV, JSON, or TXT (up to 50 MB)
- **Async audit pipeline** — audits run in the background via Celery with real-time progress polling
- **Detailed results** — per-engine scores, top semantic matches, sensitive findings with masked values, canary hits
- **PDF reports** — generate and download professional audit reports with score breakdowns and recommendations
- **Dashboard analytics** — risk distribution charts, average risk score, recent audit history
- **In-app notifications** — notified when audits complete with risk level summary
- **Role-based access** — `admin`, `researcher`, and `viewer` roles with enforced permissions
- **Rate limiting** — built-in API rate limiting via `slowapi`

---

## Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- PostgreSQL (Neon) + SQLAlchemy 2.0
- Celery + Redis
- `sentence-transformers` (`all-mpnet-base-v2`) + FAISS for semantic search
- `python-jose` + `passlib[bcrypt]` for JWT auth
- ReportLab for PDF generation
- Loguru for structured logging

**Frontend**
- [Next.js 15](https://nextjs.org/) (App Router, standalone output)
- TypeScript + Tailwind CSS
- Recharts for dashboard visualizations
- Radix UI primitives
- Axios with cookie-based JWT

**Infrastructure**
- Docker + Docker Compose
- Deployable to Railway (backend) and Vercel (frontend)

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- (For local dev without Docker) Python 3.11+, Node.js 18+, PostgreSQL or Neon Cloud, Redis Cloud

### Run with Docker

```bash
git clone https://github.com/your-org/audito.git
cd audito

# Set a secure secret key
export SECRET_KEY=your-secret-key-here

docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### Local Development

**Backend**

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql://audito:audito_pass@localhost:5432/audito
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-development
FRONTEND_URL=http://localhost:3000
```

```bash
# Start API
uvicorn main:app --reload

# Start Celery worker (separate terminal)
celery -A workers.celery_app worker --loglevel=info
```

**Frontend**

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
```

---

## API Overview

All routes are prefixed with `/api`. Authentication uses Bearer tokens (JWT).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login, returns JWT |
| `GET` | `/api/auth/me` | Get current user |
| `GET/POST` | `/api/projects` | List / create projects |
| `GET/PATCH/DELETE` | `/api/projects/{id}` | Manage a project |
| `POST` | `/api/datasets` | Upload a dataset (multipart) |
| `GET` | `/api/datasets/project/{id}` | List datasets for a project |
| `POST` | `/api/audits` | Create and queue an audit |
| `GET` | `/api/audits/{id}` | Get audit status and results |
| `GET` | `/api/audits/project/{id}` | List audits for a project |
| `POST` | `/api/reports/{audit_id}/generate` | Generate PDF report |
| `GET` | `/api/reports/{audit_id}/download` | Download PDF report |
| `GET` | `/api/analytics/dashboard` | Dashboard summary stats |
| `GET` | `/api/notifications` | List notifications |
| `PATCH` | `/api/notifications/{id}/read` | Mark notification as read |

Full interactive docs at `/docs` (Swagger UI) when the backend is running.

---

## Risk Scoring

```
Risk Score = (exact_match × 0.25) + (semantic_sim × 0.25) + (membership × 0.20)
           + (canary_exposure/100 × 0.15) + (sensitive_data × 0.15)
```

Thresholds:

| Score | Level |
|---|---|
| 0–25 | 🟢 Low |
| 26–50 | 🟡 Medium |
| 51–75 | 🟠 High |
| 76–100 | 🔴 Critical |

---

## Project Structure

```
audito/
├── backend/
│   ├── api/routes/         # FastAPI route handlers
│   ├── detection/          # Exact match + sensitive data engines
│   ├── similarity/         # Semantic similarity (FAISS)
│   ├── membership/         # Membership inference engine
│   ├── exposure/           # Canary exposure engine
│   ├── scoring/            # Risk scoring engine
│   ├── services/           # Audit orchestrator
│   ├── workers/            # Celery app + tasks
│   ├── models/             # SQLAlchemy ORM models
│   ├── reports/            # PDF report generator
│   └── utils/              # Auth, logging, dataset loader
└── frontend/
    ├── app/                # Next.js App Router pages
    ├── components/         # UI components
    ├── lib/                # API client, auth utilities
    └── types/              # TypeScript type definitions
```

---

## Deployment

**Backend → Railway**

The `backend/railway.toml` is pre-configured. Set `SECRET_KEY`, `DATABASE_URL`, and `REDIS_URL` as environment variables in your Railway project. The Celery worker runs as a separate service using the same Docker image with the command override from `docker-compose.yml`.

**Frontend → Vercel**

Set `NEXT_PUBLIC_API_URL` to your Railway backend URL. The Next.js config is set to `output: 'standalone'` and `frontend/vercel.json` handles routing.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `SECRET_KEY` | ✅ | JWT signing secret — use a long random string in production |
| `ALGORITHM` | | JWT algorithm, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Token TTL, default `30` |
| `FRONTEND_URL` | | Frontend origin for CORS, default `http://localhost:3000` |
| `UPLOAD_DIR` | | Dataset upload directory, default `uploads` |
| `MAX_UPLOAD_SIZE_MB` | | Max file size, default `50` |

---

## License

MIT
