"""Background pre-generation and caching of Doc-folder questions.

On first import (at app startup), triggers a background thread to:
1. Read all documents in the Doc folder.
2. Generate questions via the AI and store them in doc_questions_cache.json.

A file watcher polls the Doc folder every 60 s and regenerates the cache when
a new file is detected, so adding a document at runtime is handled automatically.

Usage in app.py:
    import doc_question_cache
    doc_question_cache.start(DOCUMENTS_DIR)
    questions = doc_question_cache.get_questions(n=5)
"""

import json
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quiz_engine import generate_mixed_doc_questions, _question_hash  # noqa: E402
from runtime_paths import app_dir  # noqa: E402

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.join(app_dir(), "doc_questions_cache.json")
# Minimum pool size to keep in cache; regenerate when pool drops below this.
_MIN_POOL = 20
# How many questions to generate per refresh cycle.
_GENERATE_COUNT = 10
# Poll interval for the file watcher (seconds).
_POLL_INTERVAL = 60

_lock = threading.Lock()
_pool: list = []          # in-memory question pool
_known_files: set = set() # tracks Doc folder snapshot for change detection
_documents_dir: str = ""
_started = False


# ---------------------------------------------------------------------------
# Cache persistence
# ---------------------------------------------------------------------------

def _load_cache() -> list:
    if not os.path.exists(_CACHE_PATH):
        return []
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _save_cache(questions: list) -> None:
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("doc_question_cache: failed to save cache: %s", exc)


# ---------------------------------------------------------------------------
# Question pool management
# ---------------------------------------------------------------------------

def _doc_snapshot(documents_dir: str) -> set:
    """Return a frozenset of (filename, mtime) tuples for supported docs."""
    supported = (".pdf", ".xlsx")
    result = set()
    try:
        for fname in os.listdir(documents_dir):
            if os.path.splitext(fname)[1].lower() in supported and not fname.startswith("~$"):
                path = os.path.join(documents_dir, fname)
                try:
                    result.add((fname, os.path.getmtime(path)))
                except OSError:
                    pass
    except OSError:
        pass
    return result


def _dedup(existing: list, new_qs: list) -> list:
    """Return only questions from new_qs whose hash isn't already in existing."""
    seen = {_question_hash(q["question"]) for q in existing}
    unique = []
    for q in new_qs:
        h = _question_hash(q["question"])
        if h not in seen:
            seen.add(h)
            unique.append(q)
    return unique


def _refresh(force: bool = False) -> None:
    """Generate more questions and merge into the pool if needed."""
    global _pool, _known_files

    current_files = _doc_snapshot(_documents_dir)
    files_changed = current_files != _known_files

    with _lock:
        pool_size = len(_pool)

    if not force and not files_changed and pool_size >= _MIN_POOL:
        return  # nothing to do

    logger.info("doc_question_cache: refreshing (force=%s, files_changed=%s, pool=%d)",
                force, files_changed, pool_size)
    try:
        new_qs = generate_mixed_doc_questions(_documents_dir, num_questions=_GENERATE_COUNT)
    except Exception as exc:
        logger.warning("doc_question_cache: generation failed: %s", exc)
        return

    with _lock:
        unique = _dedup(_pool, new_qs)
        _pool.extend(unique)
        _known_files = current_files
        snapshot = list(_pool)

    _save_cache(snapshot)
    logger.info("doc_question_cache: pool now has %d questions (+%d new)", len(snapshot), len(unique))


def _watcher_loop() -> None:
    """Background thread: initial generation, then periodic watch."""
    _refresh(force=True)
    while True:
        time.sleep(_POLL_INTERVAL)
        _refresh()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start(documents_dir: str) -> None:
    """Call once at app startup to initialise the cache and start the watcher."""
    global _documents_dir, _pool, _started
    if _started:
        return
    _started = True
    _documents_dir = documents_dir

    # Load any previously cached questions immediately (zero startup latency).
    with _lock:
        _pool = _load_cache()
    logger.info("doc_question_cache: loaded %d cached questions from disk", len(_pool))

    t = threading.Thread(target=_watcher_loop, daemon=True, name="doc-q-cache-watcher")
    t.start()


def get_questions(n: int = 5) -> list:
    """Return up to `n` questions sampled from the pool without replacement.

    Falls back to live generation if the pool is empty (e.g. very first run
    before the background thread finishes).
    """
    import random
    with _lock:
        available = list(_pool)

    if len(available) >= n:
        return random.sample(available, n)

    # Pool too small — generate live (blocks, but only on very first request)
    logger.info("doc_question_cache: pool too small (%d), generating live", len(available))
    try:
        live = generate_mixed_doc_questions(_documents_dir, num_questions=n)
        if live:
            return live
    except Exception as exc:
        logger.warning("doc_question_cache: live fallback failed: %s", exc)

    # Return whatever we have
    return available[:n] if available else []
