"""
AI pipeline — called by worker_ai for each article.

Uses Ollama locally (https://ollama.com) with:
  - nomic-embed-text  → embeddings (768-dim)
  - mistral / qwen2.5 → summarize, classify, extract entities

Prompts loaded from config/llm_prompts.yaml
Scoring weights from config/scoring_rules.yaml
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import yaml

from app.utils.logging import get_logger

log = get_logger("ai")

OLLAMA_URL  = os.environ.get("OLLAMA_URL", "http://ollama:11434")
LLM_MODEL   = os.environ.get("LLM_MODEL", "mistral")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
PROMPTS_PATH  = os.environ.get("PROMPTS_PATH", "/app/config/llm_prompts.yaml")
SCORING_PATH  = os.environ.get("SCORING_PATH", "/app/config/scoring_rules.yaml")

_prompts: dict = {}
_scoring: dict = {}


def _load_config():
    global _prompts, _scoring
    if not _prompts and os.path.exists(PROMPTS_PATH):
        with open(PROMPTS_PATH, encoding="utf-8") as f:
            _prompts = yaml.safe_load(f) or {}
    if not _scoring and os.path.exists(SCORING_PATH):
        with open(SCORING_PATH, encoding="utf-8") as f:
            _scoring = yaml.safe_load(f) or {}


def _ollama_generate(prompt: str, model: str = LLM_MODEL) -> str:
    """Call Ollama /api/generate (sync via httpx)."""
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        log.warning("ollama_generate_error", error=str(exc))
        return ""


def _ollama_embed(text: str, model: str = EMBED_MODEL) -> Optional[list[float]]:
    """Call Ollama /api/embeddings (sync via httpx)."""
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model, "prompt": text[:2000]},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("embedding")
    except Exception as exc:
        log.warning("ollama_embed_error", error=str(exc))
        return None


# ── Individual AI tasks ───────────────────────────────────────────────────────

def summarize_short(title: str, text: str) -> str:
    _load_config()
    prompt_tpl = _prompts.get("summarize_short", "Summarize in 3 bullet points:")
    content = f"{title}\n\n{text[:3000]}"
    return _ollama_generate(f"{prompt_tpl}\n\n{content}")


def summarize_long(title: str, text: str) -> str:
    _load_config()
    prompt_tpl = _prompts.get("summarize_long", "Summarize in 10 lines:")
    content = f"{title}\n\n{text[:5000]}"
    return _ollama_generate(f"{prompt_tpl}\n\n{content}")


def classify_article(title: str, text: str) -> str:
    _load_config()
    prompt_tpl = _prompts.get("classify", "Classify into one category:")
    content = f"{title}\n\n{text[:2000]}"
    result = _ollama_generate(f"{prompt_tpl}\n\n{content}")
    # Clean up — model may return extra text
    first_line = result.strip().split("\n")[0].strip()
    return first_line[:100] if first_line else "Other"


def extract_entities(title: str, text: str) -> dict:
    _load_config()
    prompt_tpl = _prompts.get("extract_entities", "Extract entities as JSON:")
    content = f"{title}\n\n{text[:3000]}"
    raw = _ollama_generate(f"{prompt_tpl}\n\n{content}")
    # Parse JSON safely
    try:
        # Find JSON block
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return {"people": [], "companies": [], "countries": [], "cities": [],
            "products": [], "technologies": [], "regulations": []}


def generate_embedding(text: str) -> Optional[list[float]]:
    return _ollama_embed(text)


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(
    article,
    category: str,
    quality_score: float,
    published_at: Optional[datetime],
    source_name: str,
) -> dict[str, float]:
    _load_config()
    interests     = _scoring.get("interests", {})
    source_weights = _scoring.get("source_weights", {})
    freshness_cfg  = _scoring.get("freshness", {})
    weights        = _scoring.get("formula_weights", {
        "topic_interest": 0.30,
        "freshness": 0.25,
        "novelty": 0.20,
        "source": 0.15,
        "quality": 0.10,
    })

    # Topic interest score
    cat_lower = (category or "").lower()
    topic_score = max(
        (v for k, v in interests.items() if k.lower() in cat_lower or cat_lower in k.lower()),
        default=0.3,
    )

    # Freshness score
    freshness_score = 0.5
    if published_at:
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - published_at
        if age < timedelta(hours=6):
            freshness_score = float(freshness_cfg.get("less_than_6h", 1.0))
        elif age < timedelta(hours=24):
            freshness_score = float(freshness_cfg.get("less_than_24h", 0.9))
        elif age < timedelta(hours=48):
            freshness_score = float(freshness_cfg.get("less_than_48h", 0.75))
        elif age < timedelta(hours=72):
            freshness_score = float(freshness_cfg.get("less_than_72h", 0.6))
        elif age < timedelta(days=7):
            freshness_score = float(freshness_cfg.get("less_than_7d", 0.35))
        else:
            freshness_score = float(freshness_cfg.get("older", 0.15))

    # Source score
    src_lower = (source_name or "").lower()
    src_score = 0.65
    if "arxiv" in src_lower:
        src_score = float(source_weights.get("arxiv", 1.0))
    elif "reddit" in src_lower:
        src_score = float(source_weights.get("reddit", 0.6))
    elif "github" in src_lower:
        src_score = float(source_weights.get("github", 0.8))
    elif "hackernews" in src_lower or "hacker news" in src_lower:
        src_score = float(source_weights.get("hackernews", 0.75))
    else:
        src_score = float(source_weights.get("major_media", 0.9))

    # Normalize quality (0-100 → 0-1)
    quality_norm = min(float(quality_score or 0) / 100.0, 1.0)

    # Novelty placeholder (0.7 default — will be updated during clustering)
    novelty_score = 0.7

    # Weighted final score
    final = (
        topic_score   * weights.get("topic_interest", 0.30)
        + freshness_score * weights.get("freshness", 0.25)
        + novelty_score   * weights.get("novelty", 0.20)
        + src_score       * weights.get("source", 0.15)
        + quality_norm    * weights.get("quality", 0.10)
    )

    return {
        "importance_score":          round(topic_score, 3),
        "freshness_score":           round(freshness_score, 3),
        "source_score":              round(src_score, 3),
        "novelty_score":             round(novelty_score, 3),
        "personal_relevance_score":  round(topic_score, 3),
        "quality_score":             round(quality_norm, 3),
        "final_score":               round(min(final, 1.0), 3),
    }
