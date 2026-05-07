import base64
import json
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a brutally honest senior engineer with 15+ years of experience.
You have strong opinions. You don't sugarcoat things. You give direct, actionable feedback.

When reviewing a GitHub repository's README, you evaluate:
1. Clarity of purpose — does it immediately tell you what this is and why it matters?
2. Technical credibility — does the README reflect real engineering decisions?
3. Completeness — setup, usage, architecture, limitations?
4. USP — is there a clear, compelling differentiator?
5. Red flags — vague claims, missing docs, overcomplicated setup?

Respond ONLY with a valid JSON object. No markdown fences, no preamble, nothing else. Exactly this structure:
{
  "score": <number 1-10, one decimal>,
  "verdict": "<2-3 sentence blunt summary>",
  "strengths": [
    {"title": "<short title>", "detail": "<1-2 sentences>"}
  ],
  "weaknesses": [
    {"title": "<short title>", "detail": "<1-2 sentences>"}
  ],
  "recommendations": [
    "<actionable recommendation>"
  ],
  "hiring_signal": "<Would you hire the person who built this? One blunt sentence.>"
}"""

# ── Domain types ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str
    ref: Optional[str] = None


# ── Parsing & fetching (your original logic, unchanged) ───────────────────────

def _strip_git_suffix(repo: str) -> str:
    return repo[:-4] if repo.endswith(".git") else repo


def parse_github_url(url: str) -> RepoRef:
    u = url.strip()
    if not u:
        raise ValueError("Empty URL")

    ssh = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", u)
    if ssh:
        return RepoRef(owner=ssh.group(1), repo=_strip_git_suffix(ssh.group(2)))

    https = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)(.*)$", u)
    if not https:
        raise ValueError("Not a recognized GitHub repository URL.")

    owner = https.group(1)
    repo = _strip_git_suffix(https.group(2))
    rest = (https.group(3) or "").strip("/")

    ref = None
    if rest.startswith("tree/"):
        parts = rest.split("/", 2)
        if len(parts) >= 2:
            ref = parts[1]

    return RepoRef(owner=owner, repo=repo, ref=ref)


def fetch_readme(repo: RepoRef) -> str:
    github_token = os.getenv("GITHUB_TOKEN")
    url = f"https://api.github.com/repos/{repo.owner}/{repo.repo}/readme"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SeniorEye",
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    params = {"ref": repo.ref} if repo.ref else {}
    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if resp.status_code == 404:
        raise RuntimeError("No README found in this repository.")
    if resp.status_code == 403:
        raise RuntimeError("GitHub rate limit hit. Set GITHUB_TOKEN in your .env file.")
    if not resp.ok:
        raise RuntimeError(f"GitHub API error: HTTP {resp.status_code}")

    data = resp.json()
    content_b64 = data.get("content")
    if not content_b64 or data.get("encoding") != "base64":
        raise RuntimeError("Unexpected GitHub API response.")

    readme_bytes = base64.b64decode(content_b64.encode("utf-8"))
    return readme_bytes.decode("utf-8", errors="replace")


def review_with_gemini(readme_text: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found. Add it to your .env file.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    response = model.generate_content(readme_text[:8000])
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    repo_url: str


@app.post("/api/review")
async def review_repo(request: ReviewRequest):
    try:
        repo = parse_github_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        readme = fetch_readme(repo)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch repository data.")

    try:
        result = review_with_gemini(readme)
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned malformed response. Try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI review failed: {str(e)}")


@app.get("/")
async def root():
    return FileResponse("index.html")


app.mount("/", StaticFiles(directory=".", html=True), name="static")