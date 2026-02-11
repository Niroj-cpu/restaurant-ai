from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

# Load menu data safely
with open("menu.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    menu = data["menu"]


def normalize(text):
    """Lowercase and split text into words"""
    return set(text.lower().replace("-", " ").split())


def search_menu(query):
    query_words = normalize(query)
    results = []

    for item in menu:
        score = 0

        name_words = normalize(item["name"])
        keyword_words = set()

        for kw in item.get("keywords", []):
            keyword_words |= normalize(kw)

        # Exact word matches
        name_matches = query_words & name_words
        keyword_matches = query_words & keyword_words

        # Strongly prioritize name matches
        score += len(name_matches) * 5
        score += len(keyword_matches) * 2

        if score > 0:
            results.append((score, item))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)

    return [item for _, item in results[:3]]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("question", "").strip()

    if not user_input:
        return jsonify({"answer": "Please ask about a menu item."})

    matches = search_menu(user_input)

    if not matches:
        return jsonify({
            "answer": "Sorry, I couldn’t find anything matching that."
        })

    response_lines = []
    for item in matches:
        response_lines.append(
            f"{item['name']} — ${item['price']}"
        )

    return jsonify({
        "answer": "\n".join(response_lines)
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
