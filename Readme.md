# Enterprise AI Knowledge Base Platform

An enterprise-grade, AI-powered internal knowledge base where employees upload company documentation and query it using natural language. Built with RAG (Retrieval-Augmented Generation), role-based access control, async document ingestion, audit logging, and citation-backed answers.

---

## What This Project Does

- Employees ask questions in plain English and get answers from internal company docs
- Every answer comes with citations — no hallucination
- Role-based access — employees only see their own department's docs
- Admins manage documents, users, and departments
- Full audit trail of every action in the system

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | Next.js 14 + TypeScript |
| Vector Database | Qdrant Cloud (free tier) |
| Database | PostgreSQL (Render managed) |
| Cache + Queue | Redis (Render managed) + Celery |
| File Storage | Cloudinary (free tier) |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | Claude (Anthropic) |
| Auth | OAuth 2.0 + JWT |
| Frontend Deploy | Vercel |
| Backend Deploy | Render |

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        VERCEL                               │
│                   Next.js Frontend                          │
│            Auto-deploys from GitHub on push                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS API calls
┌──────────────────────────▼──────────────────────────────────┐
│                        RENDER                               │
│                                                             │
│  ┌─────────────────┐      ┌──────────────────────────────┐  │
│  │   Web Service   │      │     Background Worker        │  │
│  │    FastAPI      │      │      Celery Worker           │  │
│  │   port 8000     │      │   (async doc ingestion)      │  │
│  └────────┬────────┘      └──────────────┬───────────────┘  │
│           │                              │                  │
│  ┌────────▼──────────────────────────────▼───────────────┐  │
│  │           Render Managed Services                     │  │
│  │    PostgreSQL            Redis                        │  │
│  │  (users, logs, docs)  (queue + cache)                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┴─────────────────┐
          │                                  │
┌─────────▼──────────┐            ┌──────────▼──────────┐
│    Qdrant Cloud     │            │     Cloudinary       │
│  (vector storage)   │            │   (file storage)     │
│    free 1GB tier    │            │     free tier        │
└─────────────────────┘            └─────────────────────┘
          │
