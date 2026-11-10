from flask import Flask, request, redirect, session, jsonify
import sqlite3
import os
from functools import wraps
from html import escape

app = Flask(__name__)

app.secret_key = os.getenv("APP_SECRET", "temporary-secret")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

CATEGORIES = [
    "Non Root",
    "Root - Device",
    "iOS - iPhone",
    "PC - Computer",
    "Guild - Glory Bot"
]

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
    # MY SHOP TELEGRAM WEBHOOK

import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/"


SHOP_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "🛒 Shop Now", "callback_data": "shop"},
            {"text": "👤 Profile", "callback_data": "profile"}
        ],
        [
            {"text": "💰 Add Balance", "callback_data": "balance"},
            {"text": "🔑 My Keys", "callback_data": "keys"}
        ],
        [
            {"text": "📖 How to Use", "callback_data": "how"},
            {"text": "📥 Download Files", "callback_data": "downloads"}
        ],
        [
            {"text": "🎁 Daily Gift", "callback_data": "gift"},
            {"text": "🤝 Refer to Earn", "callback_data": "refer"}
        ],
        [
            {"text": "🎧 Support", "callback_data": "support"},
            {"text": "🧾 Payment Proof", "callback_data": "proof"}
        ],
        [
            {"text": "👑 Reseller Upgrade", "callback_data": "reseller"}
        ]
    ]
}


def telegram_send(chat_id, message, markup=None):
    payload = {"chat_id": chat_id, "text": message}
    if markup:
        payload["reply_markup"] = markup
    requests.post(TELEGRAM_API + "sendMessage", json=payload, timeout=15)



