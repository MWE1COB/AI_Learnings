import json
import random
import re
import os
import subprocess
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional; fall back to system env vars

# Bosch AOAI Farm connection settings (loaded from .env)
_AOAI_ENDPOINT = os.getenv("BOSCH_AOAI_ENDPOINT", "https://aoai-farm.bosch-temp.com/api")
_AOAI_MODEL    = os.getenv("BOSCH_AOAI_MODEL", "askbosch-prod-farm-openai-gpt-4o-mini-2024-07-18")
_AOAI_VERSION  = os.getenv("BOSCH_AOAI_API_VERSION", "2024-08-01-preview")
_AOAI_KEY      = os.getenv("BOSCH_AOAI_API_KEY", "")

# API is available when a key is present (curl handles proxy auth transparently)
GENAI_AVAILABLE = bool(_AOAI_KEY)


def _call_aoai(messages, max_tokens=6000):
    """Call Bosch AOAI Farm via curl (handles NTLM proxy auth via Windows SSPI)."""
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY", "")
    url = f"{_AOAI_ENDPOINT}/openai/deployments/{_AOAI_MODEL}/chat/completions?api-version={_AOAI_VERSION}"
    body = json.dumps({"messages": messages, "max_tokens": max_tokens})

    cmd = ["curl", "-s"]
    if proxy:
        cmd += ["--proxy", proxy, "--proxy-ntlm", "--proxy-user", ":"]
    cmd += [
        "-X", "POST", url,
        "-H", "Content-Type: application/json",
        "-H", f"genaiplatform-farm-subscription-key: {_AOAI_KEY}",
        "-d", body,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    response = json.loads(result.stdout)
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


def generate_quiz_with_ai(topic, level, num_questions=20):
    """Generate quiz questions using Bosch AOAI Farm in two batches for reliability."""
    level_name = SKILL_LEVELS.get(level, "Beginner")

    batch_size = (num_questions + 1) // 2  # e.g. 10 for 20 questions
    all_questions = []

    for _ in range(2):
        batch = _generate_with_aoai(topic, level_name, batch_size)
        all_questions.extend(batch)
        if len(all_questions) >= num_questions:
            break

    if len(all_questions) < 5:
        raise ValueError(f"Only {len(all_questions)} valid questions generated across batches")

    return all_questions[:num_questions]


def _generate_with_aoai(topic, level_name, num_questions):
    """Generate a batch of MCQ questions using Bosch AOAI Farm (Azure OpenAI)."""

    prompt = f"""Generate exactly {num_questions} challenging multiple-choice quiz questions for the topic "{topic}" at {level_name} difficulty level.

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
    text = _call_aoai([{"role": "user", "content": prompt}]).strip()

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


def configure_aoai(api_key):
    """Update the API key used for Bosch AOAI Farm calls."""
    global _AOAI_KEY, GENAI_AVAILABLE
    _AOAI_KEY = api_key
    GENAI_AVAILABLE = bool(api_key)
    return True


# Backward-compatible alias
configure_gemini = configure_aoai


