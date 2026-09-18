import json
import random
import re
import os
import subprocess
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor

from runtime_paths import app_dir, secure_file
import secret_store

_ENV_PATH = os.path.join(app_dir(), ".env")
secure_file(_ENV_PATH)  # restrict .env (contains the API key) to this user only

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
except ImportError:
    pass  # dotenv optional; fall back to system env vars

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # PDF grounding disabled if pypdf isn't installed

# Cache of extracted document text, keyed by (path, mtime) so repeated quiz
# generations for the same topic don't re-parse the PDF every time.
_DOC_TEXT_CACHE = {}

# Persistent record of previously-asked questions (per topic+level), so a
# multi-hour event doesn't serve the same question to two different people.
_HISTORY_PATH = os.path.join(app_dir(), "question_history.json")
_HISTORY_CAP = 400  # oldest entries per topic+level are pruned past this
_HISTORY_HINT_COUNT = 15  # how many recent questions to show the AI as "don't repeat these"
_history_lock = threading.Lock()

# Bosch AOAI Farm connection settings (loaded from .env)
_AOAI_ENDPOINT = os.getenv("BOSCH_AOAI_ENDPOINT", "https://aoai-farm.bosch-temp.com/api")
_AOAI_MODEL    = os.getenv("BOSCH_AOAI_MODEL", "askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18")
_AOAI_VERSION  = os.getenv("BOSCH_AOAI_API_VERSION", "2024-08-01-preview")

# Stored "penc:"-encrypted in .env (see secret_store.portable_encrypt) — this is
# portable across machines/users by design, so a shared exe + .env just works.
_AOAI_KEY_RAW = os.getenv("BOSCH_AOAI_API_KEY", "")
_AOAI_KEY = secret_store.portable_decrypt(_AOAI_KEY_RAW)
if _AOAI_KEY_RAW and not _AOAI_KEY_RAW.startswith("penc:"):
    # One-time migration: encrypt a legacy plaintext key in place.
    _AOAI_KEY = _AOAI_KEY_RAW
    try:
        secret_store.set_env_value(_ENV_PATH, "BOSCH_AOAI_API_KEY", secret_store.portable_encrypt(_AOAI_KEY_RAW))
        secure_file(_ENV_PATH)
    except OSError:
        pass
# Optional explicit proxy override; set to empty string in .env to bypass system proxy
_AOAI_PROXY    = os.getenv("BOSCH_AOAI_PROXY", None)  # None = use system HTTP_PROXY

# API is available when a key is present (curl handles proxy auth transparently)
GENAI_AVAILABLE = bool(_AOAI_KEY)


def _call_aoai(messages, max_tokens=6000):
    """Call Bosch AOAI Farm via curl (handles NTLM proxy auth via Windows SSPI)."""
    if not _AOAI_KEY:
        raise RuntimeError(
            "BOSCH_AOAI_API_KEY is not set. "
            "Add it to a .env file or set it as an environment variable."
        )

    # BOSCH_AOAI_PROXY in .env overrides the system HTTP_PROXY/HTTPS_PROXY.
    # Set BOSCH_AOAI_PROXY= (empty) in .env to disable proxy entirely.
    if _AOAI_PROXY is None:
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY", "")
    else:
        proxy = _AOAI_PROXY
    url = f"{_AOAI_ENDPOINT}/openai/deployments/{_AOAI_MODEL}/chat/completions?api-version={_AOAI_VERSION}"
    body = json.dumps({"messages": messages, "max_tokens": max_tokens})

    cmd = ["curl", "-s", "--show-error"]
    if proxy:
        cmd += ["--proxy", proxy.strip(), "--proxy-anyauth", "--proxy-user", ":"]
    else:
        # Prevent curl from picking up HTTP_PROXY/HTTPS_PROXY system env vars
        cmd += ["--noproxy", "*"]
    cmd += [
        "-X", "POST", url,
        "-H", "Content-Type: application/json",
        "-H", f"genaiplatform-farm-subscription-key: {_AOAI_KEY}",
        "-d", body,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise RuntimeError(
            "curl is not installed or not on PATH. "
            "Install curl or add it to your system PATH."
        )

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"curl failed: {detail}")

    if not result.stdout.strip():
        raise RuntimeError("curl returned an empty response. Check network connectivity and proxy settings.")

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from API: {exc}\nResponse: {result.stdout[:500]}")

    if "error" in response:
        raise RuntimeError(f"API error: {response['error']}")
    return response["choices"][0]["message"]["content"]

