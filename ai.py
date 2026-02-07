from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

# Load menu data
with open("menu.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    menu = data["menu"]


def search_menu(query):
    query = query.lower()
    results = []

    for item in menu:
        score = 0

        if item["name"].lower() in query:
            score += 3

        for keyword in item["keywords"]:
            if keyword.lower() in query:
                score += 1

        if score > 0:
            results.append((score, item))

    results.sort(reverse=True, key=lambda x: x[0])
    return [item for _, item in results[:3]]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("question", "")
    matches = search_menu(user_input)

    if not matches:
        return jsonify({"answer": "Sorry, I couldn’t find anything matching that."})

    response = []
    for item in matches:
        response.append(
            f"{item['name']} — ${item['price']}"
        )

    return jsonify({"answer": "\n".join(response)})


if __name__ == "__main__":
    app.run(debug=True)
