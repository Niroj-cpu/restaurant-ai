from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

with open("menu.json", "r", encoding="utf-8") as f:
    menu = json.load(f)["menu"]

# Words that should NOT be required
STOP_WORDS = {
    "with", "and", "or", "the", "a", "an",
    "pcs", "piece", "pieces", "plate"
}


def normalize(text):
    return text.lower().replace("-", " ").split()


def search_menu(query):
    query_words = set(normalize(query)) - STOP_WORDS
    results = []

    for item in menu:
        name_words = set(normalize(item["name"]))

        keyword_words = set()
        for kw in item.get("keywords", []):
            keyword_words.update(normalize(kw))

        all_item_words = name_words | keyword_words

        # ❗ HARD FILTER:
        # At least ONE important query word MUST be in the NAME
        core_match = query_words & name_words
        if not core_match:
            continue  # instantly reject (this fixes chicken burger → momo)

        # Scoring (only after passing filter)
        score = 0
        score += len(core_match) * 10
        score += len(query_words & keyword_words) * 3

        results.append((score, item))

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

    return jsonify({
        "answer": "\n".join(
            f"{item['name']} — ${item['price']}" for item in matches
        )
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