from database import SKILL_LEVELS

TIMER_CONFIG = {
    # level: seconds per MCQ question (challenging questions need more time)
    1: {"mcq": 45},   # Beginner  → 15 q × 45s  = ~11 min
    2: {"mcq": 60},   # Moderate  → 15 q × 60s  = 15 min
    3: {"mcq": 75},   # Intermediate → 15 q × 75s = ~19 min
    4: {"mcq": 90},   # Expert    → 15 q × 90s  = ~22 min
}

PASS_PERCENTAGE = 80  # >=80% to pass


def get_quiz_timer(level, questions):
    """Calculate total quiz time based on question types and difficulty."""
    config = TIMER_CONFIG.get(level, TIMER_CONFIG[1])
    total = 0
    for q in questions:
        qtype = q.get("type", "mcq")
        total += config.get(qtype, 60)
    return total


def _find_topic_document(topic, documents_dir):
    """Return the path of a reference document matching `topic`, if one exists.

    Filenames are matched against the topic name with spaces/punctuation
    stripped (e.g. "CAN FD" -> "canfd.pdf", "FlexRay" -> "flexray.pdf").
    """
    if not documents_dir or not os.path.isdir(documents_dir):
        return None

    normalized_topic = re.sub(r"[^a-z0-9]", "", topic.lower())
    for fname in os.listdir(documents_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() != ".pdf":
            continue
        normalized_stem = re.sub(r"[^a-z0-9]", "", stem.lower())
        if normalized_stem == normalized_topic:
            return os.path.join(documents_dir, fname)
    return None


def _extract_pdf_text(path, max_chars=4000):
    """Extract text from a PDF, cached by (path, mtime). Returns "" on failure."""
    if PdfReader is None:
        return ""

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return ""

    cache_key = (path, mtime)
    if cache_key in _DOC_TEXT_CACHE:
        return _DOC_TEXT_CACHE[cache_key]

    text = ""
    try:
        reader = PdfReader(path)
        parts = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(parts).strip()[:max_chars]
    except Exception:
        text = ""

    _DOC_TEXT_CACHE[cache_key] = text
    return text


def generate_quiz_with_ai(topic, level, num_questions=20, single_batch=False, documents_dir=None):
    """Generate quiz questions using Bosch AOAI Farm.

    Splits the request into small chunks generated concurrently, so wall-clock
    time stays close to a single small chunk's latency regardless of num_questions.
    `single_batch` is kept for backward compatibility and no longer changes behavior.

    If `documents_dir` is given and contains a reference document for `topic`
    (e.g. documents/can.pdf for topic "CAN"), questions are grounded in that
    document's content first; otherwise questions are generated from general
    knowledge.

    Questions already served for this topic+level (tracked in a local history
    file) are filtered out and re-requested, so long-running multi-person
    events don't repeat the same question.
    """
    level_name = SKILL_LEVELS.get(level, "Beginner")

    document_text = ""
    doc_path = _find_topic_document(topic, documents_dir)
    if doc_path:
        document_text = _extract_pdf_text(doc_path)

    history_key = f"{topic}|{level_name}"
    with _history_lock:
        history = _load_history()
    entries = history.get(history_key, [])
    seen_hashes = {e["h"] for e in entries}
    avoid_questions = [e["q"] for e in entries[-_HISTORY_HINT_COUNT:]]

    # Split into small chunks and fire them at AOAI concurrently — wall-clock time
    # is then bounded by one small chunk's latency (~5-10s) instead of a single
    # large request that has to generate all questions serially (~30s+).
    chunk_size = 2

    def _request_batch(count):
        num_chunks = (count + chunk_size - 1) // chunk_size
        chunk_sizes = [chunk_size] * (num_chunks - 1) + [count - chunk_size * (num_chunks - 1)]
        results = []
        last_exc = None
        with ThreadPoolExecutor(max_workers=num_chunks) as pool:
            futures = [
                pool.submit(_generate_with_aoai, topic, level_name, size, document_text, avoid_questions)
                for size in chunk_sizes
            ]
            for future in futures:
                try:
                    results.extend(future.result())
                except Exception as exc:
                    last_exc = exc  # a failed chunk shouldn't sink the whole quiz
        if not results and last_exc is not None:
            raise last_exc
        return results

    unique_questions = []
    seen_this_run = set(seen_hashes)
    remaining = num_questions
    attempts = 0
    while remaining > 0 and attempts < 4:
        attempts += 1
        for q in _request_batch(remaining):
            q_hash = _question_hash(q["question"])
            if q_hash in seen_this_run:
                continue
            seen_this_run.add(q_hash)
            q["_hash"] = q_hash
            unique_questions.append(q)
        remaining = num_questions - len(unique_questions)

    if len(unique_questions) < 5:
        raise ValueError(f"Only {len(unique_questions)} valid questions generated")

    final = unique_questions[:num_questions]

    with _history_lock:
        history = _load_history()
        entries = history.get(history_key, [])
        entries.extend({"h": q["_hash"], "q": q["question"]} for q in final)
        history[history_key] = entries[-_HISTORY_CAP:]
        _save_history(history)

    for q in final:
        q.pop("_hash", None)

    return final


def generate_mixed_ai_questions(topic, num_questions=5):
    """Generate `num_questions` MCQs in one API call with mixed difficulty levels.

    Distribution for 5 questions: 1 Beginner, 1 Moderate, 1 Intermediate, 1 Expert,
    1 Real-Time Scenario. The prompt instructs the model to label each question with
    its intended difficulty so the single batch covers all tiers.
    """
    prompt = f"""Generate exactly {num_questions} multiple-choice questions for the topic "{topic}".
Use this exact difficulty distribution (one question per level, in this order):
1. Beginner — a foundational concept question
2. Moderate — a scenario with a tricky edge case
3. Intermediate — an advanced concept or design decision
4. Expert — deep internals, performance trade-offs, or obscure real-world edge case
5. Real-Time Scenario — a concrete, practical situation a professional might face on the job (debugging, system design, production incident, tool choice)

Return ONLY a valid JSON array of exactly {num_questions} objects. No explanation, no markdown, no extra text.
Ensure all strings are properly JSON-escaped.

Each object must have:
- "type": "mcq"
- "question": the question text
- "options": array of exactly 4 plausible answer options
- "answer": index (0-3) of the correct answer

Example:
[
  {{"type": "mcq", "question": "What is X?", "options": ["A", "B", "C", "D"], "answer": 0}}
]
"""
    max_tokens = max(300, num_questions * 350)
    text = _call_aoai([{"role": "user", "content": prompt}], max_tokens=max_tokens).strip()
    questions = _parse_questions_json(text)
    validated = []
    for q in questions:
        q["type"] = "mcq"
        if all(k in q for k in ("question", "options", "answer")):
            if isinstance(q["options"], list) and len(q["options"]) == 4:
                if isinstance(q["answer"], int) and 0 <= q["answer"] <= 3:
                    validated.append(q)
    return validated


def generate_mixed_doc_questions(documents_dir, num_questions=5):
    """Generate `num_questions` MCQs from docs in one API call with mixed difficulty."""
    combined_text = _extract_all_docs_text(documents_dir)
    if not combined_text:
        return []
    prompt = f"""Generate exactly {num_questions} multiple-choice questions grounded in the reference material below.
Use this exact difficulty distribution (one question per level, in this order):
1. Beginner — a foundational concept from the material
2. Moderate — a scenario with a tricky edge case from the material
3. Intermediate — an advanced concept or design decision from the material
4. Expert — deep or obscure detail from the material
5. Real-Time Scenario — a concrete practical situation based on the material

REFERENCE MATERIAL:
\"\"\"
{combined_text[:4000]}
\"\"\"

Return ONLY a valid JSON array of exactly {num_questions} objects. No explanation, no markdown, no extra text.
Ensure all strings are properly JSON-escaped.

Each object must have:
- "type": "mcq"
- "question": the question text
- "options": array of exactly 4 plausible answer options
- "answer": index (0-3) of the correct answer
"""
    max_tokens = max(300, num_questions * 350)
    text = _call_aoai([{"role": "user", "content": prompt}], max_tokens=max_tokens).strip()
    questions = _parse_questions_json(text)
    validated = []
    for q in questions:
        q["type"] = "mcq"
        if all(k in q for k in ("question", "options", "answer")):
            if isinstance(q["options"], list) and len(q["options"]) == 4:
                if isinstance(q["answer"], int) and 0 <= q["answer"] <= 3:
                    validated.append(q)
    return validated


def generate_realtime_scenario_questions(topic, num_questions=2):
    """Generate real-world scenario-based MCQ questions for `topic`."""
    prompt = f"""Generate exactly {num_questions} real-time scenario-based multiple-choice questions for the topic "{topic}".

Each question must describe a concrete, realistic situation a practitioner might face (e.g. debugging, system design decision, production incident, choosing the right tool). The question should require applying knowledge, not just recalling facts.

Return ONLY a valid JSON array. No explanation, no markdown, no extra text.
Ensure all strings are properly JSON-escaped.

Each question must have:
- "type": "mcq"
- "question": the scenario question text
- "options": array of exactly 4 answer options (make distractors plausible)
- "answer": index (0-3) of the correct answer

Example:
[
  {{"type": "mcq", "question": "Your RAG pipeline returns stale answers after documents are updated. What is the most likely cause?", "options": ["Embedding model changed", "Index not refreshed after document update", "Retriever top-k set too low", "LLM context window exceeded"], "answer": 1}}
]
"""
    max_tokens = min(1500, max(300, num_questions * 180))
    text = _call_aoai([{"role": "user", "content": prompt}], max_tokens=max_tokens).strip()
    questions = _parse_questions_json(text)
    validated = []
    for q in questions:
        q["type"] = "mcq"
        if all(k in q for k in ("question", "options", "answer")):
            if isinstance(q["options"], list) and len(q["options"]) == 4:
                if isinstance(q["answer"], int) and 0 <= q["answer"] <= 3:
                    validated.append(q)
    return validated


def generate_realtime_scenario_questions_from_docs(documents_dir, num_questions=1):
    """Generate real-time scenario MCQs grounded in the PDFs in documents_dir."""
    combined_text = _extract_all_docs_text(documents_dir)
    if not combined_text:
        return []
    prompt = f"""Generate exactly {num_questions} real-time scenario-based multiple-choice questions grounded in the reference material below.

Each question must describe a realistic, practical situation a professional might face. Require applied thinking, not just recall.

REFERENCE MATERIAL:
\"\"\"
{combined_text[:3000]}
\"\"\"

Return ONLY a valid JSON array. No explanation, no markdown, no extra text.
Ensure all strings are properly JSON-escaped.

Each question must have:
- "type": "mcq"
- "question": the scenario question text
- "options": array of exactly 4 plausible answer options
- "answer": index (0-3) of the correct answer
"""
    max_tokens = min(1500, max(300, num_questions * 180))
    text = _call_aoai([{"role": "user", "content": prompt}], max_tokens=max_tokens).strip()
    questions = _parse_questions_json(text)
    validated = []
    for q in questions:
        q["type"] = "mcq"
        if all(k in q for k in ("question", "options", "answer")):
            if isinstance(q["options"], list) and len(q["options"]) == 4:
                if isinstance(q["answer"], int) and 0 <= q["answer"] <= 3:
                    validated.append(q)
    return validated


def _normalize_question_text(text):
    """Collapse case/punctuation/whitespace differences so near-identical
    questions hash the same way."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _question_hash(text):
    return hashlib.sha1(_normalize_question_text(text).encode("utf-8")).hexdigest()


def _load_history():
    if not os.path.exists(_HISTORY_PATH):
        return {}
    try:
        with open(_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_history(history):
    try:
        with open(_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f)
        secure_file(_HISTORY_PATH)
    except OSError:
        pass


def _generate_with_aoai(topic, level_name, num_questions, document_text="", avoid_questions=None):
    """Generate a batch of MCQ questions using Bosch AOAI Farm (Azure OpenAI)."""

    if document_text:
        source_instructions = f"""Base the questions primarily on the reference material below. Only use
your general knowledge of "{topic}" to fill gaps where the material is insufficient.

REFERENCE MATERIAL:
\"\"\"
{document_text}
\"\"\"
"""
    else:
        source_instructions = f'No reference material is available for "{topic}", so use your general knowledge.'

    avoid_block = ""
    if avoid_questions:
        bullet_list = "\n".join(f"- {q}" for q in avoid_questions)
        avoid_block = f"""

Do NOT repeat or closely paraphrase any of these previously used questions:
{bullet_list}
"""

    prompt = f"""Generate exactly {num_questions} challenging multiple-choice quiz questions for the topic "{topic}" at {level_name} difficulty level.

{source_instructions}
{avoid_block}
IMPORTANT difficulty guidelines:
- Beginner: avoid trivial syntax questions; focus on concepts and common pitfalls
- Moderate: scenario-based questions, tricky edge cases
- Intermediate: advanced concepts, subtle behavior, design decisions
- Expert: deep internals, performance trade-offs, obscure but real-world edge cases

Avoid overly simple or basic recall questions. Prefer questions that require reasoning.

Return ONLY a valid JSON array. No explanation, no markdown, no extra text.
Ensure all strings are properly JSON-escaped (no unescaped double quotes inside strings).

Each question must have:
- "type": "mcq"
- "question": the question text
- "options": array of exactly 4 answer options (make distractors plausible)
- "answer": index (0-3) of the correct answer

Example:
[
  {{"type": "mcq", "question": "What is X?", "options": ["A", "B", "C", "D"], "answer": 0}}
]
"""
    # Cap tokens to what's actually needed for this batch size — smaller requests
    # finish faster than always asking for the full 6000-token budget.
    max_tokens = min(1500, max(300, num_questions * 180))
    text = _call_aoai([{"role": "user", "content": prompt}], max_tokens=max_tokens).strip()

    questions = _parse_questions_json(text)

    # Validate structure (MCQ only)
    validated = []
    for q in questions:
        q["type"] = "mcq"
        if all(k in q for k in ("question", "options", "answer")):
            if isinstance(q["options"], list) and len(q["options"]) == 4:
                if isinstance(q["answer"], int) and 0 <= q["answer"] <= 3:
                    validated.append(q)

    return validated


def _parse_questions_json(text):
    """Parse question JSON robustly, falling back to per-object extraction on failure."""
    # Try the full array first
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    raw = json_match.group() if json_match else text

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Truncation recovery: trim to last complete object
    try:
        last_brace = raw.rfind('}')
        if last_brace != -1:
            return json.loads(raw[:last_brace + 1] + "]")
    except json.JSONDecodeError:
        pass

    # Last resort: extract each {...} block individually and parse one by one
    questions = []
    for match in re.finditer(r'\{[^{}]*\}', text, re.DOTALL):
        try:
            q = json.loads(match.group())
            questions.append(q)
        except json.JSONDecodeError:
            continue
    return questions


def _extract_all_docs_text(documents_dir, max_chars_per_doc=3000, max_docs=5):
    """Return combined text from a random sample of PDFs in documents_dir."""
    if PdfReader is None or not documents_dir or not os.path.isdir(documents_dir):
        return ""
    all_pdfs = [f for f in os.listdir(documents_dir) if f.lower().endswith(".pdf")]
    sampled = random.sample(all_pdfs, min(max_docs, len(all_pdfs)))
    parts = []
    for fname in sampled:
        path = os.path.join(documents_dir, fname)
        text = _extract_pdf_text(path, max_chars=max_chars_per_doc)
        if text:
            stem = os.path.splitext(fname)[0]
            parts.append(f"=== {stem} ===\n{text}")
    return "\n\n".join(parts)


def generate_questions_from_docs(documents_dir, level, num_questions=5, avoid_questions=None):
    """Generate MCQ questions grounded entirely in the PDFs found in documents_dir.

    Questions are generated at the given difficulty level and avoid any stems
    listed in avoid_questions (to prevent overlap with the AI-topic batch).
    """
    level_name = SKILL_LEVELS.get(level, "Beginner")
    combined_text = _extract_all_docs_text(documents_dir)
    if not combined_text:
        raise ValueError("No readable PDF content found in the documents folder.")

    history_key = f"__docs__|{level_name}"
    with _history_lock:
        history = _load_history()
    entries = history.get(history_key, [])
    seen_hashes = {e["h"] for e in entries}
    doc_avoid = [e["q"] for e in entries[-_HISTORY_HINT_COUNT:]]
    if avoid_questions:
        doc_avoid = list(avoid_questions) + doc_avoid

    chunk_size = 2

    def _request_batch(count):
        num_chunks = (count + chunk_size - 1) // chunk_size
        chunk_sizes = [chunk_size] * (num_chunks - 1) + [count - chunk_size * (num_chunks - 1)]
        results = []
        last_exc = None
        with ThreadPoolExecutor(max_workers=num_chunks) as pool:
            futures = [
                pool.submit(_generate_with_aoai, "the provided documents", level_name, size, combined_text, doc_avoid)
                for size in chunk_sizes
            ]
            for future in futures:
                try:
                    results.extend(future.result())
                except Exception as exc:
                    last_exc = exc
        if not results and last_exc is not None:
            raise last_exc
        return results

    unique_questions = []
    seen_this_run = set(seen_hashes)
    remaining = num_questions
    attempts = 0
    while remaining > 0 and attempts < 4:
        attempts += 1
        for q in _request_batch(remaining):
            q_hash = _question_hash(q["question"])
            if q_hash in seen_this_run:
                continue
            seen_this_run.add(q_hash)
            q["_hash"] = q_hash
            unique_questions.append(q)
        remaining = num_questions - len(unique_questions)

    final = unique_questions[:num_questions]

    with _history_lock:
        history = _load_history()
        entries = history.get(history_key, [])
        entries.extend({"h": q["_hash"], "q": q["question"]} for q in final)
        history[history_key] = entries[-_HISTORY_CAP:]
        _save_history(history)

    for q in final:
        q.pop("_hash", None)

    return final


def configure_aoai(api_key):
    """Update the API key used for Bosch AOAI Farm calls."""
    global _AOAI_KEY, GENAI_AVAILABLE
    _AOAI_KEY = api_key
    GENAI_AVAILABLE = bool(api_key)
    return True


def persist_api_key(api_key):
    """Configure the key for this session AND save it to .env, portably
    encrypted so it stays readable on any machine the exe/.env is shared to.
    """
    configure_aoai(api_key)
    secret_store.set_env_value(_ENV_PATH, "BOSCH_AOAI_API_KEY", secret_store.portable_encrypt(api_key))
    secure_file(_ENV_PATH)
    return True


# Backward-compatible alias
configure_gemini = configure_aoai


