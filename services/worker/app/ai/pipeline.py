"""
AI pipeline — called by worker_ai for each article.

Uses the configured API provider for generation and 768-dimension embeddings.

Prompts loaded from config/llm_prompts.yaml
Scoring weights from config/scoring_rules.yaml
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import yaml

from app.utils.logging import get_logger

log = get_logger("ai")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
BACKGROUND_AI_ENABLED = os.environ.get("BACKGROUND_AI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").strip().rstrip("/")
LLM_MODEL = os.environ.get("OPENAI_MODEL", os.environ.get("LLM_MODEL", "gpt-4.1-mini")).strip()
EMBED_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")).strip()
OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text").strip()
EMBED_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "768"))
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
ARTICLE_OUTPUT_TOKENS = int(os.environ.get("ARTICLE_OUTPUT_TOKENS", "320"))
BRIEFING_LANGUAGE = os.environ.get("BRIEFING_LANGUAGE", "fr").strip() or "fr"
PROMPTS_PATH  = os.environ.get("PROMPTS_PATH", "/app/config/llm_prompts.yaml")
SCORING_PATH  = os.environ.get("SCORING_PATH", "/app/config/scoring_rules.yaml")
USER_PROFILE_PATH = os.environ.get("USER_PROFILE_PATH", "/app/config/user_profile.yaml")

_prompts: dict = {}
_scoring: dict = {}
_user_profile: dict = {}
ARTICLE_CATEGORIES = {
    "ai", "local llm", "agents", "supply chain", "pharma logistics",
    "transport", "carbon accounting", "warehouse automation", "robotics",
    "saas", "startups", "cybersecurity", "geopolitics",
    "european regulation", "climate", "finance", "travel", "culture", "other",
}


def _load_config():
    global _prompts, _scoring, _user_profile
    if not _prompts and os.path.exists(PROMPTS_PATH):
        with open(PROMPTS_PATH, encoding="utf-8") as f:
            _prompts = yaml.safe_load(f) or {}
    if not _scoring and os.path.exists(SCORING_PATH):
        with open(SCORING_PATH, encoding="utf-8") as f:
            _scoring = yaml.safe_load(f) or {}
    if not _user_profile:
        profile_path = USER_PROFILE_PATH if os.path.exists(USER_PROFILE_PATH) else f"{USER_PROFILE_PATH}.example"
        if os.path.exists(profile_path):
            with open(profile_path, encoding="utf-8") as f:
                _user_profile = yaml.safe_load(f) or {}


def _extract_openai_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
    return " ".join(parts).strip()


def _llm_generate(
    prompt: str,
    model: str = LLM_MODEL,
    *,
    json_mode: bool = False,
    max_output_tokens: int | None = None,
) -> str:
    try:
        if not BACKGROUND_AI_ENABLED:
            log.info("background_llm_skipped")
            return ""
        if LLM_PROVIDER == "ollama":
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"temperature": 0.2, "num_predict": max_output_tokens or ARTICLE_OUTPUT_TOKENS},
            }
            if json_mode:
                payload["format"] = "json"
            resp = httpx.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return str(resp.json().get("response") or "").strip()
        if LLM_PROVIDER != "openai":
            log.warning("unsupported_llm_provider", provider=LLM_PROVIDER)
            return ""
        if not OPENAI_API_KEY:
            log.warning("missing_openai_api_key")
            return ""
        resp = httpx.post(
            f"{OPENAI_BASE_URL}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": prompt, "max_output_tokens": max_output_tokens or ARTICLE_OUTPUT_TOKENS},
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return _extract_openai_text(resp.json())
    except Exception as exc:
        log.warning("llm_generate_error", provider=LLM_PROVIDER, error=str(exc))
        return ""


def _embed_text(text: str, model: str = EMBED_MODEL) -> Optional[list[float]]:
    try:
        if not BACKGROUND_AI_ENABLED:
            log.info("background_embedding_skipped")
            return None
        if LLM_PROVIDER == "ollama":
            resp = httpx.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": text[:4000]},
                timeout=LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            embeddings = (resp.json() or {}).get("embeddings") or []
            embedding = embeddings[0] if embeddings else None
            if not isinstance(embedding, list) or len(embedding) != EMBED_DIMENSIONS:
                log.warning("ollama_embedding_invalid", expected_dimensions=EMBED_DIMENSIONS, actual_dimensions=len(embedding or []))
                return None
            return embedding
        if LLM_PROVIDER != "openai":
            log.warning("unsupported_embedding_provider", provider=LLM_PROVIDER)
            return None
        if not OPENAI_API_KEY:
            log.warning("missing_openai_api_key")
            return None
        resp = httpx.post(
            f"{OPENAI_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": text[:4000], "dimensions": EMBED_DIMENSIONS},
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or []
        if not data:
            return None
        embedding = data[0].get("embedding")
        return embedding if isinstance(embedding, list) else None
    except Exception as exc:
        log.warning("embedding_error", provider=LLM_PROVIDER, error=str(exc))
        return None


# ── Individual AI tasks ───────────────────────────────────────────────────────

def summarize_short(title: str, text: str) -> str:
    _load_config()
    prompt_tpl = _prompts.get("summarize_short", "Summarize in 3 bullet points:")
    content = f"{title}\n\n{text[:3000]}"
    return _llm_generate(f"{prompt_tpl}\n\n{content}")


def summarize_long(title: str, text: str) -> str:
    _load_config()
    prompt_tpl = _prompts.get("summarize_long", "Summarize in 10 lines:")
    content = f"{title}\n\n{text[:5000]}"
    return _llm_generate(f"{prompt_tpl}\n\n{content}")


def classify_article(title: str, text: str) -> str:
    _load_config()
    prompt_tpl = _prompts.get("classify", "Classify into one category:")
    content = f"{title}\n\n{text[:2000]}"
    result = _llm_generate(f"{prompt_tpl}\n\n{content}")
    # Clean up — model may return extra text
    first_line = result.strip().split("\n")[0].strip()
    return first_line[:100] if first_line else "Other"


def extract_entities(title: str, text: str) -> dict:
    _load_config()
    prompt_tpl = _prompts.get("extract_entities", "Extract entities as JSON:")
    content = f"{title}\n\n{text[:3000]}"
    raw = _llm_generate(f"{prompt_tpl}\n\n{content}")
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


def normalize_article(title: str, text: str) -> dict:
    """Produce the complete, database-ready enrichment in one local LLM call.

    The worker still has deterministic fallbacks, so malformed or unavailable LLM
    output never prevents the raw article from being stored and scored.
    """
    _load_config()
    prompt_tpl = _prompts.get("normalize_article", "Return a JSON article record.")
    content = f"TITLE:\n{title}\n\nARTICLE:\n{text[:6000]}"
    raw = _llm_generate(f"{prompt_tpl}\n\n{content}", json_mode=True)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end]) if start >= 0 and end > start else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        return {}

    entity_keys = ("people", "companies", "countries", "cities", "products", "technologies", "regulations")
    entities = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    data["entities"] = {
        key: [str(item)[:160] for item in (entities.get(key) or []) if isinstance(item, (str, int, float))][:20]
        for key in entity_keys
    }
    topics = data.get("topics") if isinstance(data.get("topics"), list) else []
    data["topics"] = [str(item).strip()[:100] for item in topics if str(item).strip()][:8]
    for key, limit in (("summary_short", 1200), ("summary_long", 4000), ("category", 100), ("sentiment", 32)):
        value = data.get(key)
        data[key] = str(value).strip()[:limit] if isinstance(value, (str, int, float)) else ""
    if data["category"].lower() not in ARTICLE_CATEGORIES:
        data["category"] = "Other"
    if data["sentiment"].lower() not in {"positive", "neutral", "negative", "mixed"}:
        data["sentiment"] = "neutral"

    # A malformed or title-only local-model summary is worse than an honest
    # extractive fallback: it is what turns a dashboard into a clickbait feed.
    # Keep factual sentences from the extracted article when the model did not
    # provide enough usable substance.
    fallback_short = _extractive_summary(text, sentence_limit=3, character_limit=900)
    fallback_long = _extractive_summary(text, sentence_limit=5, character_limit=1800)
    if not _has_information_value(data["summary_short"], title):
        data["summary_short"] = fallback_short
    if not _has_information_value(data["summary_long"], title):
        data["summary_long"] = fallback_long
    return data


def _extractive_summary(text: str, *, sentence_limit: int, character_limit: int) -> str:
    """Deterministic factual fallback based on the real extracted article."""
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return ""
    candidates = re.split(r"(?<=[.!?])\s+", clean)
    selected: list[str] = []
    total = 0
    for candidate in candidates:
        candidate = candidate.strip(" -•\t")
        # Headings and marketing fragments do not make an informative fact.
        if len(candidate) < 55 or len(candidate) > 480:
            continue
        normalized = candidate.lower()
        # Do not promote a rhetorical clickbait question into the first fact.
        if "?" in candidate or normalized.startswith(("et si ", "imaginez", "decouvrez", "voici")):
            continue
        if total + len(candidate) > character_limit and selected:
            break
        selected.append(candidate)
        total += len(candidate)
        if len(selected) >= sentence_limit:
            break
    return "\n".join(f"- {sentence}" for sentence in selected)


def _has_information_value(summary: str, title: str) -> bool:
    compact = re.sub(r"\s+", " ", summary or "").strip()
    if len(compact) < 90:
        return False
    title_words = {word.lower() for word in re.findall(r"\w+", title or "") if len(word) >= 5}
    summary_words = {word.lower() for word in re.findall(r"\w+", compact) if len(word) >= 5}
    # A summary that mostly repeats the headline has no added value.
    if summary_words and len(summary_words - title_words) < 5:
        return False
    return bool(re.search(r"[.!]|\n[-•]", compact))


def synthesize_briefing(source_digest: str) -> str:
    """Create a concise second-level synthesis from selected article summaries."""
    _load_config()
    prompt_tpl = _prompts.get("generate_briefing", "Summarize the selected news.")
    if not source_digest.strip():
        return ""
    language_instruction = (
        "MANDATORY: Write every heading and bullet in French. Translate source facts faithfully; "
        "do not reuse English headings."
        if BRIEFING_LANGUAGE.lower().startswith("fr")
        else f"MANDATORY: Write every heading and bullet in {BRIEFING_LANGUAGE}."
    )
    return _llm_generate(
        f"{prompt_tpl}\n\nLANGUAGE: {BRIEFING_LANGUAGE}\n{language_instruction}\n\nSOURCE DIGEST:\n{source_digest[:14000]}",
        max_output_tokens=450,
    )


def generate_embedding(text: str) -> Optional[list[float]]:
    return _embed_text(text)


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(
    article,
    category: str,
    quality_score: float,
    published_at: Optional[datetime],
    source_name: str,
    entities: Optional[dict] = None,
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
    user_profile = _user_profile.get("profile", {}) if isinstance(_user_profile, dict) else {}
    profile_interests = user_profile.get("interests", {}) if isinstance(user_profile, dict) else {}
    negative_keywords = user_profile.get("negative_keywords", {}) if isinstance(user_profile, dict) else {}
    anti_dopamine = user_profile.get("anti_dopamine", {}) if isinstance(user_profile, dict) else {}
    anti_enabled = bool(anti_dopamine.get("enabled", False)) if isinstance(anti_dopamine, dict) else False
    clickbait_keywords = [
        str(x).lower() for x in (anti_dopamine.get("clickbait_keywords", []) if isinstance(anti_dopamine, dict) else [])
    ]
    min_word_count = int(anti_dopamine.get("min_word_count", 250)) if isinstance(anti_dopamine, dict) else 250
    excessive_punctuation_penalty = float(anti_dopamine.get("excessive_punctuation_penalty", 0.1)) if isinstance(anti_dopamine, dict) else 0.1
    title_caps_penalty = float(anti_dopamine.get("title_caps_penalty", 0.1)) if isinstance(anti_dopamine, dict) else 0.1
    boost_entities = [str(item).lower() for item in (user_profile.get("boost_entities", []) or [])]
    article_text = f"{getattr(article, 'title', '') or ''} {getattr(article, 'description', '') or ''} {getattr(article, 'text_content', '') or ''}".lower()
    article_title = str(getattr(article, "title", "") or "")

    # Topic interest score
    cat_lower = (category or "").lower()
    topic_score = max(
        (v for k, v in interests.items() if k.lower() in cat_lower or cat_lower in k.lower()),
        default=0.3,
    )

    # User profile relevance: weighted topic + entity boosts.
    profile_topic_score = max(
        (float(v) for k, v in profile_interests.items() if k.lower().replace("_", " ") in cat_lower or cat_lower in k.lower().replace("_", " ")),
        default=0.3,
    )

    entity_bonus = 0.0
    if boost_entities:
        entities_blob = " ".join(
            str(value)
            for value in (
                (entities or {}).get("people", []),
                (entities or {}).get("companies", []),
                (entities or {}).get("countries", []),
                (entities or {}).get("cities", []),
                (entities or {}).get("products", []),
                (entities or {}).get("technologies", []),
                (entities or {}).get("regulations", []),
            )
        ).lower()
        for entity in boost_entities:
            if entity and (entity in entities_blob or entity in article_text):
                entity_bonus += 0.05

    negative_penalty = 0.0
    for keyword, penalty in negative_keywords.items():
        keyword_norm = str(keyword).lower().replace("_", " ")
        if keyword_norm and keyword_norm in article_text:
            negative_penalty += abs(float(penalty)) * 0.1

    anti_dopamine_score = 0.0
    matched_negative_keywords: list[str] = []
    if anti_enabled:
        for keyword in clickbait_keywords:
            if keyword and keyword in article_text:
                matched_negative_keywords.append(keyword)
        anti_dopamine_score += min(len(matched_negative_keywords) * 0.05, 0.4)

        if int(getattr(article, "word_count", 0) or 0) < min_word_count:
            anti_dopamine_score += 0.1

        punctuation_count = article_title.count("!") + article_title.count("?")
        if punctuation_count >= 3:
            anti_dopamine_score += excessive_punctuation_penalty

        letters = [c for c in article_title if c.isalpha()]
        if letters:
            caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if caps_ratio > 0.7 and len(letters) > 8:
                anti_dopamine_score += title_caps_penalty

    anti_dopamine_score = min(max(anti_dopamine_score, 0.0), 1.0)

    personal_relevance_score = min(
        max(
            0.5 * topic_score
            + 0.5 * profile_topic_score
            + entity_bonus
            - negative_penalty
            - anti_dopamine_score,
            0.0,
        ),
        1.0,
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
        personal_relevance_score * weights.get("topic_interest", 0.30)
        + freshness_score * weights.get("freshness", 0.25)
        + novelty_score   * weights.get("novelty", 0.20)
        + src_score       * weights.get("source", 0.15)
        + quality_norm    * weights.get("quality", 0.10)
    )
    final = max(0.0, min(final - (anti_dopamine_score * 0.15), 1.0))

    if isinstance(entities, dict):
        entities.setdefault("_scoring", {})
        entities["_scoring"]["dopamine_penalty_score"] = round(anti_dopamine_score, 3)
        entities["_scoring"]["matched_negative_keywords"] = matched_negative_keywords

    return {
        "importance_score":          round(topic_score, 3),
        "freshness_score":           round(freshness_score, 3),
        "source_score":              round(src_score, 3),
        "novelty_score":             round(novelty_score, 3),
        "personal_relevance_score":  round(personal_relevance_score, 3),
        "quality_score":             round(quality_norm, 3),
        "final_score":               round(final, 3),
    }