┌─────────▼──────────┐
│  External AI APIs  │
│  Anthropic Claude  │
│  OpenAI Embeddings │
└────────────────────┘
```

---

## Folder Architecture

```
enterprise-kb-platform/
│
├── backend/                          # FastAPI application
│   │
│   ├── venv/                         # Python virtual environment (never committed)
│   │
│   ├── core/                         # Shared infrastructure — imported by all services
│   │   ├── config.py                 # All env vars via pydantic-settings
│   │   ├── database.py               # SQLAlchemy async engine + SessionLocal
│   │   ├── cache.py                  # Redis client + get/set/invalidate helpers
│   │   ├── storage.py                # Cloudinary client: upload, get_url, delete
│   │   ├── celery_app.py             # Celery factory: broker=Redis, backend=Redis
│   │   ├── exceptions.py             # Custom HTTP exceptions: NotFound, Forbidden etc.
│   │   └── schemas.py                # Shared Pydantic base schemas
│   │
│   ├── auth/                         # Authentication & session management
│   │   ├── router.py                 # /login /logout /refresh /forgot-password
│   │   ├── service.py                # JWT issuance, OTP dispatch, session CRUD
│   │   ├── schemas.py                # LoginRequest, TokenResponse, OTPRequest
│   │   ├── models.py                 # User, Session, OTPCode SQLAlchemy models
│   │   └── dependencies.py           # get_current_user, require_role, rate_limit
│   │
│   ├── departments/                  # Department and user management
│   │   ├── router.py                 # Create/delete dept, invite/remove users
│   │   ├── service.py                # Business logic, role assignment checks
│   │   └── models.py                 # Department, UserDepartment models
│   │
│   ├── ingestion/                    # Async document ingestion pipeline (GenAI)
│   │   ├── router.py                 # Upload endpoint, status polling
│   │   ├── service.py                # Orchestrates: validate→parse→chunk→embed→store
│   │   ├── tasks.py                  # Celery tasks: process_document, retry, delete
│   │   ├── parsers.py                # PDF, DOCX, PPTX, XLSX, Markdown, code parsers
│   │   ├── chunkers.py               # Content-aware chunking per file type
│   │   └── models.py                 # Document, Chunk, IngestionJob models
│   │
│   ├── rag/                          # RAG query pipeline (GenAI)
│   │   ├── router.py                 # POST /query, chat sessions, feedback
│   │   ├── service.py                # embed→filter→retrieve→rerank→LLM→cite
│   │   ├── vector_store.py           # Qdrant client: upsert, search, delete
│   │   ├── embedder.py               # Embedding model abstraction (OpenAI)
│   │   ├── llm_client.py             # Claude API client with streaming
│   │   ├── prompts.py                # System prompts, RAG templates, citation prompts
│   │   ├── reranker.py               # Cross-encoder reranker for top-k refinement
│   │   └── schemas.py                # QueryRequest, QueryResponse, Citation schemas
│   │
│   ├── audit/                        # Audit logging — every action tracked
│   │   ├── router.py                 # GET /logs with filters, CSV export
│   │   ├── service.py                # log_action() called by all other services
│   │   └── models.py                 # AuditLog: actor, action, target, ip, status
│   │
│   ├── analytics/                    # Usage analytics dashboards
│   │   ├── router.py                 # /analytics/company and /analytics/dept/:id
│   │   └── service.py                # SQL aggregations: top docs, peak times, gaps
│   │
│   ├── notifications/                # In-app and email notifications
│   │   ├── tasks.py                  # send_email(), send_in_app_alert() Celery tasks
│   │   └── templates/                # Email templates (ingestion_failed, security etc.)
│   │
│   ├── migrations/                   # Alembic database migrations
│   │   ├── env.py                    # Async migration support, imports all models
│   │   └── versions/                 # Auto-generated migration scripts
│   │
│   ├── scripts/                      # One-off deployment scripts
│   │   ├── seed_super_admin.py       # Creates super admin at deploy — never via UI
│   │   └── cleanup_vectors.py        # Removes orphaned Qdrant vectors
│   │
│   ├── tests/                        # Pytest test suite
│   │   ├── conftest.py               # Fixtures: test DB, mock Qdrant, test users
│   │   ├── unit/                     # Unit tests per service
│   │   └── integration/              # End-to-end: upload→ingest→query→audit
│   │
│   ├── main.py                       # FastAPI app factory, registers all routers
│   └── requirements.txt              # All Python dependencies
│
├── frontend/                         # Next.js 14 App Router
│   │
│   ├── app/                          # Pages and layouts (App Router)
│   │   ├── layout.tsx                # Root layout: AuthProvider, ThemeProvider
│   │   ├── (auth)/                   # Login, forgot-password, reset-password
│   │   ├── (super-admin)/admin/      # Super admin dashboard
│   │   ├── (dept-admin)/dashboard/   # Dept admin dashboard
│   │   └── (employee)/chat/          # Employee chat interface
│   │
│   ├── components/                   # Reusable UI components
│   │   ├── ui/                       # Button, Input, Modal, Table, Toast etc.
│   │   ├── chat/                     # MessageBubble, CitationCard, FeedbackButtons
│   │   ├── documents/                # UploadDropzone, IngestionStatusBadge
│   │   └── analytics/                # Charts, TopDocsList, FeedbackSummary
│   │
│   ├── hooks/                        # TanStack Query hooks
│   │   ├── useAuth.ts                # useLogin, useLogout, useCurrentUser
│   │   ├── useDocuments.ts           # useUploadDocument, useIngestionStatus
│   │   └── useChat.ts                # useQuery, useChatSessions, useSubmitFeedback
│   │
│   ├── lib/                          # API client and auth state
│   │   ├── api-client.ts             # Axios: base URL, JWT injection, refresh interceptor
│   │   └── auth-store.ts             # Access token in memory (not localStorage)
│   │
│   └── types/                        # TypeScript interfaces matching backend schemas
│       ├── auth.ts                   # User, Role, Department, Session
│       ├── documents.ts              # Document, Chunk, IngestionJob
│       └── chat.ts                   # QueryRequest, QueryResponse, Citation
│
├── .env.example                      # All required env vars documented
├── .gitignore                        # Excludes venv, node_modules, .env, .next
├── Makefile                          # Shortcuts: make dev, test, migrate, seed, lint
└── README.md                         # This file
```

---

## RAG Pipeline Flow

```
Employee types a question
        │
        ▼
  FastAPI /query endpoint
        │
        ▼
  Embed the query (OpenAI text-embedding-3-small)
        │
        ▼
  Search Qdrant with metadata filter
  (dept_id + access_level — enforced at query time, not UI)
        │
        ▼
  Rerank top-k results (cross-encoder)
        │
        ▼
  Assemble context from top chunks
        │
        ▼
  Call Claude API with system prompt + context + question
        │
        ▼
  Extract citations from response
        │
        ▼
  Return answer + citations to employee
  "According to [HR Policy v2.pdf]..."
        │
        ▼
  Write audit log entry (async, non-blocking)
