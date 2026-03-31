# 🎬 Movie Recommendation API

An AI-powered REST API that generates personalised movie recommendations based on natural language mood descriptions. Built with **FastAPI** and the **Anthropic Claude API**.

---

## Overview

This project demonstrates how to wrap an LLM into a production-ready REST API using FastAPI. Users describe what they feel like watching in plain English, and Claude generates contextual recommendations with reasoning for each suggestion.

```
POST /recommend
{
  "mood": "something tense and cerebral, like a psychological thriller",
  "genre": "thriller",
  "max_results": 3
}
```

```json
{
  "mood_summary": "Looking for intellectually engaging, high-tension cinema",
  "recommendations": [
    {
      "title": "Prisoners",
      "year": 2013,
      "genre": "psychological thriller",
      "why_recommended": "...",
      "mood_match": "..."
    }
  ],
  "total_found": 3
}
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ASGI Server | [Uvicorn](https://www.uvicorn.org/) |
| Data Validation | [Pydantic v2](https://docs.pydantic.dev/) |
| AI Model | [Claude (Anthropic)](https://www.anthropic.com/) |
| Language | Python 3.11+ |

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Welcome message and docs link |
| `GET` | `/health` | Health check — returns server status |
| `GET` | `/genres` | List all supported genres |
| `POST` | `/recommend` | Get movie recommendations by mood |
| `POST` | `/explain` | Explain why a specific movie fits a mood |

Full interactive documentation available at `/docs` (Swagger UI) and `/redoc` when the server is running.

---

## Project Structure

```
movie-recommendation-api/
├── main.py              # FastAPI app — all routes, models, and logic
├── requirements.txt     # Python dependencies
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- An Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/yanghan17/movie-recommendation-api.git
cd movie-recommendation-api
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (Git Bash)
source venv/Scripts/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set your API key**

Mac/Linux/Git Bash:
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Windows PowerShell:
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

**5. Start the server**
```bash
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`. The `--reload` flag auto-restarts on code changes.

---

## Usage

### Interactive Docs (recommended)

Open `http://localhost:8000/docs` in your browser. FastAPI auto-generates a Swagger UI where you can test all endpoints without writing any code.

### cURL Examples

**Health check:**
```bash
curl http://localhost:8000/health
```

**Get recommendations:**
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "mood": "I want something funny and lighthearted",
    "max_results": 3
  }'
```

**With genre filter and exclusions:**
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "mood": "tense and suspenseful",
    "genre": "thriller",
    "max_results": 2,
    "exclude": ["Inception", "The Dark Knight"]
  }'
```

**Explain a specific movie:**
```bash
curl -X POST http://localhost:8000/explain \
  -H "Content-Type: application/json" \
  -d '{
    "movie_title": "Parasite",
    "mood": "I want something thought-provoking"
  }'
```

---

## Request & Response Schemas

### `POST /recommend`

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mood` | string | ✅ | Natural language description of what you want to watch |
| `genre` | string | ❌ | Optional genre filter |
| `max_results` | integer (1–10) | ❌ | Number of recommendations (default: 3) |
| `exclude` | list of strings | ❌ | Movies to exclude from recommendations |

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| `mood_summary` | string | Claude's interpretation of the mood |
| `recommendations` | list | Array of movie objects |
| `total_found` | integer | Number of movies returned |

Each movie object: `title`, `year`, `genre`, `why_recommended`, `mood_match`

---

## Key Concepts Demonstrated

**FastAPI request validation** — Pydantic models enforce types and constraints on all incoming requests. A missing required field or wrong type returns a `422 Unprocessable Entity` automatically, with a descriptive error message — no manual validation code needed.

**Prompt engineering** — Claude is prompted to return responses in a strict structured format, which is then parsed into typed Pydantic models. The system prompt constrains output shape; the user message fills in the dynamic content.

**Response models** — `response_model=RecommendResponse` in the route decorator tells FastAPI to validate the return value and strip any unintended fields before sending to the client.

**CORS middleware** — Applied globally so the API can be called from any frontend origin. In a production deployment this would be restricted to specific allowed domains.

---

## Development Notes

- Model is set via the `CLAUDE_MODEL` constant at the top of `main.py` — change this to use a different Claude version
- Parsing of Claude's structured text response is intentionally simple (line-by-line) — in a production system you'd use JSON mode or tool use for more reliable parsing
- No database or caching layer — every request calls the Claude API fresh. For production, consider caching popular mood queries

---

## License

MIT
