from flask import Flask, render_template, request, jsonify
import json
import os
import re

app = Flask(__name__)

with open("menu.json", "r", encoding="utf-8") as f:
    menu = json.load(f)["menu"]

STOP_WORDS = {
    "with", "and", "or", "the", "a", "an",
    "pcs", "pc", "piece", "pieces", "order", "please"
}

FOOD_NOUNS = {
    "burger", "momo", "salad", "pasta", "noodle",
    "soup", "wrap", "rice", "bowl"
}

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    words = text.split()
    return [w for w in words if w not in STOP_WORDS]

def extract_primary_noun(words):
    """Return the last food noun mentioned"""
    for w in reversed(words):
        if w in FOOD_NOUNS:
            return w
    return None

def search_menu(query):
    query_words = normalize(query)
    primary_noun = extract_primary_noun(query_words)

    results = []

    for item in menu:
        name_words = normalize(item["name"])

        # 🚨 HARD LOCK: primary noun MUST be in name
        if primary_noun and primary_noun not in name_words:
            continue

        keyword_words = []
        for kw in item.get("keywords", []):
            keyword_words.extend(normalize(kw))

        all_words = set(name_words + keyword_words)

        matched = set(query_words) & all_words
        coverage = len(matched) / len(query_words)

        if coverage < 0.6:
            continue

        score = (
            coverage * 100 +
            (10 if primary_noun in name_words else 0)
        )

        results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in results[:3]]

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
        return jsonify({"answer": "Sorry, I couldn’t find anything matching that."})

    return jsonify({
        "answer": "\n".join(
            f"{item['name']} — ${item['price']}"
            for item in matches
        )
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