```

---

## Document Ingestion Pipeline

```
Dept admin uploads a file
        │
        ▼
  FastAPI validates file type and size
        │
        ▼
  File saved to Cloudinary (raw storage)
        │
        ▼
  IngestionJob created in PostgreSQL (status: PROCESSING)
        │
        ▼
  Celery task queued via Redis
        │
        ▼
  Celery worker picks up task:
    1. Parse file (PDF→pdfplumber, DOCX, PPTX, XLSX, MD, code)
    2. Chunk content (content-aware per file type)
       - PDF       → semantic chunking
       - Markdown  → header-aware chunking
       - Code      → function/class level chunking
       - Excel/CSV → row-group chunking
       - PPTX      → slide-level chunking
    3. Embed each chunk (OpenAI embeddings)
    4. Upsert vectors to Qdrant with metadata:
       {file_id, dept_id, access_level, chunk_index}
    5. Update IngestionJob → status: COMPLETED
        │
        ▼
  Dept admin notified (in-app + email)
```

---

## User Roles

| Role | Created By | Access |
|---|---|---|
| Super Admin | Seed script at deploy | All depts + global docs |
| Dept Admin | Super admin only | Own dept + global docs |
| Employee | Self-register with company email OR invited | Own dept + global docs |

Access is enforced at the **vector query level**, not the UI level. A user cannot retrieve vectors from another department even if they call the API directly.

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL installed locally
- Redis installed locally

### Backend

```bash
cd backend

# create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# install dependencies
pip install -r requirements.txt

# copy and fill environment variables
cp ../.env.example .env

# run database migrations
alembic upgrade head

# seed super admin (run once)
python scripts/seed_super_admin.py

# start FastAPI
uvicorn main:app --reload

# start Celery worker (new terminal, venv activated)
celery -A core.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # add NEXT_PUBLIC_API_URL
npm run dev
```

---

## Environment Variables

```bash
# PostgreSQL — Render gives this string
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname

# Redis — Render gives this string
REDIS_URL=redis://...

# Qdrant Cloud
QDRANT_URL=https://xxx.qdrant.io
QDRANT_API_KEY=your-api-key

