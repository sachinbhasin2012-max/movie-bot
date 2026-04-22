from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

df = pd.read_csv("movies.csv", encoding="latin1")

sessions = {}

def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = {
            "queries": [],
            "shown": []
        }
    return sessions[user_id]


def score_movie(row, keywords, session):
    score = 0
    text = " ".join(keywords)
    reasons = []

    if row['Genre'].lower() in text:
        score += 40
        reasons.append("genre match")

    if row['Language'].lower() in text:
        score += 20
        reasons.append("language match")

    if row['Mood'].lower() in text:
        score += 20
        reasons.append("mood match")

    score += row['Rating'] * 2
    reasons.append("high rating")

    if row['Title'] in session["shown"]:
        score -= 50
        reasons.append("already shown penalty")

    score += random.randint(0, 10)

    return score, reasons


def get_reason(movie, user_input, session):
    if session["shown"]:
        ref_movie = random.choice(session["shown"][-3:])
        return random.choice([
            f"Because you watched {ref_movie}",
            f"Similar to {ref_movie}",
            f"Based on your interest in {ref_movie}"
        ])
    
    if movie["Genre"].lower() in user_input:
        return f"Because you searched {movie['Genre']}"
    
    return "Trending on OTTplay"


@app.get("/chat")
def chat(user_id: str, message: str):
    session = get_session(user_id)

    session["queries"].append(message)
    session["queries"] = session["queries"][-10:]

    keywords = message.lower().split()

    scored = []
    for _, row in df.iterrows():
        s, reasons = score_movie(row, keywords, session)
        scored.append((row, s, reasons))

    scored_sorted = sorted(scored, key=lambda x: x[1], reverse=True)

    top20 = scored_sorted[:20]

    if not top20:
        # fallback
        top20 = [(row, row["Rating"], ["fallback: top rated"]) for _, row in df.sort_values(by="Rating", ascending=False).head(20).iterrows()]

    final = random.sample(top20, min(5, len(top20)))

    session["shown"].extend([r[0]["Title"] for r in final])

    responses = [
        "Top picks for you 👇",
        "You might like these 🎬",
        "Recommended based on your taste 👇"
    ]

    results = []
    for row, score, reasons in final:
        results.append({
            "title": row["Title"],
            "genre": row["Genre"],
            "language": row["Language"],
            "rating": row["Rating"],
            "runtime": row["Runtime"],
            "platform": row["Platform"],
            "reason": get_reason(row, message, session),
            "explain": ", ".join(reasons[:3])
        })

    return {
        "reply": random.choice(responses),
        "results": results,
        "recent_searches": session["queries"][-5:]
    }