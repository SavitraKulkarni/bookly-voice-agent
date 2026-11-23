"""Seed the Bookly mock backend.

Dates are relative to today so the 30-day return window behaves the same
whenever a reviewer runs this.

    python -m data.seed            # writes data/bookly.db
    python -m data.seed --db PATH  # any path (simulations use temp copies)

Coverage (see CLAUDE.md "Seed data must cover"):
  Maya Chen      multi-order customer; 418027 is a multi-book order delivered
                 12 days ago (inside window); 418355 shipped; 417702 delivered
                 47 days ago (outside window)
  James Okafor   single shipped order (happy path)
  Daniel Reyes   single order delivered 52 days ago (outside window)
  Sofia Alvarez  processing order (offer cancel); she calls from an unknown phone
  Robert Kim     lost order + repeat caller (recent_contacts=2) -> escalate
  Priya Patel    order delivered exactly 30 days ago (last day of the window)
  +15125550199   unknown phone number (not in DB)
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from bookly.db import DEFAULT_DB, connect, init_schema

UNKNOWN_PHONE = "+15125550199"


def d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


CUSTOMERS = [
    # id, name, phone, email, zip, recent_contacts
    (1, "Maya Chen", "+14155550101", "maya.chen@example.com", "94110", 0),
    (2, "James Okafor", "+13125550142", "james.okafor@example.com", "60614", 0),
    (3, "Daniel Reyes", "+12065550177", "daniel.reyes@example.com", "98103", 0),
    (4, "Sofia Alvarez", "+17185550123", "sofia.alvarez@example.com", "11215", 0),
    (5, "Robert Kim", "+16175550188", "robert.kim@example.com", "02139", 2),
    (6, "Priya Patel", "+17735550144", "priya.patel@example.com", "60622", 0),
]

ORDERS = [
    # order_number, customer_id, status, placed, shipped, delivered, eta, carrier, tracking, ship_zip
    ("418027", 1, "delivered", d(18), d(15), d(12), None, "UPS", "1Z999AA10123456784", "94110"),
    ("418355", 1, "shipped", d(4), d(2), None, d(-3), "UPS", "1Z999AA10198765432", "94110"),
    ("417702", 1, "delivered", d(53), d(50), d(47), None, "USPS", "9400111899223344556677", "94110"),
    ("419120", 2, "shipped", d(3), d(1), None, d(-2), "USPS", "9400111899220011223344", "60614"),
    ("416881", 3, "delivered", d(58), d(55), d(52), None, "UPS", "1Z999AA10155544433", "98103"),
    ("420044", 4, "processing", d(1), None, None, d(-6), None, None, "11215"),
    ("415930", 5, "lost", d(24), d(21), None, d(13), "USPS", "9400111899227788990011", "02139"),
    ("417950", 6, "delivered", d(36), d(33), d(30), None, "UPS", "1Z999AA10166677788", "60622"),
]

ITEMS = [
    # order_number, title, author, format, price_cents
    ("418027", "Klara and the Sun", "Kazuo Ishiguro", "paperback", 1499),
    ("418027", "Tomorrow, and Tomorrow, and Tomorrow", "Gabrielle Zevin", "hardcover", 2799),
    ("418355", "The Overstory", "Richard Powers", "paperback", 1899),
    ("417702", "Educated", "Tara Westover", "paperback", 1800),
    ("419120", "Project Hail Mary", "Andy Weir", "hardcover", 2899),
    ("416881", "The Name of the Wind", "Patrick Rothfuss", "paperback", 1999),
    ("420044", "Lessons in Chemistry", "Bonnie Garmus", "hardcover", 2999),
    ("415930", "The Covenant of Water", "Abraham Verghese", "hardcover", 3200),
    ("417950", "The Midnight Library", "Matt Haig", "paperback", 1699),
]


def seed(path: Path | str, demo_phone: str | None = None) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = connect(path)
    init_schema(conn)
    conn.executemany(
        "INSERT INTO customers (id,name,phone,email,zip,recent_contacts) VALUES (?,?,?,?,?,?)",
        CUSTOMERS,
    )
    if demo_phone:
        # Live demo: calls from this number reach Maya Chen's account (3 orders, one with 2 books).
        # Local database only; the number is never written to the repo.
        conn.execute("UPDATE customers SET phone = ? WHERE id = 1", (demo_phone,))
    conn.executemany(
        "INSERT INTO orders (order_number,customer_id,status,placed_at,shipped_at,delivered_at,eta,carrier,tracking_number,ship_zip)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        ORDERS,
    )
    conn.executemany(
        "INSERT INTO order_items (order_number,title,author,format,price_cents) VALUES (?,?,?,?,?)",
        ITEMS,
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--demo-phone", help="Your cell in E.164 (+1...): calls from it reach Maya Chen's account")
    args = ap.parse_args()
    seed(args.db, demo_phone=args.demo_phone)
    print(f"Seeded {args.db}" + (" (demo phone mapped to Maya Chen)" if args.demo_phone else ""))
