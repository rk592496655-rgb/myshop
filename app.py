from flask import Flask, request, redirect, session, jsonify
import sqlite3
import os
from functools import wraps
from html import escape

app = Flask(__name__)

app.secret_key = os.getenv("APP_SECRET", "temporary-secret")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

CATEGORIES = ["Android Non Root", "Android Root", "Iphone Panel"]

def db():
    con = sqlite3.connect("shop.db")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        stock INTEGER
    )
    """)
    columns = [r["name"] for r in con.execute(
        "PRAGMA table_info(products)"
    ).fetchall()]
    if "category" not in columns:
        con.execute(
            "ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'Android Non Root'"
        )

    con.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price_inr REAL NOT NULL DEFAULT 0,
        price_usd REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/")
        return "Wrong password"
    return """
    <html><meta name="viewport" content="width=device-width, initial-scale=1">
    <body style="background:#101827;color:white;font-family:Arial;padding:25px">
    <h2>My Shop Admin Login</h2>
    <form method="post">
    <input name="password" type="password" placeholder="Admin Password" required>
    <button>Login</button></form></body></html>
    """

@app.route("/")
@login_required
def home():
    with db() as con:
        products = con.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()

        plans = con.execute("""
            SELECT plans.*, products.name AS product_name
            FROM plans JOIN products ON products.id=plans.product_id
            ORDER BY plans.id DESC
        """).fetchall()

    options = "".join(
        f'<option value="{c}">{c}</option>' for c in CATEGORIES
    )

    product_rows = ""
    for p in products:
        product_rows += f"""
        <tr>
        <td>{escape(str(p['name'] or ''))}</td>
        <td>{escape(str(p['category'] or ''))}</td>
        <td>
        <form action="/delete_product/{p['id']}" method="post">
        <button>Delete Product</button></form>
        </td></tr>
        """

    plan_rows = ""
    for p in plans:
        plan_rows += f"""
        <tr>
        <td>{escape(str(p['product_name']))}</td>
        <td>{escape(str(p['name']))}</td>
        <td>₹{p['price_inr']:.2f}</td>
        <td>${p['price_usd']:.2f}</td>
        <td>{p['stock']}</td>
        <td>
        <form action="/delete_plan/{p['id']}" method="post">
        <button>Delete Plan</button></form>
        </td></tr>
        """

    product_options = "".join(
        f'<option value="{p["id"]}">{escape(str(p["name"]))}</option>'
        for p in products
    )

    return f"""
    <html>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <body style="background:#101827;color:white;font-family:Arial;padding:18px">
    <h1>MY SHOP DASHBOARD</h1>
    <hr>
    <h2>Add New Product</h2>
    <form action="/add_product" method="post">
    <input name="name" placeholder="Product Name" required>
    <p>Select Category</p>
    <select name="category">{options}</select>
    <button type="submit">Add Product</button>
    </form>
    <hr>
    <h2>Add Multiple Plans</h2>
    <form action="/add_plan" method="post">
    <p>Select Product</p>
    <select name="product_id" required>{product_options}</select>
    <p>Plan Name</p>
    <input name="name" placeholder="Example: 1 Day / 7 Days" required>
    <p>INR Price (₹)</p>
    <input name="price_inr" type="number" step="0.01" min="0" required>
    <p>USD Price ($)</p>
    <input name="price_usd" type="number" step="0.01" min="0" required>
    <p>Stock Quantity</p>
    <input name="stock" type="number" min="0" required>
    <button type="submit">Add Plan</button>
    </form>
    <hr>
    <h2>My Products</h2>
    <table border="1" cellpadding="7">
    <tr><th>Name</th><th>Category</th><th>Action</th></tr>
    {product_rows}
    </table>
    <hr>
    <h2>All Plans</h2>
    <table border="1" cellpadding="7">
    <tr><th>Product</th><th>Plan</th><th>INR</th>
    <th>USD</th><th>Stock</th><th>Action</th></tr>
    {plan_rows}
    </table>
    </body></html>
    """

@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "")
    if not name or category not in CATEGORIES:
        return "Invalid product details", 400

    with db() as con:
        con.execute(
            "INSERT INTO products(name,price,stock,category) VALUES(?,?,?,?)",
            (name, 0, 0, category)
        )
    return redirect("/")

@app.route("/add_plan", methods=["POST"])
@login_required
def add_plan():
    try:
        product_id = int(request.form["product_id"])
        name = request.form["name"].strip()
        price_inr = float(request.form["price_inr"])
        price_usd = float(request.form["price_usd"])
        stock = int(request.form["stock"])

        if not name or price_inr < 0 or price_usd < 0 or stock < 0:
            return "Invalid plan details", 400

        with db() as con:
            product = con.execute(
                "SELECT id FROM products WHERE id=?", (product_id,)
            ).fetchone()
            if not product:
                return "Product not found", 404

            con.execute("""
                INSERT INTO plans
                (product_id,name,price_inr,price_usd,stock)
                VALUES(?,?,?,?,?)
            """, (product_id, name, price_inr, price_usd, stock))

        return redirect("/")
    except (ValueError, KeyError):
        return "Please enter valid numbers", 400

@app.route("/delete_plan/<int:plan_id>", methods=["POST"])
@login_required
def delete_plan(plan_id):
    with db() as con:
        con.execute("DELETE FROM plans WHERE id=?", (plan_id,))
    return redirect("/")

@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    with db() as con:
        con.execute("DELETE FROM plans WHERE product_id=?", (product_id,))
        con.execute("DELETE FROM products WHERE id=?", (product_id,))
    return redirect("/")

@app.route("/api/products")
@login_required
def api_products():
    with db() as con:
        products = con.execute("""
            SELECT products.*, plans.id AS plan_id,
            plans.name AS plan_name, plans.price_inr,
            plans.price_usd, plans.stock AS plan_stock
            FROM products LEFT JOIN plans
            ON products.id=plans.product_id
            ORDER BY products.id DESC, plans.id
        """).fetchall()
    return jsonify([dict(p) for p in products])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
