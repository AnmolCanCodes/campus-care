import os
import random
import re
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from ai import AIError, generate_complaint
from database import SessionLocal, ensure_schema, get_db
from mailer import build_mailto, compose_body

ensure_schema()

app = FastAPI(title="College Care")
app.mount("/static", StaticFiles(directory=BASE_DIR / "public" / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

CATEGORIES = [
    "Faculty", "Infrastructure", "Examination", "Fees",
    "Library", "Computer Lab", "Hostel", "Other",
]
SEMESTERS = list(range(1, 9))
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RANT_MAX = 1000
RANT_KINDS = ("rant", "confession")
PROMPTS = {
    "rant": [
        "The worst thing about this college is...",
        "Wi-Fi works everywhere except the room where I'm sitting.",
        "Nobody told us the timetable changed. Again.",
        "The canteen food deserves its own complaint.",
        "Attendance rules that nobody can explain...",
        "Results come out whenever they feel like it.",
        "The one class I dread every single week...",
        "Why is the one printer always out of paper?",
    ],
    "confession": [
        "I've been pretending to understand this subject all semester.",
        "The thing I've never told anyone at college is...",
        "I skipped a class to hide in the library and I'd do it again.",
        "I'm scared about placements and I haven't told anyone.",
        "I secretly enjoy a subject everyone else complains about.",
        "I signed attendance for a friend and I still feel weird about it.",
        "My biggest college secret is...",
        "I wish I had said this to a teacher...",
    ],
}


def prompts():
    out = {k: v[:] for k, v in PROMPTS.items()}
    for v in out.values():
        random.shuffle(v)
    return out


def recent_rants(limit: int = 20):
    """Short one-line versions of the newest posts, for the bottom ticker."""
    db = SessionLocal()
    try:
        rows = db.query(models.Rant).order_by(models.Rant.id.desc()).limit(limit).all()
        out = []
        for r in rows:
            text = " ".join(r.content.split())
            if len(text) > 110:
                text = text[:107].rstrip() + "..."
            out.append({"kind": r.kind or "rant", "text": text})
        return out
    except Exception:
        return []
    finally:
        db.close()


templates.env.globals["recent_rants"] = recent_rants


def hod_email() -> str:
    return os.getenv("HOD_EMAIL", "hod@example.com").strip()


def render(request: Request, name: str, status_code: int = 200, **context):
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def form_context(values=None, errors=None, ai_error=None):
    return {
        "values": values or {}, "errors": errors or {}, "ai_error": ai_error,
        "categories": CATEGORIES, "semesters": SEMESTERS,
    }


def validate(v: dict) -> dict:
    errors = {}
    if len(v["name"]) < 2:
        errors["name"] = "Enter your full name."
    if not v["roll_number"]:
        errors["roll_number"] = "Enter your roll number."
    if not v["course"]:
        errors["course"] = "Enter your course, for example BCA."
    if v["semester"] not in [str(s) for s in SEMESTERS]:
        errors["semester"] = "Choose your semester."
    if not EMAIL_RE.match(v["email"]):
        errors["email"] = "Enter a valid email address."
    if v["category"] not in CATEGORIES:
        errors["category"] = "Choose a category."
    if len(v["subject"]) < 5:
        errors["subject"] = "Give the complaint a short subject."
    if len(v["description"]) < 20:
        errors["description"] = "Describe the issue in a little more detail (at least 20 characters)."
    return errors


def compose_for(student: models.Student, result: dict) -> str:
    return compose_body(result["body"], student.name, student.roll_number,
                        student.course, student.semester)


# ---------- Home ----------
@app.get("/")
def home(request: Request):
    return render(request, "index.html", categories=CATEGORIES)


# ---------- Complaint form ----------
@app.get("/complaint")
def complaint_page(request: Request):
    return render(request, "complaint.html", **form_context())


@app.post("/complaint")
def complaint_submit(
    request: Request,
    name: str = Form(""), roll_number: str = Form(""), course: str = Form(""),
    semester: str = Form(""), email: str = Form(""), category: str = Form(""),
    subject: str = Form(""), description: str = Form(""),
    db: Session = Depends(get_db),
):
    values = {
        "name": " ".join(name.split()), "roll_number": roll_number.strip().upper(),
        "course": " ".join(course.split()), "semester": semester.strip(),
        "email": email.strip(), "category": category.strip(),
        "subject": " ".join(subject.split()), "description": description.strip(),
    }
    errors = validate(values)
    if errors:
        return render(request, "complaint.html", 422, **form_context(values, errors))

    # Call the AI first, so a failure never leaves half-saved records behind.
    try:
        result = generate_complaint(
            name=values["name"], roll_number=values["roll_number"], course=values["course"],
            semester=int(values["semester"]), category=values["category"],
            subject=values["subject"], description=values["description"],
        )
    except AIError as exc:
        return render(request, "complaint.html", 503, **form_context(values, ai_error=str(exc)))

    student = db.query(models.Student).filter_by(roll_number=values["roll_number"]).first()
    if student is None:
        student = models.Student(roll_number=values["roll_number"])
        db.add(student)
    student.name = values["name"]
    student.course = values["course"]
    student.semester = int(values["semester"])
    student.email = values["email"]
    db.flush()

    complaint = models.Complaint(
        student_id=student.id, category=values["category"], subject=values["subject"],
        description=values["description"], ai_subject=result["subject"],
        priority=result["priority"], ai_email=compose_for(student, result),
    )
    db.add(complaint)
    db.commit()
    return RedirectResponse(f"/result?id={complaint.id}", status_code=303)


# ---------- Regenerate ----------
@app.post("/generate")
def regenerate(request: Request, complaint_id: int = Form(...), db: Session = Depends(get_db)):
    complaint = db.get(models.Complaint, complaint_id)
    if complaint is None:
        return RedirectResponse("/complaint", status_code=303)
    s = complaint.student
    try:
        result = generate_complaint(
            name=s.name, roll_number=s.roll_number, course=s.course, semester=s.semester,
            category=complaint.category, subject=complaint.subject,
            description=complaint.description,
        )
    except AIError as exc:
        return show_result(request, complaint, error=str(exc), status_code=503)
    complaint.ai_subject = result["subject"]
    complaint.priority = result["priority"]
    complaint.ai_email = compose_for(s, result)
    db.commit()
    return RedirectResponse(f"/result?id={complaint.id}", status_code=303)


# ---------- Result ----------
def show_result(request, complaint, error=None, status_code=200):
    mailto = None
    if complaint is not None:
        mailto = build_mailto(hod_email(), complaint.ai_subject, complaint.ai_email)
    return render(request, "result.html", status_code, complaint=complaint,
                  hod_email=hod_email(), mailto=mailto, error=error)


@app.get("/result")
def result_page(request: Request, id: Optional[int] = None, db: Session = Depends(get_db)):
    complaint = db.get(models.Complaint, id) if id else None
    return show_result(request, complaint, status_code=200 if complaint else 404)


# ---------- Anonymous rants and confessions ----------
def rant_context(**extra):
    ctx = {"rant_max": RANT_MAX, "prompts": prompts(), "kind": "rant",
           "posted": False, "error": None, "content": ""}
    ctx.update(extra)
    return ctx


@app.get("/rantventkaro")
def rant_page(request: Request, posted: int = 0, kind: str = "rant"):
    kind = kind if kind in RANT_KINDS else "rant"
    return render(request, "rant.html", **rant_context(posted=bool(posted), kind=kind))


@app.post("/rantventkaro")
def rant_submit(request: Request, content: str = Form(""), kind: str = Form("rant"),
                db: Session = Depends(get_db)):
    kind = kind if kind in RANT_KINDS else "rant"
    text = content.strip()
    error = None
    if len(text) < 5:
        error = "Write a little more before posting."
    elif len(text) > RANT_MAX:
        error = f"That is over {RANT_MAX} characters. Trim it down or split it into two posts."
    if error:
        return render(request, "rant.html", 422, **rant_context(error=error, content=text, kind=kind))
    db.add(models.Rant(content=text, kind=kind))  # nothing else is stored with it
    db.commit()
    return RedirectResponse(f"/rantventkaro?posted=1&kind={kind}", status_code=303)


@app.get("/rants")
def rant_wall(request: Request, kind: Optional[str] = None, db: Session = Depends(get_db)):
    active = kind if kind in RANT_KINDS else None
    query = db.query(models.Rant)
    if active:
        query = query.filter(models.Rant.kind == active)
    rants = query.order_by(models.Rant.id.desc()).limit(300).all()
    return render(request, "rants.html", rants=rants, active=active)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", reload=True)