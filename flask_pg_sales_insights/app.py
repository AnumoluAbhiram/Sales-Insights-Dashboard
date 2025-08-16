from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import text

# ------------------------------------------------------
# Flask App Setup
# ------------------------------------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ------------------------------------------------------
# Database Config (PostgreSQL)
# ------------------------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:1234@localhost:5432/sales_insights"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------------------------------------------
# User Model
# ------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ------------------------------------------------------
# Routes
# ------------------------------------------------------
@app.route("/", endpoint="index")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("user_dashboard"))

# ----------------------- Login -----------------------
@app.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash("✅ Logged in successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("❌ Invalid credentials!", "danger")
    return render_template("login.html")

# ----------------------- Logout -----------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Logged out successfully!", "info")
    return redirect(url_for("login"))

# ----------------------- Register -----------------------
@app.route("/register", methods=["GET", "POST"], endpoint="register")
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("⚠️ Username or Email already exists!", "danger")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# ----------------------- Admin Dashboard -----------------------
@app.route("/admin_dashboard", endpoint="admin_dashboard")
def admin_dashboard():
    if "user_id" not in session or not session.get("is_admin"):
        flash("⚠️ Admin access required!", "danger")
        return redirect(url_for("login"))

    total_users = User.query.count()
    total_admins = User.query.filter_by(is_admin=True).count()
    total_normal_users = User.query.filter_by(is_admin=False).count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_admins=total_admins,
        total_normal_users=total_normal_users,
        recent_users=recent_users,
    )

# ----------------------- User Dashboard -----------------------
@app.route("/user_dashboard", endpoint="user_dashboard")
def user_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    date_filter = ""
    params = {}
    if start_date and end_date:
        date_filter = "WHERE o.order_date BETWEEN :start_date AND :end_date"
        params = {"start_date": start_date, "end_date": end_date}

    # -----------------------
    # KPI Cards
    # -----------------------
    total_customers = db.session.execute(text("SELECT COUNT(*) FROM customers")).scalar()
    total_orders = db.session.execute(text(f"SELECT COUNT(*) FROM orders o {date_filter}"), params).scalar()
    total_revenue = db.session.execute(text(f"""
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price),0)
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        {date_filter}
    """), params).scalar()

    # -----------------------
    # Monthly Revenue
    # -----------------------
    monthly_revenue = db.session.execute(text(f"""
        SELECT to_char(date_trunc('month', o.order_date),'YYYY-MM') AS month,
               COALESCE(SUM(oi.quantity * oi.unit_price),0) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        {date_filter}
        GROUP BY 1 ORDER BY 1
    """), params).fetchall()

    # -----------------------
    # Top Customers
    # -----------------------
    top_customers = db.session.execute(text(f"""
        SELECT c.name AS customer_name, SUM(oi.quantity*oi.unit_price) AS revenue,
               RANK() OVER(ORDER BY SUM(oi.quantity*oi.unit_price) DESC) AS rnk
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        JOIN order_items oi ON oi.order_id = o.id
        {date_filter}
        GROUP BY c.id ORDER BY revenue DESC LIMIT 5
    """), params).fetchall()

    # -----------------------
    # Top Products
    # -----------------------
    top_products = db.session.execute(text(f"""
        SELECT p.name, SUM(oi.quantity) AS qty
        FROM products p
        JOIN order_items oi ON oi.product_id = p.id
        JOIN orders o ON o.id = oi.order_id
        {date_filter}
        GROUP BY p.id ORDER BY qty DESC LIMIT 5
    """), params).fetchall()

    # -----------------------
    # Top Categories
    # -----------------------
    top_categories = db.session.execute(text("""
        SELECT p.category AS category_name, SUM(oi.quantity * oi.unit_price) AS revenue
        FROM products p
        JOIN order_items oi ON oi.product_id = p.id
        JOIN orders o ON o.id = oi.order_id
        GROUP BY p.category
        ORDER BY revenue DESC
        LIMIT 5
    """)).fetchall()

    # -----------------------
    # Order Status Counts
    # -----------------------
    if start_date and end_date:
        order_status_counts = db.session.execute(text("""
            SELECT status, COUNT(*) AS count
            FROM orders o
            WHERE o.order_date BETWEEN :start_date AND :end_date
            GROUP BY status
        """), params).fetchall()
    else:
        order_status_counts = db.session.execute(text("""
            SELECT status, COUNT(*) AS count
            FROM orders o
            GROUP BY status
        """)).fetchall()

    # -----------------------
    # Inactive Customers (30+ days no orders)
    # -----------------------
    inactive_customers = db.session.execute(text("""
        SELECT c.name AS customer_name, MAX(o.order_date) AS last_order
        FROM customers c
        LEFT JOIN orders o ON o.customer_id = c.id
        GROUP BY c.id
        HAVING COALESCE(MAX(o.order_date), '1900-01-01') <= :inactive_date
        ORDER BY last_order ASC
    """), {"inactive_date": datetime.utcnow() - timedelta(days=30)}).fetchall()

    return render_template(
        "user_dashboard.html",
        user=user,
        total_customers=total_customers,
        total_orders=total_orders,
        total_revenue=total_revenue,
        monthly_revenue=monthly_revenue,
        top_customers=top_customers,
        top_products=top_products,
        top_categories=top_categories,
        order_status_counts=order_status_counts,
        inactive_customers=inactive_customers,
        start_date=start_date,
        end_date=end_date
    )

# ----------------------- CRUD: Users -----------------------
@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if "user_id" not in session or not session.get("is_admin"):
        flash("⚠️ Admin access required!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        is_admin = "is_admin" in request.form

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("⚠️ User already exists!", "danger")
            return redirect(url_for("add_user"))

        new_user = User(username=username, email=email, is_admin=is_admin)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("✅ User added successfully!", "success")
        return redirect(url_for("users"))

    return render_template("add_user.html")

@app.route("/users")
def users():
    if "user_id" not in session or not session.get("is_admin"):
        flash("⚠️ Admin access required!", "danger")
        return redirect(url_for("login"))
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users.html", users=all_users)

@app.route("/profile/<int:id>")
def profile(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get_or_404(id)
    return render_template("profile.html", user=user)

@app.route("/update_user/<int:id>", methods=["GET", "POST"])
def update_user(id):
    if "user_id" not in session or not session.get("is_admin"):
        flash("⚠️ Admin access required!", "danger")
        return redirect(url_for("login"))
    user = User.query.get_or_404(id)
    if request.method == "POST":
        user.username = request.form["username"]
        user.email = request.form["email"]
        if request.form["password"]:
            user.set_password(request.form["password"])
        user.is_admin = "is_admin" in request.form
        db.session.commit()
        flash("✅ User updated successfully!", "success")
        return redirect(url_for("users"))
    return render_template("update_user.html", user=user)

@app.route("/delete_user/<int:id>")
def delete_user(id):
    if "user_id" not in session or not session.get("is_admin"):
        flash("⚠️ Admin access required!", "danger")
        return redirect(url_for("login"))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash("🗑️ User deleted successfully!", "info")
    return redirect(url_for("users"))

# ------------------------------------------------------
# Inject Current Time
# ------------------------------------------------------
@app.context_processor
def inject_now():
    return {"now": datetime.now()}

# ------------------------------------------------------
# Run Server
# ------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Ensure default admin exists
        admin = User.query.filter_by(email="admin@sales.com").first()
        if not admin:
            admin = User(username="admin", email="admin@sales.com", is_admin=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
