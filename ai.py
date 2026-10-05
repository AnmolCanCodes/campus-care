import json
import os
import re
from typing import Dict

from openai import (
    APIConnectionError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)


class AIError(Exception):
    """Raised with a message that is safe to show to the student."""


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

Reply with JSON only, using exactly these keys: "subject", "priority", "body"."""

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


def generate_complaint(
    *, name: str, roll_number: str, course: str, semester: int,
    category: str, subject: str, description: str,
) -> Dict[str, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        raise AIError("The AI service is not set up yet. Add your OPENAI_API_KEY to the .env file.")

    client = OpenAI(api_key=api_key, timeout=40.0, max_retries=1)
    user_message = (
        f"Student: {name}, {course}, semester {semester}\n"
        f"Category: {category}\n"
        f"Student's own subject: {subject}\n"
        f"Student's description:\n{description}"
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except AuthenticationError as exc:
        raise AIError("The AI service rejected the API key. Check OPENAI_API_KEY in .env.") from exc
    except RateLimitError as exc:
        raise AIError("The AI service is busy or out of quota. Try again in a minute.") from exc
    except APIConnectionError as exc:
        raise AIError("We couldn't reach the AI service. Check your connection and try again.") from exc
    except OpenAIError as exc:
        raise AIError("The AI service returned an error. Please try again.") from exc

    try:
        data = json.loads(response.choices[0].message.content or "")
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