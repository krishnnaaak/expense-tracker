"""Expense Tracker API
-------------------
FastAPI backend with SQLite persistence.
Idempotency-safe POST via client-supplied idempotency_key.
Amount stored as INTEGER paise (1 INR = 100 paise) to avoid float precision issues.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional
import sqlite3
import uuid
from datetime import datetime, date
from decimal import Decimal
import os

DB_PATH = os.getenv("DB_PATH", "expenses.db")

app = FastAPI(title="Expense Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent reads
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id           TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,          -- prevents duplicate on retry
                amount_paise INTEGER NOT NULL,         -- store as paise, never float
                category     TEXT NOT NULL,
                description  TEXT NOT NULL DEFAULT '',
                date         TEXT NOT NULL,            -- ISO 8601 date string
                created_at   TEXT NOT NULL
            )
        """)
        conn.commit()


init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExpenseCreate(BaseModel):
    amount: str                   # accept as string to preserve precision ("1234.50")
    category: str
    description: str = ""
    date: str                     # ISO date: "2025-04-28"
    idempotency_key: Optional[str] = None   # client sends UUID; generated server-side if absent

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        try:
            d = Decimal(v)
        except Exception:
            raise ValueError("amount must be a valid number")
        if d <= 0:
            raise ValueError("amount must be positive")
        if d > Decimal("10000000"):  # sanity cap: 1 crore
            raise ValueError("amount too large")
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be YYYY-MM-DD")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if not v.strip():
            raise ValueError("category cannot be blank")
        return v.strip()


class ExpenseOut(BaseModel):
    id: str
    amount: str           # returned as decimal string e.g. "1234.50"
    category: str
    description: str
    date: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def paise_to_str(paise: int) -> str:
    """Convert integer paise back to INR string with 2 decimal places."""
    return f"{Decimal(paise) / 100:.2f}"


def str_to_paise(amount_str: str) -> int:
    """Convert decimal string to integer paise."""
    return int((Decimal(amount_str) * 100).to_integral_value())


def row_to_expense(row) -> dict:
    return {
        "id": row["id"],
        "amount": paise_to_str(row["amount_paise"]),
        "category": row["category"],
        "description": row["description"],
        "date": row["date"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(body: ExpenseCreate):
    """
    Create an expense. Idempotent: if the same idempotency_key is sent again
    (e.g. network retry), we return the existing record unchanged instead of
    creating a duplicate.
    """
    idem_key = body.idempotency_key or str(uuid.uuid4())

    with get_db() as conn:
        # Check for existing record with this idempotency key
        existing = conn.execute(
            "SELECT * FROM expenses WHERE idempotency_key = ?", (idem_key,)
        ).fetchone()

        if existing:
            return row_to_expense(existing)

        expense_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + "Z"
        amount_paise = str_to_paise(body.amount)

        conn.execute(
            """
            INSERT INTO expenses (id, idempotency_key, amount_paise, category, description, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (expense_id, idem_key, amount_paise, body.category, body.description, body.date, created_at),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        return row_to_expense(row)


@app.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(
    category: Optional[str] = Query(None, description="Filter by category"),
    sort: Optional[str] = Query(None, description="Use 'date_desc' to sort newest first"),
):
    """
    Return list of expenses with optional category filter and date sorting.
    """
    sql = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if category:
        sql += " AND LOWER(category) = LOWER(?)"
        params.append(category)

    if sort == "date_desc":
        sql += " ORDER BY date DESC, created_at DESC"
    else:
        sql += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [row_to_expense(r) for r in rows]


@app.get("/expenses/categories", response_model=list[str])
def list_categories():
    """Return distinct categories for filter dropdown."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM expenses ORDER BY category ASC"
        ).fetchall()
    return [r["category"] for r in rows]


@app.get("/health")
def health():
    return {"status": "ok"}
