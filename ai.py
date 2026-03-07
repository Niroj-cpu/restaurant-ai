from flask import Flask, render_template, request, jsonify
import json
import os
import re
from difflib import SequenceMatcher

app = Flask(__name__)

with open("menu.json", "r", encoding="utf-8") as f:
    menu = json.load(f)["menu"]

# =========================
# AI MATCHING HELPERS
# =========================

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def tokenize(text):
    return re.findall(r"[a-z]+", text.lower())

def find_matches(query, menu_items, top_n=3):
    """
    Score every menu item against the user query using:
      1. Keyword overlap        (high weight)
      2. Direct name substring  (high weight)
      3. Fuzzy name similarity  (medium weight)
      4. Category match         (low weight)
      5. Ingredient match       (low weight)
    Returns top_n matches above the confidence threshold.
    """
    query_tokens = tokenize(query)
    query_lower  = query.lower()
    scored = []

    for item in menu_items:
        score = 0.0

        # 1. Keyword overlap
        for kw in item.get("keywords", []):
            for kt in tokenize(kw):
                if any(similarity(kt, qt) > 0.82 for qt in query_tokens):
                    score += 18

        # 2. Direct name substring match
        name_lower = item["name"].lower()
        if name_lower in query_lower:
            score += 55
        else:
            name_tokens = tokenize(item["name"])
            matched = sum(
                1 for nt in name_tokens
                if any(similarity(nt, qt) > 0.82 for qt in query_tokens)
            )
            score += (matched / max(len(name_tokens), 1)) * 45

        # 3. Fuzzy full-name similarity
        score += similarity(query, item["name"]) * 28

        # 4. Category match
        if any(similarity(item.get("category", "").lower(), qt) > 0.82 for qt in query_tokens):
            score += 14

        # 5. Ingredient match
        for ing in item.get("ingredients", []):
            if any(similarity(ing.lower(), qt) > 0.85 for qt in query_tokens):
                score += 7

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for s, it in scored[:top_n] if s >= 18]

def detect_intent(query):
    tokens      = tokenize(query)
    query_lower = query.lower()

    halal_kw = {"halal"}
    veg_kw   = {"vegan", "vegetarian", "veggie"}
    list_kw  = {"menu", "list", "all", "everything", "options", "show", "see", "what"}

    if any(t in tokens for t in halal_kw):
        return "halal"
    if any(t in tokens for t in veg_kw) and any(t in tokens for t in list_kw):
        return "veg_list"
    if any(t in tokens for t in list_kw) and len(tokens) <= 5:
        return "list"
    return "search"

def format_item_text(item):
    halal = " ✅ Halal" if item.get("halal") else ""
    return f"{item['name']} — ${item['price']:.2f}{halal}\n{item['description']}"

def list_menu(filter_fn=None):
    categories = {}
    for item in menu:
        if filter_fn and not filter_fn(item):
            continue
        cat = item["category"].title()
        categories.setdefault(cat, []).append(item)

    if not categories:
        return "No items found."

    lines = []
    for cat, items in categories.items():
        lines.append(f"📂 {cat}")
        for it in items:
            halal = " ✅" if it.get("halal") else ""
            lines.append(f"  • {it['name']}  (${it['price']:.2f}){halal}")
    return "\n".join(lines)

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

    intent = detect_intent(question)

    if intent == "halal":
        answer = "Here are our Halal-certified items:\n\n" + list_menu(filter_fn=lambda x: x.get("halal"))
        return jsonify({"answer": answer})

    if intent == "veg_list":
        def is_veg(item):
            non_veg = {"chicken", "lamb", "bacon", "meat", "fish"}
            return not any(v in " ".join(item.get("ingredients", [])).lower() for v in non_veg)
        answer = "Here are our vegetarian-friendly items:\n\n" + list_menu(filter_fn=is_veg)
        return jsonify({"answer": answer})

    if intent == "list":
        answer = "Here's our full menu:\n\n" + list_menu()
        return jsonify({"answer": answer})

    # Default: AI item search
    matches = find_matches(question, menu)
    if not matches:
        return jsonify({"answer": "Sorry, I couldn't find anything matching that. Try asking about momos, salads, chaat, wraps, breakfast, and more!"})

    answer = "\n\n".join(format_item_text(item) for item in matches)
    return jsonify({"answer": answer})

# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
