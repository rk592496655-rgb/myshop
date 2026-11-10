import requests
import sqlite3
import time
import os

TOKEN = os.getenv("BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}/"
keyboard = {
    "keyboard": [
        ["🛒 Shop Now", "👤 Profile"],
        ["💰 Add Balance", "🔑 My Keys"],
        ["📖 How to Use", "📥 Download Files"],
        ["🎁 Daily Gift", "🤝 Refer to Earn"],
        ["🎧 Support", "🧾 Payment Proof"],
        ["👑 Reseller Upgrade"]
    ],
    "resize_keyboard": True
}

def send_message(chat_id, text, markup=None)
    data = {"chat_id": chat_id, "text": text}
    if markup:
        data["reply_markup"] = __import__("json").dumps(markup)
    requests.post(API + "sendMessage", data=data, timeout=20)

def get_products():
    con = sqlite3.connect("shop.db")
    con.row_factory = sqlite3.Row
    products = con.execute("SELECT * FROM products").fetchall()
    con.close()
    return products

offset = 0

while True:
    try:
        data = requests.get(
            API + "getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35
        ).json()

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            command = message.get("text", "")

            if not chat_id:
                continue

            if command == "/start":
                send_message(chat_id, "Welcome to MY SHOP 🛍️\nPlease select a menu:", keyboard)

            elif command in ["🛒 Shop Now", "/products"]:
                products = get_products()
                if not products:
                    send_message(chat_id, "No products available right now.", keyboard)
                else:
                    text = "🛍️ MY SHOP PRODUCTS\n\n"
                    for p in products:
                        text += f"📦 {p['name']}\n💰 Price: ₹{p['price']}\n📊 Stock: {p['stock']}\n\n"
                    send_message(chat_id, text, keyboard)

            elif command == "👤 Profile":
                send_message(chat_id, "👤 YOUR PROFILE\nYour Telegram account is connected.", keyboard)

            elif command == "💰 Add Balance":
                send_message(chat_id, "💰 ADD BALANCE\nPlease contact Support for balance addition.", keyboard)

            elif command == "🔑 My Keys":
                send_message(chat_id, "🔑 MY KEYS\nYour purchased keys will appear here.", keyboard)

            elif command == "📖 How to Use":
                send_message(chat_id, "📖 HOW TO USE\nSelect Shop Now to view available products.", keyboard)

            elif command == "📥 Download Files":
                send_message(chat_id, "📥 DOWNLOAD FILES\nYour available downloads will appear here.", keyboard)

            elif command == "🎁 Daily Gift":
                send_message(chat_id, "🎁 DAILY GIFT\nDaily gift feature is coming soon.", keyboard)

            elif command == "🤝 Refer to Earn":
                send_message(chat_id, "🤝 REFER TO EARN\nReferral feature is coming soon.", keyboard)

            elif command == "🎧 Support":
                send_message(chat_id, "🎧 SUPPORT\nPlease contact the shop administrator.", keyboard)

            elif command == "🧾 Payment Proof":
                send_message(chat_id, "🧾 PAYMENT PROOF\nPlease send your payment screenshot to Support.", keyboard)

            elif command == "👑 Reseller Upgrade":
                send_message(chat_id, "👑 RESELLER UPGRADE\nContact Support for reseller upgrade.", keyboard)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)
