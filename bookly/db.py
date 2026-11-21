"""SQLite access for Bookly's mock backend.

Plain sqlite3, no ORM: the schema is small and the queries are what a
reviewer should be able to read in one screen.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "bookly.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    phone           TEXT UNIQUE,          -- E.164
    email           TEXT UNIQUE,
    zip             TEXT NOT NULL,        -- account / billing ZIP
    recent_contacts INTEGER NOT NULL DEFAULT 0,  -- support contacts in last 14 days
    store_credit_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    order_number  TEXT PRIMARY KEY,       -- 6 digits, easy to say on a call
    customer_id   INTEGER NOT NULL REFERENCES customers(id),
    status        TEXT NOT NULL CHECK (status IN ('processing','shipped','delivered','lost','cancelled')),
    placed_at     TEXT NOT NULL,          -- ISO date
    shipped_at    TEXT,
    delivered_at  TEXT,
    eta           TEXT,
    carrier       TEXT,
    tracking_number TEXT,
    ship_zip      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY,
    order_number TEXT NOT NULL REFERENCES orders(order_number),
    title        TEXT NOT NULL,
    author       TEXT NOT NULL,
    format       TEXT NOT NULL DEFAULT 'paperback',
    price_cents  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS returns (
    id            INTEGER PRIMARY KEY,
    order_number  TEXT NOT NULL REFERENCES orders(order_number),
    item_id       INTEGER NOT NULL UNIQUE REFERENCES order_items(id),  -- one return per item: idempotency
    reason        TEXT NOT NULL,
    resolution    TEXT NOT NULL CHECK (resolution IN ('refund','store_credit')),
    amount_cents  INTEGER NOT NULL,
    status        TEXT NOT NULL,          -- awaiting_book | credit_issued
    credit_issued INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

-- Outbound messages that would hit SMS/email providers in production.
CREATE TABLE IF NOT EXISTS outbox (
    id         INTEGER PRIMARY KEY,
    channel    TEXT NOT NULL,             -- sms | email
    recipient  TEXT NOT NULL,
    kind       TEXT NOT NULL,             -- receipt | password_reset | tracking
    body       TEXT NOT NULL,
    dedupe_key TEXT UNIQUE,
    created_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    return Path(os.environ.get("BOOKLY_DB", DEFAULT_DB))


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def catalog_titles(conn: sqlite3.Connection) -> list[str]:
    """Distinct titles + authors; used for STT key-term boosting in phone mode."""
    rows = conn.execute("SELECT DISTINCT title, author FROM order_items").fetchall()
    terms: list[str] = []
    for r in rows:
        terms += [r["title"], r["author"]]
    return sorted(set(terms))
