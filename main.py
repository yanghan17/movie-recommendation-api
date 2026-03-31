"""
main.py — Movie Recommendation API powered by Claude
=====================================================

WHAT THIS PROJECT IS:
  A REST API that recommends movies based on your mood or preferences.
  Users send a request describing what they feel like watching,
  and Claude generates personalised recommendations with reasoning.

  This is a completely standalone project — no BizBot, no RAG.
  Just a clean example of how to build a proper API with FastAPI.

WHY THIS PROJECT:
  Every AI application needs a way for other programs (a mobile app,
  a website, a Telegram bot, another service) to talk to it.
  REST APIs are the standard way to do this.
  FastAPI is the modern Python standard for building REST APIs.

ENDPOINTS:
  GET  /              → welcome message
  GET  /health        → check if server is running
  POST /recommend     → get movie recommendations
  GET  /genres        → list available genres
  POST /explain       → explain why a movie is good for a given mood

HOW TO RUN:
  pip install -r requirements.txt
  export ANTHROPIC_API_KEY=your_key_here
  uvicorn main:app --reload

  Then open: http://localhost:8000/docs
  (FastAPI auto-generates an interactive page where you can test everything)
"""

import os
from typing import Optional

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ── FASTAPI APP SETUP ─────────────────────────────────────────────
# FastAPI() creates the application.
# The title, description, and version appear in the auto-generated docs.

app = FastAPI(
    title="Movie Recommendation API",
    description="Get AI-powered movie recommendations based on your mood and preferences",
    version="1.0.0"
)

# CORS Middleware: allows web browsers from any origin to call this API.
# Without this, a website hosted at http://myapp.com would be blocked
# from calling an API at http://localhost:8000 (browser security rule).
# CORSMiddleware tells the browser: "yes, this API accepts requests from anywhere"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # * means all origins — fine for development
    allow_methods=["*"],       # allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],       # allow any request headers
)

CLAUDE_MODEL = "claude-sonnet-4-6"


# ── PYDANTIC MODELS (Request & Response Schemas) ──────────────────
# Pydantic models do two things:
#   1. Define the exact shape of data expected in requests / returned in responses
#   2. Automatically validate incoming data — if a required field is missing
#      or the wrong type, FastAPI returns a clear error message automatically

class RecommendRequest(BaseModel):
    """
    The data a user sends when asking for recommendations.
    Field() adds extra metadata: description appears in the auto-docs,
    and example shows up as a pre-filled value when testing.
    """
    mood: str = Field(
        ...,  # the ... means this field is REQUIRED (no default value)
        description="How you're feeling or what kind of movie you want",
        example="I want something thrilling but not too scary, maybe a heist movie"
    )
    genre: Optional[str] = Field(
        None,  # None means this field is OPTIONAL
        description="Preferred genre (optional)",
        example="thriller"
    )
    max_results: int = Field(
        default=3,
        ge=1,   # ge = greater than or equal to: minimum value is 1
        le=10,  # le = less than or equal to: maximum value is 10
        description="How many movies to recommend (1-10)"
    )
    exclude: Optional[list[str]] = Field(
        None,
        description="Movies you've already seen and want to exclude",
        example=["Inception", "The Dark Knight"]
    )


class MovieRecommendation(BaseModel):
    """A single movie recommendation."""
    title: str
    year: int
    genre: str
    why_recommended: str    # Claude's reasoning for this recommendation
    mood_match: str         # How it matches the user's mood


class RecommendResponse(BaseModel):
    """The full response returned to the user."""
    mood_summary: str                       # Claude's interpretation of the mood
    recommendations: list[MovieRecommendation]
    total_found: int


class ExplainRequest(BaseModel):
    """Request to explain why a specific movie fits a mood."""
    movie_title: str = Field(..., example="Parasite")
    mood: str = Field(..., example="I want something thought-provoking")


class ExplainResponse(BaseModel):
    movie_title: str
    explanation: str


# ── HELPER: CALL CLAUDE ───────────────────────────────────────────
def call_claude(system: str, user_message: str, max_tokens: int = 1024) -> str:
    """
    A small helper that calls the Claude API and returns the text response.

    WHY A HELPER FUNCTION?
    We call Claude from multiple endpoints (recommend, explain).
    Instead of repeating the API call code each time, we put it here once.
    This is called the DRY principle: Don't Repeat Yourself.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


# ── ROUTES (ENDPOINTS) ────────────────────────────────────────────
# Each function below is one endpoint.
# The decorator (@app.get, @app.post) tells FastAPI:
#   - What HTTP method (GET = read data, POST = send data)
#   - What URL path ("/health", "/recommend", etc.)


@app.get("/")
def root():
    """
    The root endpoint — just a welcome message.
    GET / is what you see when you visit http://localhost:8000 in a browser.
    """
    return {
        "message": "Movie Recommendation API is running!",
        "docs": "Visit /docs for the interactive API documentation"
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Used by deployment systems (Docker, AWS, etc.) to verify the server is alive.
    If this returns 200 OK, the server is working.
    If it times out or returns an error, something is wrong.
    """
    return {"status": "healthy", "model": CLAUDE_MODEL}


