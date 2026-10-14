# College Complaint & Issue Management System

A simple AI-powered web application that allows college students to submit complaints, generate professional complaint emails using AI, and send them to the concerned college authority.

The project is designed as a BCA Minor Project and focuses on solving a practical college communication problem while keeping the system simple and easy to use.

## Features

### 1. Student Information

Students provide basic information before submitting a formal complaint:

* Name
* Roll Number
* Course
* Semester
* Email

The information is stored in a SQLite database and is associated with the submitted complaint.

### 2. Complaint Submission

Students can submit complaints related to different college issues, such as:

* Faculty
* Infrastructure
* Examination
* Fees
* Library
* Computer Lab
* Hostel
* Other college-related issues

Students can provide a subject and describe their problem in their own words.

### 3. AI-Powered Complaint Generation

The system uses an LLM to analyze the student's complaint.

The AI generates:

* A professional subject
* Suggested priority
* A professionally written complaint email

The AI does not replace the student's original complaint. It converts the student's description into a clearer and more professional format.

### 4. Priority Detection

The AI suggests a complaint priority:

* Low
* Medium
* High

The priority is only a suggestion and the student can review the generated complaint before sending it.

### 5. Send Complaint to HOD

After reviewing the generated complaint, the student can click the "Send to HOD" button.

The application opens the student's email client with:

* HOD email address
* Generated subject
* Generated complaint body

already filled in.

The student can review the email and manually send it.

The application does not require Gmail API or Google OAuth.

### 6. Complaint Storage

Complaint information is stored in a local SQLite database.

Stored information includes:

* Student information
* Complaint category
* Complaint subject
* Complaint description
* AI-generated priority
* AI-generated email
* Submission date and time

### 7. Anonymous Rant & Vent

The project also contains a hidden anonymous page available at:

`/rantventkaro`

This page allows students to express their feelings, frustrations, opinions, or experiences related to college.

No student information is attached to these posts.

The feature is intentionally separated from the formal complaint system.

Example:

> Why do assignments always arrive one day before the deadline?

Rants are stored without name, roll number, or email.

## Project Workflow

### Formal Complaint

```text
Student
   |
   v
Student Information
   |
   v
Complaint Form
   |
   v
FastAPI Backend
   |
   +-------> SQLite Database
   |
   v
LLM API
   |
   v
Professional Complaint
   |
   v
Student Reviews Complaint
   |
   v
Email Client
   |
   v
HOD

## Technology Stack

### Backend

* Python
* FastAPI
* Uvicorn

### Frontend

* HTML
* CSS
* JavaScript
* Jinja2 Templates

### Database

* SQLite
* SQLAlchemy

### Artificial Intelligence

* LLM API
* AI is used for complaint analysis and professional email generation.

### Environment Configuration

* python-dotenv

## Project Structure

```text
college-complaint-system/
│
├── app.py
├── database.py
├── models.py
├── ai.py
├── requirements.txt
├── README.md
├── .env
├── database.db
│
├── templates/
│   ├── index.html
│   ├── complaint.html
│   ├── result.html
│   └── rant.html
│
└── static/
    ├── style.css
    └── script.js
```

## Database Structure

### Students Table

```text
students
----------------
id
name
roll_number
course
semester
email
```

### Complaints Table

```text
complaints
----------------
id
student_id
category
subject
description
priority
ai_email
created_at
```

### Rants Table

```text
rants
----------------
id
content
created_at
```

The Rants table does not contain student information.

## Installation

Clone or download the project.

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on Linux/macOS:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_api_key_here
HOD_EMAIL=hod@example.com
```

Do not commit `.env` to GitHub.

Add it to `.gitignore`:

```text
.env
venv/
__pycache__/
database.db
```

## Running the Application

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

Open the application in the browser:

```text
http://127.0.0.1:8000
```

The anonymous Rant & Vent page is available at:

```text
http://127.0.0.1:8000/rantventkaro
```

## Main API Routes

### Home

```text
GET /
```

Displays the main application page.

### Complaint

```text
GET /complaint
POST /complaint
```

Displays and processes the complaint form.

### AI Generation

```text
POST /generate
```

Sends the complaint information to the LLM and generates a professional complaint.

### Result

```text
GET /result
```

Displays the generated complaint and provides the option to send it through email.

### Rant & Vent

```text
GET /rantventkaro
POST /rantventkaro
```

Displays the anonymous rant page and stores submitted rants.

## Email Workflow

The application does not directly send emails through the Gmail API.

Instead, it generates a `mailto:` link containing:

```text
Recipient
Subject
Email Body
```

When the student clicks "Send to HOD", their default email client opens with the generated email.

The student remains responsible for reviewing and sending the email.

## AI Workflow

The student first writes the complaint in their own words.

For example:

```text
The computers in our lab are not working and
we have to share one computer between multiple
students during practical classes.
```

The backend sends the complaint to the LLM with instructions to:

1. Understand the complaint.
2. Generate a professional subject.
3. Suggest a priority.
4. Write a professional email.
5. Preserve the original facts.
6. Avoid inventing information.

The generated response is then shown to the student.

## Privacy

The formal complaint system stores the student information required for the complaint.

The Rant & Vent feature does not intentionally associate a rant with:

* Student name
* Roll number
* Course
* Semester
* Email

Students should not submit passwords, personal information, or sensitive information in anonymous rants.

## Objective

The main objective of this project is to provide students with a simple platform to communicate college-related issues in a structured and professional manner.

The AI component helps students transform informal descriptions into professional complaint emails, while the anonymous Rant & Vent feature provides a separate space for students to express their feelings.

## Disclaimer

This project is created for educational purposes as a BCA Minor Project.

AI-generated complaints should always be reviewed by the student before being sent to any college authority.