# Cloudinary
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# AI
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Auth
JWT_SECRET=your-long-random-secret
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Super Admin (used by seed script only)
SUPER_ADMIN_EMAIL=admin@company.com
SUPER_ADMIN_PASSWORD=strongpassword
```

---

## Build Order (Development Phases)
The Actual Workflow

The Daily Workflow (repeat for every phase)
Plan → Code → Test locally → Commit → Move to next file
Never jump between phases. Finish one completely before starting next.

Phase by Phase — What You Actually Do

Phase 2 — Backend Core
Step 1  →  Write requirements.txt
Step 2  →  pip install -r requirements.txt
Step 3  →  Write core/config.py
Step 4  →  Write core/exceptions.py
Step 5  →  Write core/schemas.py
Step 6  →  Write core/database.py
Step 7  →  Write main.py
Step 8  →  Run uvicorn main:app --reload
Step 9  →  Open localhost:8000/docs — confirm it works
Step 10 →  Commit

Phase 3 — Database Models + Migrations
Step 1  →  Write all models (auth, departments, ingestion, audit, rag)
Step 2  →  pip install alembic
Step 3  →  alembic init migrations
Step 4  →  Configure migrations/env.py
Step 5  →  alembic revision --autogenerate -m "initial tables"
Step 6  →  alembic upgrade head
Step 7  →  Open PostgreSQL, confirm all tables created
Step 8  →  Commit

Phase 4 — Auth
Step 1  →  Write auth/models.py
Step 2  →  Write auth/schemas.py
Step 3  →  Write auth/service.py
Step 4  →  Write auth/dependencies.py
Step 5  →  Write auth/router.py
Step 6  →  Register router in main.py
Step 7  →  Run seed_super_admin.py — confirm super admin created in DB
Step 8  →  Test /login in /docs — confirm JWT returned
Step 9  →  Test /refresh — confirm new token returned
Step 10 →  Test wrong password — confirm 401 returned
Step 11 →  Test role check — confirm employee cannot access admin route
Step 12 →  Commit

Phase 5 — Departments
Step 1  →  Write departments/models.py
Step 2  →  Write departments/schemas.py
Step 3  →  Write departments/service.py
Step 4  →  Write departments/router.py
Step 5  →  Register router in main.py
Step 6  →  Test create department as super admin
Step 7  →  Test invite employee as dept admin
Step 8  →  Test that employee cannot create department
Step 9  →  Commit

Phase 6 — Storage + Queue Setup
Step 1  →  Sign up Cloudinary → get API keys → add to .env
Step 2  →  Write core/storage.py (Cloudinary client)
Step 3  →  Test file upload and URL retrieval manually
Step 4  →  Sign up Qdrant Cloud → get URL + API key → add to .env
Step 5  →  Write core/cache.py (Redis client)
Step 6  →  Write core/celery_app.py
Step 7  →  Run celery worker in terminal 2
Step 8  →  Send a test task — confirm worker picks it up
Step 9  →  Commit

Phase 7 — Document Ingestion (hardest phase)
Step 1  →  Write ingestion/models.py
Step 2  →  Write ingestion/parsers.py
           → test each parser individually with a real file
           → PDF works? ✅ DOCX works? ✅ etc.
Step 3  →  Write ingestion/chunkers.py
           → test each chunker — print chunks to console
           → confirm chunk size is 512-1024 tokens
Step 4  →  Write rag/embedder.py
           → test embed one chunk — confirm vector returned
Step 5  →  Write rag/vector_store.py
           → test upsert one vector to Qdrant
           → open Qdrant Cloud dashboard — confirm it appears
Step 6  →  Write ingestion/tasks.py (Celery task)
           → wire parsers + chunkers + embedder + vector_store
Step 7  →  Write ingestion/service.py
Step 8  →  Write ingestion/router.py
Step 9  →  Register router in main.py
Step 10 →  Upload a real PDF via /docs
           → watch Celery terminal process it
           → check Qdrant dashboard for vectors
Step 11 →  Test failed ingestion — upload corrupt file
           → confirm status shows FAILED with error reason
Step 12 →  Commit

Phase 8 — RAG Query Pipeline (the core feature)
Step 1  →  Write rag/prompts.py
Step 2  →  Write rag/llm_client.py
           → test calling Claude API directly — confirm response
Step 3  →  Write rag/reranker.py
Step 4  →  Write rag/schemas.py
Step 5  →  Write rag/service.py
           → wire embedder + vector_store + reranker + llm_client
Step 6  →  Write rag/router.py
Step 7  →  Register router in main.py
Step 8  →  Upload a document (Phase 7)
           → ask a question about it via /docs
           → confirm answer returned with citations
Step 9  →  Test access control
           → employee A queries doc from dept B
           → confirm empty result, not the answer
Step 10 →  Test no-answer fallback
           → ask something not in any doc
           → confirm "No relevant information found"
Step 11 →  Commit

Phase 9 — Audit + Analytics + Notifications
Step 1  →  Write audit/models.py + service.py + router.py
Step 2  →  Add log_action() call to every existing endpoint
Step 3  →  Test — perform any action, check audit log in DB
Step 4  →  Write analytics/service.py + router.py
Step 5  →  Test analytics endpoints return real data
Step 6  →  Write notifications/tasks.py + email templates
Step 7  →  Test notification fires on ingestion complete
Step 8  →  Commit

Phase 10 — Tests
Step 1  →  Write tests/conftest.py (fixtures)
Step 2  →  Write unit tests for auth service
Step 3  →  Write unit tests for chunkers and parsers
Step 4  →  Write integration test: upload → ingest → query
Step 5  →  Write integration test: role access control
Step 6  →  Run pytest — all green
Step 7  →  Commit

Phase 11 — Frontend
Step 1  →  npx create-next-app@latest frontend
Step 2  →  Write types/ (auth.ts, documents.ts, chat.ts)
Step 3  →  Write lib/api-client.ts (Axios + JWT interceptor)
Step 4  →  Write lib/auth-store.ts
Step 5  →  Build (auth) pages — login, forgot password
Step 6  →  Test login works end to end with real backend
Step 7  →  Build (employee)/chat/ — the core UI
Step 8  →  Test full flow: login → ask question → see answer + citations
Step 9  →  Build (dept-admin)/dashboard/
Step 10 →  Build (super-admin)/admin/
Step 11 →  Commit

Phase 12 — Deploy
Step 1  →  Push everything to GitHub main
Step 2  →  Render → create Web Service → connect repo → add env vars
Step 3  →  Render → create Background Worker → same repo
Step 4  →  Render → create PostgreSQL → copy DATABASE_URL
Step 5  →  Render → create Redis → copy REDIS_URL
Step 6  →  Run alembic upgrade head against Render PostgreSQL
Step 7  →  Run seed_super_admin.py against Render PostgreSQL
Step 8  →  Vercel → connect repo → set frontend/ as root → add env vars
Step 9  →  Test full flow on production URL
Step 10 →  Done

The Golden Rules
✅ Test every file before moving to the next
✅ Never start a new phase with broken code from previous phase
✅ Commit at the end of every working phase
✅ Always test with real data (real PDFs, real questions)
✅ Keep your .env updated as you add new services
✅ Read error messages fully before asking for help
❌ Never skip testing and jump to next phase
❌ Never code frontend before backend is fully working
❌ Never push broken code to main

---



## Deployment (No Docker Required)

### Render (Backend)
1. Connect GitHub repo to Render
2. Create **Web Service** → root directory: `backend/` → start command: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. Create **Background Worker** → same repo → start command: `celery -A core.celery_app worker`
4. Create **PostgreSQL** database → copy connection string to env vars
5. Create **Redis** instance → copy URL to env vars
6. Add all env vars from `.env.example`

### Vercel (Frontend)
1. Connect GitHub repo to Vercel
2. Set root directory: `frontend/`
3. Add `NEXT_PUBLIC_API_URL` pointing to your Render backend URL
4. Deploy — auto-deploys on every push to main

### Qdrant Cloud
1. Sign up at cloud.qdrant.io
2. Create a free cluster
3. Copy URL and API key to Render env vars

### Cloudinary
1. Sign up at cloudinary.com
2. Copy cloud name, API key, API secret to Render env vars

---

## Key Design Decisions

**Single embedding model for all file types**
Mixing embedding models breaks vector space similarity. One model, one collection, metadata filters for access control.

**Access enforced at query time not UI level**
Qdrant filter applied on every search: `{dept_id: user.dept_id, access_level: ["dept", "global"]}`. Frontend cannot bypass this.

**Async ingestion via Celery**
Document processing (parse + chunk + embed) is slow and must not block the API. Celery workers handle it asynchronously. Status is polled by the frontend.

**No answer hallucination**
If Qdrant retrieval confidence is below threshold, the system returns "No relevant information found" instead of guessing.

**Super admin via seed script only**
No public endpoint can create a super admin. Prevents privilege escalation.

**JWT access token in memory (not localStorage)**
Protects against XSS. Refresh token in httpOnly cookie. Silent refresh on expiry.
