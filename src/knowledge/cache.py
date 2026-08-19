"""
Redis caching layer.

Caches:
  - Retrieval results (question → serialised context)
  - LLM responses (prompt hash → response text)
  - Evaluation results (question+answer hash → evaluation dict)
  - Ingestion markers (source hash → "1")

Falls back gracefully when Redis is unavailable.
"""

import hashlib
import json
import pickle
import time
from typing import Any, Optional

import redis as redis_lib

from src.utils.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_TTL
from src.utils.logger_config import logger

_redis_client: Optional[redis_lib.Redis] = None
_last_failed_at: float = 0.0          # epoch seconds of last failed attempt
_RETRY_COOLDOWN: float = 30.0         # seconds to wait before retrying


def get_redis_client() -> Optional[redis_lib.Redis]:
    """
    Return a singleton Redis client.
    Returns None if Redis is unavailable (silent fallback).
    After a failure, waits _RETRY_COOLDOWN seconds before trying again
    to avoid timeout spam on every Streamlit render.
    """
    global _redis_client, _last_failed_at

    # Already connected — return immediately
    if _redis_client is not None:
        return _redis_client

    # Still within cooldown after a previous failure — skip silently
    if time.time() - _last_failed_at < _RETRY_COOLDOWN:
        return None

    try:
        client = redis_lib.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_connect_timeout=2,
            decode_responses=False,
        )
        client.ping()
        _redis_client = client
        _last_failed_at = 0.0
        logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    except Exception as e:
        _last_failed_at = time.time()
        logger.warning(f"Redis unavailable — caching disabled. ({e})")
        _redis_client = None
    return _redis_client


def _make_key(prefix: str, *parts: str) -> str:
    """Build a namespaced Redis key from a prefix and variable parts."""
    combined = ":".join(parts)
    digest = hashlib.md5(combined.encode()).hexdigest()[:20]
    return f"eval_gen:{prefix}:{digest}"


# ─── Retrieval cache ─────────────────────────────────────────────────────────

def cache_retrieval(question: str, context_docs: list, ttl: int = REDIS_TTL) -> None:
    """Cache a retrieval result (list of Document objects) for a question."""
    client = get_redis_client()
    if client is None:
        return
    key = _make_key("retrieval", question)
    try:
        client.setex(key, ttl, pickle.dumps(context_docs))
        logger.debug(f"Cached retrieval for key: {key}")
    except Exception as e:
        logger.warning(f"Failed to cache retrieval: {e}")


def get_cached_retrieval(question: str) -> Optional[list]:
    """Return cached retrieval result or None."""
    client = get_redis_client()
    if client is None:
        return None
    key = _make_key("retrieval", question)
    try:
        data = client.get(key)
        if data:
            logger.debug(f"[CACHE HIT] Retrieval: {key}")
            return pickle.loads(data)
    except Exception as e:
        logger.warning(f"Failed to read retrieval cache: {e}")
    return None


# ─── LLM response cache ───────────────────────────────────────────────────────

def cache_llm_response(prompt_key: str, response: str, ttl: int = REDIS_TTL) -> None:
    """Cache an LLM response string."""
    client = get_redis_client()
    if client is None:
        return
    key = _make_key("llm", prompt_key)
    try:
        client.setex(key, ttl, response.encode("utf-8"))
        logger.debug(f"Cached LLM response: {key}")
    except Exception as e:
        logger.warning(f"Failed to cache LLM response: {e}")


def get_cached_llm_response(prompt_key: str) -> Optional[str]:
    """Return a cached LLM response or None."""
    client = get_redis_client()
    if client is None:
        return None
    key = _make_key("llm", prompt_key)
    try:
        data = client.get(key)
        if data:
            logger.debug(f"[CACHE HIT] LLM response: {key}")
            return data.decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to read LLM cache: {e}")
    return None


# ─── Evaluation cache ─────────────────────────────────────────────────────────

def cache_evaluation(question: str, answer: str, evaluation: dict, ttl: int = REDIS_TTL) -> None:
    """Cache an evaluation result dict."""
    client = get_redis_client()
    if client is None:
        return
    key = _make_key("evaluation", question, answer[:200])
    try:
        client.setex(key, ttl, json.dumps(evaluation).encode("utf-8"))
        logger.debug(f"Cached evaluation: {key}")
    except Exception as e:
        logger.warning(f"Failed to cache evaluation: {e}")


def get_cached_evaluation(question: str, answer: str) -> Optional[dict]:
    """Return a cached evaluation dict or None."""
    client = get_redis_client()
    if client is None:
        return None
    key = _make_key("evaluation", question, answer[:200])
    try:
        data = client.get(key)
        if data:
            logger.debug(f"[CACHE HIT] Evaluation: {key}")
            return json.loads(data.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to read evaluation cache: {e}")
    return None


def flush_cache(pattern: str = "eval_gen:*") -> int:
    """Delete all keys matching pattern. Returns count deleted."""
    client = get_redis_client()
    if client is None:
        return 0
    keys = client.keys(pattern)
    if keys:
        return client.delete(*keys)
    return 0
