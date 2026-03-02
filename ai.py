from flask import Flask, render_template, request, jsonify
import json
import os
import re

app = Flask(__name__)

with open("menu.json", "r", encoding="utf-8") as f:
    menu = json.load(f)["menu"]

# =========================
# NORMALIZATION RULES
# =========================

STOP_WORDS = {
    "with", "and", "or", "the", "a", "an", "pcs", "pc",
    "pieces", "piece", "plate", "order", "please"
}

SYNONYMS = {
    "veg": "vegetable",
    "veggie": "vegetable",
    "vegan": "vegetable",
    "chkn": "chicken",
    "fried": "fried",
    "grilled": "grill",
}

CATEGORY_WORDS = {
    "momo", "burger", "salad", "pasta", "noodle", "soup"
}

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    words = text.split()

    normalized = []
    for w in words:
        if w in STOP_WORDS:
            continue
        w = SYNONYMS.get(w, w)
        if w.endswith("s"):
            w = w[:-1]  # singularize
        normalized.append(w)

    return normalized


# =========================
# CORE SEARCH ENGINE
# =========================

def search_menu(query):
    query_words = set(normalize(query))
    results = []

    # Detect category intent (burger vs momo etc.)
    query_categories = query_words & CATEGORY_WORDS

    for item in menu:
        name_words = set(normalize(item["name"]))

        keyword_words = set()
        for kw in item.get("keywords", []):
            keyword_words.update(normalize(kw))

        item_words = name_words | keyword_words

        # 🚨 HARD CATEGORY FILTER
        if query_categories:
            if not (query_categories & name_words):
                continue  # reject completely

        # 🚨 INTENT COVERAGE RULE
        matched = query_words & item_words
        coverage = len(matched) / len(query_words)

        # Must satisfy at least 70% of intent
        if coverage < 0.7:
            continue

        score = (
            len(matched) * 10 +
            len(query_categories & name_words) * 20
        )

        results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:3]]


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please ask about a menu item."})

    matches = search_menu(question)

    if not matches:
        return jsonify({
            "answer": "Sorry, I couldn’t find anything matching that."
        })

    return jsonify({
        "answer": "\n".join(
            f"{item['name']} — ${item['price']}"
            for item in matches
        )
    })


# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
