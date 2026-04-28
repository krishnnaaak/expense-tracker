# Expense Tracker

A minimal full-stack expense tracking app — **FastAPI backend + vanilla HTML/JS frontend**.

**Live app:** [YOUR_FRONTEND_URL]  
**Backend API:** [YOUR_BACKEND_URL]  
**API Docs:** [YOUR_BACKEND_URL/docs]

---

## Running Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
# Update API_BASE in frontend/index.html to http://localhost:8000
# Then open in browser:
open frontend/index.html
# Or serve with:
npx serve frontend
```

### Tests
```bash
cd backend
pip install pytest httpx
pytest test_main.py -v
```

### Docker
```bash
cd backend
docker build -t expense-tracker-api .
docker run -p 8000:8000 -v $(pwd)/data:/data expense-tracker-api
```

---

## Key Design Decisions

### 1. Money as Integer Paise — Not Float
`amount` is stored as `INTEGER` paise in SQLite (₹10.50 → `1050`). 

Floating-point arithmetic is unsuitable for money: `0.1 + 0.2 = 0.30000000000000004`. Storing amounts as the smallest currency unit eliminates rounding errors entirely. The API accepts and returns amounts as decimal strings (`"10.50"`) using Python's `Decimal` for conversion, so precision is never lost at any layer.

### 2. Idempotency Key on POST /expenses
The frontend generates a `crypto.randomUUID()` **once per form submission** and sends it as `idempotency_key`. The backend stores this key with a `UNIQUE` constraint — if the same key arrives again (network retry, double-click, page reload mid-request), the existing record is returned unchanged with `201`.

This means: clicking submit 3× fast → creates exactly 1 expense.

### 3. SQLite over Postgres
Chosen for this timebox because:
- Zero infra setup — single file, ships inside the container
- WAL mode enabled for safe concurrent reads
- Sufficient for personal-scale data

**Trade-off I'd make in production:** Move to Postgres for multi-user workloads, connection pooling, and proper migrations (Alembic).

### 4. Vanilla JS Frontend (No Framework)
The UI requirements are simple enough that React would add build complexity with no real benefit here. A single `index.html` is deployable anywhere (Vercel, GitHub Pages, S3) with zero build step.

**Trade-off:** State management gets messier as features grow. Would switch to React + React Query for a production product.

### 5. Amount Stored as Paise, Returned as String
The API always returns `amount` as a decimal string (e.g. `"1234.50"`) rather than a float. This prevents JSON serialization from silently losing precision on large numbers.

---

## What I Intentionally Did Not Do

- **Authentication** — Out of scope for a single-user personal tool
- **Pagination** — Reasonable for <10k expenses; would add `offset/limit` for production
- **Edit/Delete** — Not in the acceptance criteria; avoided scope creep
- **ORM (SQLAlchemy)** — Direct sqlite3 is simpler and more transparent for this scale
- **React / build pipeline** — Zero build step was a conscious tradeoff for deployability

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/expenses` | Create expense (idempotent via `idempotency_key`) |
| `GET`  | `/expenses` | List expenses (`?category=Food&sort=date_desc`) |
| `GET`  | `/expenses/categories` | Distinct categories for filter dropdown |
| `GET`  | `/health` | Health check |

---

## Evaluation Checklist

- ✅ Idempotency: double-submit → 1 record
- ✅ Money handling: integer paise storage, no floats
- ✅ Filter by category (case-insensitive)
- ✅ Sort by date (newest first)
- ✅ Total shown for visible expenses
- ✅ Category summary breakdown
- ✅ Client-side + server-side validation
- ✅ Loading and error states
- ✅ Automated tests (unit + integration)
- ✅ Docker-ready backend
