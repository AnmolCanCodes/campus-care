from urllib.parse import quote


def compose_body(body: str, name: str, roll_number: str, course: str, semester: int) -> str:
    """Attach the student's details as the sign-off of the AI-written body."""
    return f"{body}\n\nRegards,\n{name}\nRoll No: {roll_number}\n{course}, Semester {semester}"


def build_mailto(to: str, subject: str, body: str) -> str:
    """Build a mailto: link that opens the student's own email app, pre-filled."""
    body = body.replace("\r\n", "\n").replace("\n", "\r\n")
    return f"mailto:{to}?subject={quote(subject, safe='')}&body={quote(body, safe='')}"