def telegram_menu_action(chat_id, action, user=None):

    # SHOP NOW - SHOW CATEGORIES
    if action == "shop":
        keyboard = {
            "inline_keyboard": [
                [{"text": "Non Root", "callback_data": "cat_0"}],
                [{"text": "Root - Device", "callback_data": "cat_1"}],
                [{"text": "iOS - iPhone", "callback_data": "cat_2"}],
                [{"text": "PC - Computer", "callback_data": "cat_3"}],
                [{"text": "Guild - Glory Bot", "callback_data": "cat_4"}]
            ]
        }
        telegram_send(chat_id, "🛍️ MY SHOP\n\nSelect a category:", keyboard)

    # CATEGORY PRODUCTS
    elif action.startswith("cat_"):
        try:
            index = int(action.split("_")[1])
            category = CATEGORIES[index]
        except (ValueError, IndexError):
            telegram_send(chat_id, "Invalid category.")
            return

        with db() as con:
            products = con.execute(
                "SELECT id, name, stock FROM products WHERE category=? ORDER BY id DESC",
                (category,)
            ).fetchall()

        keyboard = {"inline_keyboard": []}

        for p in products:
            keyboard["inline_keyboard"].append([
                {
                    "text": f"📦 {p['name']} | Stock: {p['stock']}",
                    "callback_data": f"product_{p['id']}"
                }
            ])

        keyboard["inline_keyboard"].append([
            {"text": "⬅️ Back to Categories", "callback_data": "shop"}
        ])

        telegram_send(
            chat_id,
            f"📂 {category}\n\nSelect a product:",
            keyboard
        )

    # PRODUCT DETAILS AND PLANS
    elif action.startswith("product_"):
        try:
            product_id = int(action.split("_")[1])
        except ValueError:
            return

        with db() as con:
            product = con.execute(
                "SELECT * FROM products WHERE id=?",
                (product_id,)
            ).fetchone()

            plans = con.execute(
                "SELECT * FROM plans WHERE product_id=? ORDER BY id ASC",
                (product_id,)
            ).fetchall()

        if not product:
            telegram_send(chat_id, "Product not found.")
            return

        keyboard = {"inline_keyboard": []}

        for p in plans:
            status = "Out of stock" if p["stock"] <= 0 else f"${p['price_usd']}"
            keyboard["inline_keyboard"].append([
                {
                    "text": f"{p['name']} - {status}",
                    "callback_data": f"plan_{p['id']}"
                }
            ])

        keyboard["inline_keyboard"].append([
            {"text": "📁 Files & Setup", "callback_data": f"files_{product_id}"}
        ])

        try:
            category_index = CATEGORIES.index(product["category"])
        except (ValueError, TypeError):
            category_index = 0

        keyboard["inline_keyboard"].append([
            {
                "text": "⬅️ All Products",
                "callback_data": f"cat_{category_index}"
            }
        ])

        telegram_send(
            chat_id,
            f"📦 {product['name']}\n\nSelect your plan:",
            keyboard
        )

    # PLAN CHECKOUT
    elif action.startswith("plan_"):
        try:
            plan_id = int(action.split("_")[1])
        except ValueError:
            return

        with db() as con:
            plan = con.execute(
                "SELECT * FROM plans WHERE id=?",
                (plan_id,)
            ).fetchone()

            if plan:
                product = con.execute(
                    "SELECT * FROM products WHERE id=?",
                    (plan["product_id"],)
                ).fetchone()
            else:
                product = None

        if not plan or not product:
            telegram_send(chat_id, "Plan not found.")
            return

        if plan["stock"] <= 0:
            telegram_send(chat_id, "❌ This plan is out of stock.")
            return

        keyboard = {
            "inline_keyboard": [
                [{"text": f"UPI India - ₹{plan['price_inr']}", "callback_data": f"pay_upi_{plan_id}"}],
                [{"text": f"Bangladesh Pay - ৳{plan['price_inr']}", "callback_data": f"pay_bd_{plan_id}"}],
                [{"text": f"Binance Pay - {plan['price_usd']} USDT", "callback_data": f"pay_binance_{plan_id}"}],
                [{"text": "💰 Pay with Balance", "callback_data": f"pay_balance_{plan_id}"}],
                [{"text": "🎟️ Apply Coupon Code", "callback_data": f"coupon_{plan_id}"}],
                [{"text": "⬅️ All Plans", "callback_data": f"product_{product['id']}"}]
            ]
        }

        telegram_send(
            chat_id,
            f"🧾 CHECKOUT SUMMARY\n\n"
            f"Product: {product['name']}\n"
            f"Plan: {plan['name']}\n"
            f"Quantity: 1\n"
            f"Unit Price: ${plan['price_usd']} USDT\n"
            f"Final Total: ${plan['price_usd']} USDT\n\n"
            f"📦 Available Stock: {plan['stock']}\n\n"
            f"Choose payment method:",
            keyboard
        )

    # PAYMENT PLACEHOLDER
    elif action.startswith("pay_"):
        telegram_send(
            chat_id,
            "💳 Payment option selected.\n\nPayment verification is not configured yet. Please contact Support."
        )

    # FILES AND SETUP
    elif action.startswith("files_"):
        telegram_send(
            chat_id,
            "📁 Files & Setup\n\nPlease contact Support for available files and setup instructions."
        )

    # COUPON
    elif action.startswith("coupon_"):
        telegram_send(
            chat_id,
            "🎟️ Coupon system is coming soon."
        )

    # MAIN MENU
    elif action == "main_menu":
        telegram_send(
            chat_id,
            "🏠 MY SHOP\n\nPlease select a menu:",
            SHOP_KEYBOARD
        )

    # PROFILE
    elif action == "profile":
        name = user.get("first_name", "User") if user else "User"
        username = user.get("username", "Not set") if user else "Not set"
        telegram_send(
            chat_id,
            f"👤 YOUR PROFILE\nName: {name}\nUsername: @{username}"
        )

    elif action == "balance":
        telegram_send(chat_id, "💰 ADD BALANCE\nPlease contact Support for balance addition.")

    elif action == "keys":
        telegram_send(chat_id, "🔑 MY KEYS\nYour purchased keys will appear here.")

    elif action == "how":
        telegram_send(chat_id, "📖 HOW TO USE\nSelect Shop Now to view available products.")

    elif action == "downloads":
        telegram_send(chat_id, "📥 DOWNLOAD FILES\nYour available downloads will appear here.")

    elif action == "gift":
        telegram_send(chat_id, "🎁 DAILY GIFT\nDaily gift feature is coming soon.")

    elif action == "refer":
        telegram_send(chat_id, "🤝 REFER TO EARN\nReferral feature is coming soon.")

    elif action == "support":
        telegram_send(chat_id, "🎧 SUPPORT\nPlease contact the shop administrator.")

    elif action == "proof":
        telegram_send(chat_id, "🧾 PAYMENT PROOF\nPlease send your payment screenshot to Support.")

    elif action == "reseller":
        telegram_send(chat_id, "👑 RESELLER UPGRADE\nContact Support for reseller upgrade.")
        


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if not BOT_TOKEN or not WEBHOOK_SECRET:
        return jsonify({"ok": False}), 500

    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}

    callback = update.get("callback_query")
    if callback:
        requests.post(
            TELEGRAM_API + "answerCallbackQuery",
            json={"callback_query_id": callback["id"]},
            timeout=15
        )
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        if chat_id:
            telegram_menu_action(chat_id, callback.get("data", ""), callback.get("from", {}))
        return jsonify({"ok": True})

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    command = message.get("text", "")

    if chat_id and command == "/start":
        telegram_send(
            chat_id,
            "Welcome to MY SHOP 🛍️\nPlease select a menu:",
            SHOP_KEYBOARD
        )
    elif chat_id and command == "/products":
        telegram_menu_action(chat_id, "shop")

    return jsonify({"ok": True})
