from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Load menu data
with open("menu.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    menu = data["menu"]


# 🔎 Intelligent deterministic search (NO AI)
def search_menu(query):
    query = query.lower().strip()
    query_words = set(query.split())
    best_match = None
    best_score = 0

    for item in menu:
        score = 0
        name = item["name"].lower()
        category = item.get("category", "").lower()
        keywords = [k.lower() for k in item.get("keywords", [])]
        ingredients = [i.lower() for i in item.get("ingredients", [])]

        # 1️⃣ Exact full name match (highest priority)
        if query == name:
            return [item]

        # 2️⃣ Name contains full query
        if query in name:
            score += 10

        # 3️⃣ All query words appear in name
        if all(word in name for word in query_words):
            score += 8

        # 4️⃣ Keyword matching
        for keyword in keywords:
            if keyword in query:
                score += 5

        # 5️⃣ Category match
        if category and category in query:
            score += 3

        # 6️⃣ Ingredient match
        for word in query_words:
            if word in ingredients:
                score += 2

        # Keep best scoring item
        if score > best_score:
            best_score = score
            best_match = item

    if best_match:
        return [best_match]

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
        return jsonify({"answer": "Sorry, I couldn’t find anything matching that."})

    item = matches[0]

    response = (
        f"{item['name']} — ${item['price']}\n"
        f"Category: {item['category']}\n"
        f"{item['description']}"
    )

    return jsonify({"answer": response})

# Main entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets this automatically
    app.run(host="0.0.0.0", port=port)       # debug=False for production

