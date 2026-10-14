import json
import os
import re
from typing import Dict

import httpx


class AIError(Exception):
    """Raised with a message that is safe to show to the student."""


HF_URL = "https://router.huggingface.co/v1/chat/completions"

SYSTEM_PROMPT = """You help college students turn informal complaints into clear, formal emails \
addressed to the Head of Department (HOD).

Rules:
1. Understand the student's complaint and keep every fact they gave.
2. Never invent names, dates, numbers, places or events that the student did not mention.
3. Write a short, professional subject line (under 90 characters).
4. Suggest a priority: "Low" (minor inconvenience), "Medium" (recurring problem that disrupts \
studies), or "High" (safety risk, an exam/fee/deadline at stake, or a complete breakdown affecting \
many students).
5. Write the email body in a polite, formal tone. Start with "Respected Sir/Madam," and end \
with a polite closing request for action. Do NOT add a sign-off, name, or roll number: \
the application adds those.
6. Keep the body between 80 and 220 words.

Reply with one JSON object and nothing else (no markdown, no code fences, no explanation), \
using exactly these keys: "subject", "priority", "body"."""

_SIGNOFF = re.compile(
    r"^(regards|warm regards|best regards|yours\s+\w+|sincerely|respectfully)[,.]?$", re.I
)


def _strip_signoff(body: str) -> str:
    """Remove a sign-off the model added anyway; the app appends the real one."""
    lines = body.rstrip().splitlines()
    for i in range(len(lines) - 1, max(len(lines) - 7, -1), -1):
        if _SIGNOFF.match(lines[i].strip()):
            return "\n".join(lines[:i]).rstrip()
    return body.strip()


def _parse_json(text: str) -> dict:
    """Open models sometimes wrap JSON in <think> blocks or code fences. Dig it out."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(text[start:end + 1], strict=False)


def generate_complaint(
    *, name: str, roll_number: str, course: str, semester: int,
    category: str, subject: str, description: str,
) -> Dict[str, str]:
    token = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or "").strip()
    if not token or token.startswith("your_"):
        raise AIError("The AI service is not set up yet. Add your HF_TOKEN to the .env file.")
    model = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct").strip()

    user_message = (
        f"Student: {name}, {course}, semester {semester}\n"
        f"Category: {category}\n"
        f"Student's own subject: {subject}\n"
        f"Student's description:\n{description}"
    )
    payload = {
        "model": model,
        "temperature": 0.3,
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    }

    try:
        resp = httpx.post(
            HF_URL, json=payload, headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(28.0, connect=8.0),
        )
    except httpx.TimeoutException as exc:
        raise AIError("The AI service took too long to answer. Please try again.") from exc
    except httpx.HTTPError as exc:
        raise AIError("We couldn't reach the AI service. Check your connection and try again.") from exc

    if resp.status_code in (401, 403):
        raise AIError("The AI service rejected the token. Check HF_TOKEN and its permissions.")
    if resp.status_code == 429:
        raise AIError("The AI service is busy or the free quota is used up. Try again later.")
    if resp.status_code in (400, 404):
        raise AIError(f"The model \"{model}\" isn't available. Set a different HF_MODEL in the settings.")
    if resp.status_code >= 400:
        raise AIError("The AI service returned an error. Please try again.")

    try:
        content = resp.json()["choices"][0]["message"]["content"] or ""
        data = _parse_json(content)
        ai_subject = str(data["subject"]).strip()
        body = _strip_signoff(str(data["body"]))
        priority = str(data["priority"]).strip().capitalize()
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise AIError("The AI reply was incomplete. Please try again.") from exc

    if not ai_subject or not body:
        raise AIError("The AI reply was incomplete. Please try again.")
    if priority not in ("Low", "Medium", "High"):
        priority = "Medium"

    return {"subject": ai_subject[:200], "priority": priority, "body": body}