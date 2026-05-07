# SeniorEye 👁

**Paste a GitHub repo URL. Get an honest senior engineer review.**

No flattery. No generic feedback. SeniorEye reads the README and tells you what a grumpy, experienced engineer actually thinks — score, strengths, weaknesses, recommendations, and a hiring signal.

---

## What it does

- Fetches the README from any public GitHub repository
- Sends it to Gemini 2.5 Flash with a structured senior engineer prompt
- Returns a scored review: verdict, strengths, weaknesses, actionable recommendations, and a one-line hiring signal

## Stack

- **Backend** — FastAPI + Python
- **Frontend** — Vanilla HTML/CSS/JS (no build step, no dependencies)
- **AI** — Google Gemini 2.5 Flash via `google-generativeai`
- **Hosting** — Vercel

## Running locally

**1. Clone and install**

```bash
git clone https://github.com/KumarManik44/SeniorEye.git
cd SeniorEye
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Set up environment variables**

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_token_here   # optional, increases rate limit
```

Get your Gemini API key at [aistudio.google.com](https://aistudio.google.com).

**3. Run**

```bash
uvicorn app:app --reload --port 8501
```

Open [http://localhost:8501](http://localhost:8501).

## Deploying to Vercel

This project deploys to Vercel via GitHub integration.

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
3. Add environment variables in Vercel dashboard:
   - `GEMINI_API_KEY`
   - `GITHUB_TOKEN` (optional)
4. Deploy

## Project structure

```
SeniorEye/
├── app.py           # FastAPI backend + GitHub fetch + Gemini review logic
├── index.html       # Frontend (single file, no build step)
├── requirements.txt
├── .env             # Not committed — add your keys here
└── .gitignore
```

## Limitations

- Reviews are based on the README only — no source code traversal
- README truncated at 8,000 characters for very large files
- Supports public repos only (no auth for private repos)

---

Built by [Kumar Manik](https://github.com/KumarManik44)
