# 🚀 Employee Attendance & Analytics API

<p align="center">

  **A FastAPI + MongoDB backend for employee attendance management and workforce analytics**

  ![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
  ![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
  ![Status](https://img.shields.io/badge/Project-Backend%20API-6C63FF?style=for-the-badge)

</p>

---

## 📌 Project Overview

The **Employee Attendance & Analytics API** is a Python backend developed for the HROne Software Engineer Trainee technical assignment.

Built using **FastAPI and MongoDB**, the application supports employee management, attendance punch-in and punch-out, manual attendance corrections with an audit trail, and analytics powered by MongoDB aggregation pipelines.

### ✨ Key Highlights

- 👥 Employee creation and listing
- 🕒 Attendance punch-in and punch-out with business rules
- 📝 Manual attendance regularization and audit tracking
- 📊 Monthly employee attendance analytics
- 🏢 Department-wise attendance summaries
- 🏆 Late-arrival leaderboard
- 📈 Department attendance trends
- 🔍 MongoDB execution-statistics explain endpoint
- ⚡ Database indexes for uniqueness and query performance

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Backend programming |
| FastAPI | REST API framework |
| MongoDB 6.0+ | NoSQL database |
| PyMongo | MongoDB connectivity and queries |
| Pydantic | Request validation and data models |
| Uvicorn | ASGI application server |
| Git & GitHub | Version control and repository hosting |

> **Database recommendation:** MongoDB 7.0 is recommended for closer compatibility with the assignment grader.

---

## 📋 Prerequisites

Before running the application, install:

- Python 3.11 or newer
- MongoDB 6.0 or newer, locally or through MongoDB Atlas
- Git
- Visual Studio Code or another code editor (optional)

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```powershell
git clone <YOUR_PUBLIC_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>
```

Replace the placeholders with your actual GitHub repository URL and project folder name.

### 2. Create a virtual environment

```powershell
py -3.11 -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a local `.env` file in the project root.

```dotenv
MONGO_URI=mongodb://localhost:27017
MONGO_DB=attendance_db
```

For MongoDB Atlas, replace the local connection string with your Atlas connection string.

**Security notes:**

- Never commit `.env` or database credentials to GitHub.
- Configure real environment variables when required; they take precedence over values loaded from `.env`.
- Ensure `.env` is included in `.gitignore`.

---

## ▶️ Run the Application

From the project root, run:

```powershell
uvicorn app.main:app --port 8000 --reload
```

If your project uses the provided sample seeding script, you can load the sample data first:

```powershell
python sample_seed.py
```

Run the seed command only if `sample_seed.py` exists in your project.

### 🌐 API Documentation

Once the server is running, open these URLs:

| Resource | URL |
|---|---|
| Interactive API documentation | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Health check | [http://localhost:8000/health](http://localhost:8000/health) |
| OpenAPI JSON | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) |

---

## 📡 API Features

| Module | Functionality |
|---|---|
| Health | Application and database readiness |
| Employees | Create and list employee records |
| Attendance | Punch-in, punch-out and attendance listing |
| Regularization | Manually correct attendance records with audit history |
| Monthly Analytics | Employee attendance statistics for a selected month |
| Department Summary | Department-level attendance aggregation |
| Late Leaderboard | Identify employees with late arrivals |
| Department Trend | Daily attendance trends for a department |
| Explain API | Inspect MongoDB execution statistics for supported queries |

Refer to the project's `openapi.yaml` and `DATA_MODEL.md` for the precise API contract and data definitions.

---

## 🗄️ Database & Performance

The application uses MongoDB collections for employee records and attendance logs.

Database indexes support:

- Unique employee codes
- Unique employee attendance records by date
- Date-based attendance queries
- Employee-specific attendance reports
- Department and status filtering
- Late-arrival reporting

MongoDB aggregation pipelines are used for analytical endpoints where appropriate.

---

## 🧪 Testing & Validation

Before submission, compare the implementation against `openapi.yaml` and `DATA_MODEL.md`.

Recommended test cases include:

- Valid and invalid employee creation
- Duplicate employee codes
- Punch-in and punch-out business rules
- Repeated and concurrent attendance requests
- Manual corrections and audit history
- Overnight shifts and timestamp boundaries
- Missing attendance days and employees without logs
- Monthly statistics and department summaries
- Late-arrival leaderboard ties
- Date gap filling in department trends
- MongoDB explain plans and execution statistics

**Important:** Successful HTTP responses alone do not prove that all business rules and analytical results are correct. Validate the returned data against expected results.

---

## 📁 Required Submission Files

The public repository should contain these required files:

```text
project-root/
├── app/
│   └── main.py
├── requirements.txt
├── README.md
├── REVIEW.md
├── DECISIONS.md
├── openapi.yaml
├── DATA_MODEL.md
└── .gitignore
```

This is an illustrative structure. Keep the assignment's supplied files and actual project layout intact, and include any additional files the implementation genuinely needs.

### 📄 Documentation

- **`README.md`** — Setup, configuration, execution and project overview
- **`REVIEW.md`** — Review of the provided existing code
- **`DECISIONS.md`** — Explanation of implementation and design decisions
- **`requirements.txt`** — Python dependencies

---

## 🔒 Security & Repository Checklist

Before pushing to GitHub:

- [ ] Exclude `.env` files and database credentials.
- [ ] Exclude the `.venv` virtual environment.
- [ ] Do not include a Dockerfile.
- [ ] Confirm all required submission files are present.
- [ ] Verify the documented commands match the actual project.
- [ ] Check that the repository is public.
- [ ] Test the application using a clean setup where possible.

---

## 📅 Submission

**Assignment:** HROne — Software Engineer Trainee  
**Project:** Employee Attendance & Analytics API  
**Deadline:** 15 October 2026, 11:59 PM IST

Submit the public GitHub repository URL using the submission form provided in the HROne assignment email. Use the same email address as your application and keep the repository public until 31 October 2026, as instructed.

---

<p align="center">

  **Built with Python, FastAPI and MongoDB**

  *Focused on reliable attendance management, analytics and maintainable backend design.*

</p>