@app.get("/genres")
def list_genres():
    """
    Returns the list of genres this API supports.
    GET endpoints don't need a request body — all info is in the URL.
    """
    genres = [
        "action", "comedy", "drama", "thriller", "horror",
        "sci-fi", "romance", "animation", "documentary",
        "mystery", "fantasy", "biography"
    ]
    return {"genres": genres, "count": len(genres)}


@app.post("/recommend", response_model=RecommendResponse)
def recommend_movies(request: RecommendRequest):
    """
    Main endpoint: get movie recommendations based on mood.

    HOW FASTAPI HANDLES THIS:
    1. User sends a POST request with JSON body (the RecommendRequest)
    2. FastAPI automatically parses and validates the JSON
    3. If valid, the `request` object is populated and passed to this function
    4. If invalid (missing fields, wrong types), FastAPI returns a 422 error automatically
    5. We call Claude, parse the response, and return a RecommendResponse

    response_model=RecommendResponse tells FastAPI to:
    - Validate that our return value matches the schema
    - Only include fields defined in the schema (no accidental data leaks)
    - Show the response shape in the auto-generated docs
    """
    # Build the exclusion string if the user listed movies to skip
    exclude_str = ""
    if request.exclude:
        exclude_str = f"\nDo NOT recommend these movies (user has seen them): {', '.join(request.exclude)}"

    genre_str = f"Preferred genre: {request.genre}" if request.genre else "No genre preference"

    # Prompt engineering: we ask Claude to respond in a structured format
    # so we can parse it predictably
    system = """You are an expert film critic and recommendation engine.
When asked for recommendations, respond in this EXACT format:

MOOD_SUMMARY: [one sentence describing the user's mood]

MOVIE_1:
TITLE: [movie title]
YEAR: [release year as a number]
GENRE: [primary genre]
WHY: [2-3 sentences explaining why this matches their mood]
MATCH: [one sentence on how it fits their specific request]

MOVIE_2:
[same format]

[continue for all movies requested]

Be specific and thoughtful. Only recommend real movies."""

    user_message = f"""Please recommend {request.max_results} movies for someone with this mood/preference:
"{request.mood}"
{genre_str}{exclude_str}"""

    raw_response = call_claude(system, user_message)

    # Parse the structured response into our Pydantic model
    # This is simple text parsing — in production you'd use JSON mode
    recommendations = []
    try:
        lines = raw_response.strip().split("\n")
        mood_summary = ""
        current_movie = {}

        for line in lines:
            line = line.strip()
            if line.startswith("MOOD_SUMMARY:"):
                mood_summary = line.replace("MOOD_SUMMARY:", "").strip()
            elif line.startswith("TITLE:"):
                current_movie["title"] = line.replace("TITLE:", "").strip()
            elif line.startswith("YEAR:"):
                year_str = line.replace("YEAR:", "").strip()
                current_movie["year"] = int("".join(filter(str.isdigit, year_str)) or "2000")
            elif line.startswith("GENRE:"):
                current_movie["genre"] = line.replace("GENRE:", "").strip()
            elif line.startswith("WHY:"):
                current_movie["why_recommended"] = line.replace("WHY:", "").strip()
            elif line.startswith("MATCH:"):
                current_movie["mood_match"] = line.replace("MATCH:", "").strip()
                # We have all fields for this movie — save it and start fresh
                if len(current_movie) == 5:
                    recommendations.append(MovieRecommendation(**current_movie))
                current_movie = {}

    except Exception as e:
        # If parsing fails, raise an HTTP 500 error with a description
        # HTTPException is FastAPI's way of returning error responses
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse Claude's response: {str(e)}. Raw: {raw_response[:200]}"
        )

    if not recommendations:
        raise HTTPException(
            status_code=500,
            detail="Claude returned a response but no movies could be parsed from it."
        )

    return RecommendResponse(
        mood_summary=mood_summary or "Based on your preferences",
        recommendations=recommendations,
        total_found=len(recommendations)
    )


@app.post("/explain", response_model=ExplainResponse)
def explain_movie(request: ExplainRequest):
    """
    Explain why a specific movie fits a particular mood.
    Useful for when you already have a movie in mind and want validation.
    """
    system = "You are a film critic. Give thoughtful, concise explanations of why movies match particular moods. 2-3 sentences maximum."

    user_message = f'Why is "{request.movie_title}" a good movie for someone who says: "{request.mood}"?'

    explanation = call_claude(system, user_message, max_tokens=256)

    return ExplainResponse(
        movie_title=request.movie_title,
        explanation=explanation
    )
