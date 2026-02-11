from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Load menu data
with open("menu.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    menu = data["menu"]

# 🔎 Exact-match search — no AI, fully deterministic
def search_menu(query):
    query = query.lower().strip()

    for item in menu:
        name = item["name"].lower()
        keywords = [k.lower() for k in item.get("keywords", [])]

        # Exact match with the menu item name
        if query == name:
            return [item]

        # Exact match with any keyword
        if query in keywords:
            return [item]

    # No matches found
    return []

# 🏠 Home route
@app.route("/")
def home():
    return render_template("index.html")

# ❓ Ask route
@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("question", "")
    matches = search_menu(user_input)

    if not matches:
        return jsonify({"answer": "Sorry, I couldn’t find anything matching that exactly."})

    item = matches[0]

    response = (
        f"{item['name']} — ${item['price']}\n"
        f"Category: {item['category']}\n"
        f"{item['description']}"
    )

    return jsonify({"answer": response})

# 🚀 Main entry point with port handling
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets this automatically
    app.run(host="0.0.0.0", port=port)       # debug=False for production
