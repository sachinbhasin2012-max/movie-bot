from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import random

app = FastAPI()

# Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
df = pd.read_csv("movies.csv", encoding="ISO-8859-1")

# Session memory
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

    if row['Genre'].lower() in keywords:
        score += 40

    if row['Language'].lower() in keywords:
        score += 20

    if row['Mood'].lower() in keywords:
        score += 20

    score += row['Rating'] * 2

    if row['Title'] in session["shown"]:
        score -= 30

    score += random.randint(0, 10)

    return score

def get_reason(movie, user_input, session):
    if movie["Genre"].lower() in user_input:
        return f"Because you searched {movie['Genre']}"
    
    if movie["Language"].lower() in user_input:
        return f"Popular {movie['Language']} content"
    
    if len(session["queries"]) > 3:
        return "Based on your recent activity"
    
    return "Trending on OTTplay"

@app.get("/chat")
def chat(user_id: str, message: str):
    session = get_session(user_id)

    session["queries"].append(message)
    session["queries"] = session["queries"][-10:]

    keywords = message.lower().split()

    df["score"] = df.apply(lambda row: score_movie(row, keywords, session), axis=1)

    top20 = df.sort_values(by="score", ascending=False).head(20)

    final = top20.sample(5)

    session["shown"].extend(final["Title"].tolist())

    results = []
    for _, row in final.iterrows():
        results.append({
            "title": row["Title"],
            "genre": row["Genre"],
            "language": row["Language"],
            "rating": row["Rating"],
            "platform": row["Platform"],
            "reason": get_reason(row, message, session)
        })

    return {
        "reply": "Here are some movies for you 👇",
        "results": results
    }