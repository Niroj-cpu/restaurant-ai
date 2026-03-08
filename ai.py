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

def find_best_match(query, menu_items):
    """
    Returns the single best matching item, or None if nothing clears the threshold.

    Scoring signals (in descending priority):
      1. Exact multi-word keyword match  — highest weight
      2. Keyword token overlap           — medium weight
      3. Name substring / token match    — high weight
      4. Fuzzy full-name similarity      — medium weight
      5. Category match                  — low weight
      6. Ingredient match                — low weight
    """
    query_tokens = tokenize(query)
    query_lower  = query.lower().strip()
    scored = []

    for item in menu_items:
        score = 0.0

        # 1. Multi-word keyword match
        for kw in item.get("keywords", []):
            kw_lower = kw.lower().strip()
            if kw_lower == query_lower:
                score += 40 + len(kw_lower.split()) * 25   # perfect match
            elif kw_lower in query_lower:
                score += 40 + len(kw_lower.split()) * 20   # keyword inside query
            elif query_lower in kw_lower:
                score += 20 + len(query_lower.split()) * 10 # query inside keyword

        # 2. Keyword token overlap
        for kw in item.get("keywords", []):
            for kt in tokenize(kw):
                if len(kt) <= 2:
                    continue
                if any(similarity(kt, qt) > 0.82 for qt in query_tokens):
                    score += 10

        # 3. Name match
        name_lower = item["name"].lower()
        if name_lower in query_lower:
            score += 60
        else:
            name_tokens = tokenize(item["name"])
            matched = sum(
                1 for nt in name_tokens
                if any(similarity(nt, qt) > 0.82 for qt in query_tokens)
            )
            score += (matched / max(len(name_tokens), 1)) * 40

        # 4. Fuzzy full-name similarity
        score += similarity(query, item["name"]) * 30

        # 5. Category match
        if any(similarity(item.get("category", "").lower(), qt) > 0.82 for qt in query_tokens):
            score += 12

        # 6. Ingredient match
        for ing in item.get("ingredients", []):
            if any(similarity(ing.lower(), qt) > 0.85 for qt in query_tokens):
                score += 5

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    if scored and scored[0][0] >= 18:
        return scored[0][1]
    return None

def detect_intent(query):
    tokens      = tokenize(query)
    halal_kw    = {"halal"}
    veg_kw      = {"vegan", "vegetarian", "veggie"}
    list_kw     = {"menu", "list", "all", "everything", "options", "show", "see", "what"}

    if any(t in tokens for t in halal_kw):
        return "halal"
    if any(t in tokens for t in veg_kw) and any(t in tokens for t in list_kw):
        return "veg_list"
    if any(t in tokens for t in list_kw) and len(tokens) <= 5:
        return "list"
    return "search"

# Build a lookup of base-name → size variants at startup
SIZE_PATTERN = re.compile(r'\((Small|Medium|Large|Baby|Huge)\)', re.I)
SIZE_WORDS   = {"small", "medium", "large", "baby", "huge"}
SIZE_ORDER   = {"baby": 0, "small": 1, "medium": 2, "large": 3, "huge": 4}

_size_groups = {}  # base_name_lower → [item, ...]
for _item in menu:
    _m = SIZE_PATTERN.search(_item["name"])
    if _m:
        _base = SIZE_PATTERN.sub("", _item["name"]).strip().lower()
        _size_groups.setdefault(_base, []).append(_item)
# Sort each group by size order
for _base in _size_groups:
    _size_groups[_base].sort(
        key=lambda x: SIZE_ORDER.get(
            (SIZE_PATTERN.search(x["name"]).group(1) or "").lower(), 99)
    )

def find_size_group(query, menu_items=None):
    if menu_items is None:
        menu_items = menu
    """
    If the query matches a sized item but contains no size word,
    return all size variants so the user can pick. Returns a list or None.
    """
    query_lower  = query.lower().strip()
    query_tokens = set(tokenize(query))

    # If user already specified a size, let normal search handle it
    if query_tokens & SIZE_WORDS:
        return None

    best_base  = None
    best_score = 0

    for base in _size_groups:
        # Direct substring match
        if base in query_lower or query_lower in base:
            score = len(base)
        else:
            # Fuzzy token overlap
            base_tokens = set(tokenize(base))
            overlap = sum(
                1 for bt in base_tokens
                if any(similarity(bt, qt) > 0.82 for qt in query_tokens)
            )
            score = (overlap / max(len(base_tokens), 1)) * len(base)

        if score > best_score:
            best_score = score
            best_base  = base

    # Require confident match: score + at least one shared token with base name
    if best_score >= 5 and best_base:
        base_tokens = set(tokenize(best_base))
        if base_tokens & query_tokens or best_base in query_lower or query_lower in best_base:
            # Guard: if query matches a non-sized item's keyword exactly, prefer that item
            for item in menu_items:
                if SIZE_PATTERN.search(item["name"]):
                    continue
                for kw in item.get("keywords", []):
                    if kw.lower().strip() == query_lower:
                        return None  # exact non-sized match wins
            return _size_groups[best_base]
    return None

def format_size_group(items):
    """Format all size variants of an item into a single response."""
    base_name = SIZE_PATTERN.sub("", items[0]["name"]).strip()
    desc = items[0].get("description", "")
    lines = [f"{base_name}", f"{desc}", ""]
    for item in items:
        size_match = SIZE_PATTERN.search(item["name"])
        size = size_match.group(1) if size_match else "?"
        halal = " ✅" if item.get("halal") else ""
        lines.append(f"  {size:<8} — ${item['price']:.2f}{halal}")
    return "\n".join(lines)

def format_item(item):
    halal = "  ✅ Halal" if item.get("halal") else ""
    ingredients = ", ".join(item.get("ingredients", []))
    return (
        f"{item['name']} — ${item['price']:.2f}{halal}\n"
        f"{item['description']}\n"
        f"Ingredients: {ingredients}"
    )

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
            non_veg = {"chicken", "lamb", "bacon", "meat", "fish", "turkey", "ham", "tuna", "beef"}
            return not any(v in " ".join(item.get("ingredients", [])).lower() for v in non_veg)
        answer = "Here are our vegetarian-friendly items:\n\n" + list_menu(filter_fn=is_veg)
        return jsonify({"answer": answer})

    if intent == "list":
        answer = "Here's our full menu:\n\n" + list_menu()
        return jsonify({"answer": answer})

    # Check if query matches a size-variant group (e.g. "coffee", "latte", "ice cream")
    size_group = find_size_group(question)
    if size_group:
        return jsonify({"answer": format_size_group(size_group)})

    # Single best match
    match = find_best_match(question, menu)
    if not match:
        return jsonify({"answer": "Sorry, I couldn't find that on our menu. Try asking for something specific, or type 'menu' to browse everything!"})

    return jsonify({"answer": format_item(match)})

# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
