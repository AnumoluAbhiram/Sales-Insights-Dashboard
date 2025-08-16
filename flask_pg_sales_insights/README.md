# Sales Insights (Flask + PostgreSQL)

A tiny, job-ready project to **showcase SQL skills** in 2 hours. It demonstrates:
- Relational schema design (customers, products, orders, order_items)
- Indexes, a trigger, a view, and a window-function ranking **function**
- Parameterized queries from Flask using **psycopg2**
- A clean Bootstrap UI with a small **Chart.js** bar chart

## 1) Prereqs
- Python 3.10+
- PostgreSQL 14+ (with `psql` in PATH)
- VS Code + **Python** extension

## 2) Open in VS Code
1. Download and unzip this project.
2. In VS Code: **File → Open Folder…** → choose the folder.
3. Open an integrated terminal: **Terminal → New Terminal**.

## 3) Create virtual environment
```bash
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

## 4) Install dependencies
```bash
pip install -r requirements.txt
```

## 5) Create a PostgreSQL database
```bash
# Log in to Postgres (adjust -U user if needed)
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE sales_insights;"
# Load schema + sample data
psql -U postgres -h localhost -d sales_insights -f sql/db.sql
```

> If `psql` asks for a password, enter your Postgres user's password.  
> If you use pgAdmin, create DB `sales_insights`, then run everything inside `sql/db.sql` in a Query Tool.

## 6) Configure environment
Copy `.env.example` to `.env` and update credentials if needed:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sales_insights
```

## 7) Run the app
**Option A (simple):**
```bash
python app.py
```
**Option B (debug in VS Code):**
- Press **Run and Debug** (▶️ on sidebar) → pick **Flask: Run app.py**.

Then open: http://127.0.0.1:5000/

## 8) What to demo in an interview
- Show **schema** (`sql/db.sql`): foreign keys, indexes, `CHECK` constraints.
- Show **trigger** (`set_updated_at`) that maintains `orders.updated_at`.
- Show **view** `monthly_revenue` used by the dashboard.
- Show **function** `customer_revenue_rank()` using a **window function**.
- Explain **parameterized queries** in `app.py` (search on /customers).
- Talk about performance: why indexes exist and how you'd add EXPLAIN ANALYZE.

## 9) Quick tasks you can add (bonus points)
- A page to filter orders by date range (use `BETWEEN` and aggregates).
- A materialized view for faster dashboards and a refresh endpoint.
- Pagination using `OFFSET/LIMIT` for customers.

---

**Made for rapid showcasing—good luck!**
