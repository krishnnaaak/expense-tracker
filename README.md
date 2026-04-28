# Expense Tracker

A minimal full-stack expense tracking app — **FastAPI backend + vanilla HTML/JS frontend**.

* **Live App:** https://expense-tracker-virid-ten-84.vercel.app/
* **Backend API:** https://expense-tracker-backend-jvl8.onrender.com
* **API Docs:** https://expense-tracker-backend-jvl8.onrender.com/docs

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

Floating-point arithmetic is unsuitable for money: `0.1 + 0.2 = 0.30000000000000004`.
Storing amounts as the smallest currency unit eliminates rounding errors entirely.

The API accepts and returns amounts as decimal strings (`"10.50"`) using Python's `Decimal`.

---

### 2. Idempotency Key on POST /expenses

The frontend generates a `crypto.randomUUID()` once per submission and sends it as `idempotency_key`.
The backend enforces a `UNIQUE` constraint.

This ensures:

* Double-click → 1 record
* Network retry → no duplicates
* Page refresh during submit → safe

This directly addresses **real-world unreliable network conditions**.

---

### 3. SQLite over Postgres

Chosen for simplicity and timebox:

* Zero setup
* Single-file persistence
* WAL mode enabled

**Production trade-off:** Move to Postgres for concurrency, scaling, and migrations.

---

### 4. Vanilla JS Frontend

Chosen for:

* Zero build step
* Easy deployment (Vercel/static hosting)
* Faster iteration

**Trade-off:** Not scalable for complex state → would switch to React in production.

---

### 5. API Design for Correctness

* Amount returned as string (not float)
* Case-insensitive filtering
* Sorting by `created_at` ensures true chronological order

---

## Real-World Conditions Handling

This system is designed to behave correctly under realistic conditions:

* Duplicate submissions → handled via idempotency key
* Page refresh after submit → data persists (SQLite)
* Slow backend / cold start → frontend shows error states
* Retry safety → repeated POST returns the same record

---

## What I Intentionally Did Not Do

* Authentication — single-user scope
* Pagination — unnecessary for small datasets
* Edit/Delete — not required
* ORM (SQLAlchemy) — direct SQL keeps system simple
* Complex frontend framework — avoided unnecessary complexity

---

## Known Limitations

* Backend is hosted on Render free tier → may take ~5–10 seconds to wake up after inactivity
* No pagination for very large datasets
* No authentication / multi-user support

---

## API Reference

| Method | Endpoint               | Description                                       |
| ------ | ---------------------- | ------------------------------------------------- |
| `POST` | `/expenses`            | Create expense (idempotent via `idempotency_key`) |
| `GET`  | `/expenses`            | List expenses (`?category=Food&sort=date_desc`)   |
| `GET`  | `/expenses/categories` | Distinct categories                               |
| `GET`  | `/health`              | Health check                                      |

---

## Evaluation Checklist

* ✅ Idempotency (retry-safe POST)
* ✅ Correct money handling (no float precision issues)
* ✅ Filter by category
* ✅ Sort by newest (`created_at`)
* ✅ Total calculation (frontend)
* ✅ Category summary
* ✅ Validation (client + server)
* ✅ Error + loading states
* ✅ Deployment (frontend + backend live)

---

## Notes for Reviewer

* The deployed app includes a few sample entries for demonstration
* Try clicking "Add Expense" multiple times quickly → only one entry will be created
* Sorting reflects actual creation time, not just date
