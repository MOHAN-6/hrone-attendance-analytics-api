# 🚀 Employee Attendance & Analytics API

**A FastAPI + MongoDB backend for employee attendance management and workforce analytics.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Project](https://img.shields.io/badge/Project-Backend%20API-6C63FF?style=for-the-badge)

## 📌 Project Overview

The **Employee Attendance & Analytics API** is a Python backend developed for the HROne Software Engineer Trainee technical assignment.

Built with **FastAPI and MongoDB**, the application provides employee management, attendance punch-in and punch-out, manual attendance regularization with audit history, and workforce analytics using MongoDB aggregation pipelines.

### ✨ Key Features

- Employee creation and listing
- Attendance punch-in and punch-out with business-rule validation
- Attendance regularization with an audit trail
- Monthly employee attendance analytics
- Department-wise attendance summaries
- Late-arrival leaderboard
- Department attendance trends
- MongoDB query execution-statistics endpoint
- Database indexes for uniqueness and query performance

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Backend programming |
| FastAPI | REST API framework |
| MongoDB | Database |
| PyMongo | MongoDB connectivity and queries |
| Pydantic | Request validation and data models |
| Uvicorn | ASGI application server |
| Git and GitHub | Version control and repository hosting |

## 📋 Prerequisites

Install the following before running the application:

- Python 3.11 or newer
- MongoDB compatible with the application's aggregation features
- Git
- Visual Studio Code or another code editor (optional)

## ⚙️ Installation and Setup

### 1. Clone the repository

```powershell
git clone https://github.com/MOHAN-6/hrone-attendance-analytics-api.git
cd hrone-attendance-analytics-api
```

### 2. Create a virtual environment

```powershell
py -3.11 -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use Command Prompt and run:

```bat
.venv\Scripts\activate.bat
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 🔐 Environment Configuration

Create a local `.env` file in the project root:

```dotenv
MONGO_URI=mongodb://localhost:27017
MONGO_DB=attendance_db
```

For MongoDB Atlas, use your own connection string and database configuration.

**Security guidelines:**

- Never commit `.env` files, passwords, or database credentials to GitHub.
- Keep `.env` in `.gitignore`.
- Use environment variables for production configuration.
- Do not share database credentials publicly.

## ▶️ Run the Application

From the project root, start the API:

```powershell
python -m uvicorn app.main:app --port 8000 --reload
```

If port 8000 is already in use, choose another port, such as 8001:

```powershell
python -m uvicorn app.main:app --port 8001 --reload
```

### Optional sample data

The repository includes `sample_seed.py` for loading sample data.

**Warning:** The script clears existing employee and attendance records in the configured collections before inserting sample records. Run it only against a disposable development database when you intentionally want to reset its data. Do not run it against a database containing records you need to preserve.

### 🌐 API Documentation

After starting the server, open the appropriate URL for your selected port.

| Resource | URL when using port 8000 |
|---|---|
| Interactive API documentation | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Health check | [http://localhost:8000/health](http://localhost:8000/health) |
| OpenAPI JSON | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) |

## 📡 API Modules

| Module | Functionality |
|---|---|
| Health | Application and database readiness |
| Employees | Create and list employee records |
| Attendance | Punch-in, punch-out, and attendance listing |
| Regularization | Correct attendance records and maintain audit history |
| Monthly Analytics | Employee attendance statistics for a selected month |
| Department Summary | Department-level attendance aggregation |
| Late Leaderboard | Identify employees with late arrivals |
| Department Trend | Daily attendance trends for a department |
| Explain API | Inspect MongoDB execution statistics for supported queries |

Refer to `openapi.yaml` for the API contract and `DATA_MODEL.md` for the data definitions.

## 🗄️ Database and Performance

The application uses MongoDB collections for employee records and attendance logs.

Database indexes support:

- Unique employee codes
- Unique employee attendance records by date
- Date-based attendance queries
- Employee-specific attendance reports
- Department and status filtering
- Late-arrival reporting

MongoDB aggregation pipelines support analytical endpoints where appropriate.

## 🧪 Testing and Validation

Before submission, validate the implementation against `openapi.yaml` and `DATA_MODEL.md`.

Recommended test cases include:

- Valid and invalid employee creation
- Duplicate employee codes
- Punch-in and punch-out business rules
- Repeated and concurrent attendance requests
- Attendance regularization and audit history
- Overnight shifts and timestamp boundaries
- Missing attendance days and employees without attendance logs
- Monthly statistics and department summaries
- Late-arrival leaderboard ties
- Date-gap filling in department trends
- MongoDB explain plans and execution statistics

Successful HTTP responses alone do not prove that all business rules and analytics are correct. Verify response values against expected results.

## 📁 Project Structure

```text
hrone-attendance-analytics-api/
├── app/
│   └── main.py
├── sample_data/
├── requirements.txt
├── README.md
├── REVIEW.md
├── DECISIONS.md
├── DATA_MODEL.md
├── openapi.yaml
├── sample_seed.py
└── .gitignore
```

The structure above highlights the main project files. Keep any additional files required by the supplied implementation.

## 📄 Documentation

- **`README.md`** — Project overview, setup, configuration, and execution
- **`REVIEW.md`** — Review of the provided code and identified issues
- **`DECISIONS.md`** — Implementation and design decisions
- **`DATA_MODEL.md`** — Data definitions and relationships
- **`openapi.yaml`** — API specification
- **`requirements.txt`** — Python dependencies

## 🔒 Security and Submission Checklist

- [ ] `.env` files and credentials are excluded from GitHub.
- [ ] The `.venv` directory is excluded from GitHub.
- [ ] No Dockerfile is included.
- [ ] Required assignment files are present.
- [ ] Setup instructions match the actual project.
- [ ] The repository is public.
- [ ] The application has been tested with a working MongoDB connection.
- [ ] Analytics results have been checked against expected values.

## 📅 Submission

**Assignment:** HROne — Software Engineer Trainee  
**Project:** Employee Attendance & Analytics API  
**Deadline:** 15 October 2026, 11:59 PM IST

Submit the public GitHub repository URL through the submission form provided in the HROne assignment email. Use the same email address as your application and keep the repository public until 31 October 2026, as instructed.

Follow the assignment's restrictions on sharing the problem statement and solution outside the permitted submission process.

---

**Built with Python, FastAPI, and MongoDB.**

*Focused on reliable attendance management, analytics, and maintainable backend design.*
