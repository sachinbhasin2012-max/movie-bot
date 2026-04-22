from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import random
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Movie Bot is Live 🚀"}

# Load data
df = pd.read_csv("movies.csv", encoding="latin1")

sessions = {}

def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = {"queries": [], "shown": []}
    return sessions[user_id]


# -------- Parsing Engine (CORE UPGRADE) --------
def parse_filters(msg):
    filters = {}

    # Language
    for lang in ["hindi", "english", "bengali", "punjabi", "tamil", "telugu"]:
        if lang in msg:
            filters["language"] = lang

    # Genre
    for genre in ["comedy", "action", "drama", "thriller", "romance"]:
        if genre in msg:
            filters["genre"] = genre

    # Movie name (if user mentions exact title)
    title_match = re.findall(r'"(.*?)"', msg)
    if title_match:
        filters["title"] = title_match[0]

    # Rating (>=)
    rating_match = re.search(r'(\d+)\s*(star|rating)', msg)
    if rating_match:
        filters["rating_min"] = int(rating_match.group(1))

    # Runtime filters
    under_runtime = re.search(r'under\s*(\d+)', msg)
    over_runtime = re.search(r'over\s*(\d+)', msg)

    if under_runtime:
        filters["runtime_max"] = int(under_runtime.group(1))

    if over_runtime:
        filters["runtime_min"] = int(over_runtime.group(1))

    # Between runtime
    between_runtime = re.search(r'between\s*(\d+)\s*and\s*(\d+)', msg)
    if between_runtime:
        filters["runtime_min"] = int(between_runtime.group(1))
        filters["runtime_max"] = int(between_runtime.group(2))

    return filters


# -------- Apply Filters --------
def apply_filters(df, filters):
    filtered = df.copy()

    if "language" in filters:
        filtered = filtered[filtered["Language"].str.lower() == filters["language"]]

    if "genre" in filters:
        filtered = filtered[filtered["Genre"].str.lower() == filters["genre"]]

    if "title" in filters:
        filtered = filtered[filtered["Title"].str.lower().str.contains(filters["title"])]

    if "rating_min" in filters:
        filtered = filtered[filtered["Rating"] >= filters["rating_min"]]

    if "runtime_min" in filters:
        filtered = filtered[filtered["Runtime"] >= filters["runtime_min"]]

    if "runtime_max" in filters:
        filtered = filtered[filtered["Runtime"] <= filters["runtime_max"]]

    return filtered


# -------- Scoring --------
def score_movie(row, session):
    score = row["Rating"] * 2

    if row["Title"] in session["shown"]:
        score -= 50

    score += random.randint(0, 2)

    return score


def get_reason(row, session):
    if session["shown"]:
        ref = random.choice(session["shown"][-3:])
        return f"Because you watched {ref}"
    return "Trending on OTTplay"


# -------- Chat API --------
@app.get("/chat")
def chat(user_id: str, message: str):
    session = get_session(user_id)
    msg = message.lower()

    # -------- Intent: Count --------
    if "how many" in msg:
        return {
            "reply": f"I have {len(df)} movies in my database 🎬",
            "results": [],
            "recent_searches": session["queries"][-5:]
        }

    session["queries"].append(message)
    session["queries"] = session["queries"][-10:]

    # -------- NEW FILTER ENGINE --------
    filters = parse_filters(msg)
    filtered_df = apply_filters(df, filters)

    # -------- Fallback --------
    if filtered_df.empty:
        filtered_df = df.sort_values(by="Rating", ascending=False).head(20)

    # -------- Ranking --------
    filtered_df["score"] = filtered_df.apply(lambda row: score_movie(row, session), axis=1)
    ranked = filtered_df.sort_values(by="score", ascending=False)

    # -------- Final (NO RANDOM BREAK) --------
    top = ranked.head(10)
    final = top.sample(min(5, len(top)))  # controlled diversity

    session["shown"].extend(final["Title"].tolist())

    results = []
    for _, row in final.iterrows():
        results.append({
            "title": row["Title"],
            "genre": row["Genre"],
            "language": row["Language"],
            "rating": row["Rating"],
            "runtime": row["Runtime"],
            "platform": row["Platform"],
            "reason": get_reason(row, session),
            "explain": f"Matched filters: {', '.join(filters.keys()) if filters else 'general'}"
        })

    return {
        "reply": "Recommendations based on your filters 👇",
        "results": results,
        "recent_searches": session["queries"][-5:]
    }