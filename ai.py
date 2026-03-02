from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

with open("menu.json", "r", encoding="utf-8") as f:
    menu = json.load(f)["menu"]

STOP_WORDS = ["with", "and", "or", "the", "a", "an", "pcs", "pc", "piece", "pieces", "order", "please"]
FOOD_NOUNS = ["burger", "momo", "salad", "pasta", "noodle", "soup", "wrap", "rice", "bowl"]


def clean_text(text):
    text = text.lower()
    clean = ""
    for char in text:
        if char.isalpha() or char.isdigit() or char == " ":
            clean += char
    words = clean.split()
    result = []
    for word in words:
        if word not in STOP_WORDS:
            result.append(word)
    return result


def find_food_noun(words):
    i = len(words) - 1
    while i >= 0:
        if words[i] in FOOD_NOUNS:
            return words[i]
        i -= 1
    return None


def words_match(query_words, item):
    name_words = clean_text(item["name"])
    keyword_words = []
    for kw in item.get("keywords", []):
        for word in clean_text(kw):
            keyword_words.append(word)

    all_words = name_words + keyword_words

    matched_count = 0
    for word in query_words:
        if word in all_words:
            matched_count += 1

    if len(query_words) == 0:
        return False

    coverage = matched_count / len(query_words)
    return coverage >= 0.6


def noun_in_name(noun, item):
    if noun is None:
        return True
    name_words = clean_text(item["name"])
    return noun in name_words


def search_menu(query):
    query_words = clean_text(query)
    primary_noun = find_food_noun(query_words)

    results = []

    for item in menu:
        if not noun_in_name(primary_noun, item):
            continue

        if not words_match(query_words, item):
            continue

        name_words = clean_text(item["name"])
        score = 0

        for word in query_words:
            all_words = name_words
            for kw in item.get("keywords", []):
                for w in clean_text(kw):
                    all_words.append(w)
            if word in all_words:
                score += 1

        if primary_noun in name_words:
            score += 10

        results.append((score, item))

    # Sort by score (simple bubble sort)
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if results[j][0] > results[i][0]:
                results[i], results[j] = results[j], results[i]

    top_results = []
    for i in range(min(3, len(results))):
        top_results.append(results[i][1])

    return top_results


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
        return jsonify({"answer": "Sorry, I couldn't find anything matching that."})

    answer = ""
    for item in matches:
        if answer != "":
            answer += "\n"
        answer += item["name"] + " — $" + str(item["price"])

    return jsonify({"answer": answer})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
