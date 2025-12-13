# ⚡ FastAPI Notes API

This project is a backend API built with **FastAPI** designed to practice and demonstrate real-world backend concepts, including authentication, database relationships, migrations, middleware, and file handling.

The project is intentionally concise, aiming to cover most core FastAPI features efficiently.

---

## ✨ Features

* **FastAPI**-based REST API
* **PostgreSQL** database with **SQLAlchemy** ORM
* Database migrations using **Alembic**
* **Pydantic** models for request and response validation
* JWT-based authentication
* Dependency Injection for database sessions
* Middleware support (logging / response time)
* Environment-based configuration
* CORS configuration

---

## 📂 Project Structure

```text

├── alembic/
│   ├── README
│   ├── env.py
│   └── script.py.mako
├── .gitignore
├── alembic.ini
├── config.py
├── db_connection.py
├── db_models.py
├── main.py
├── pydantic_models.py
├── requirement.txt
└── README.md
```
----

## 🧱 Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Framework** | FastAPI | High-performance API |
| **ORM** | SQLAlchemy | Python SQL Toolkit and ORM |
| **Database** | PostgreSQL | Robust Relational Database |
| **Migrations** | Alembic | Database migration tool |
| **Validation** | Pydantic | Data validation and settings management |
| **Server** | Uvicorn | ASGI server |

-----

## ⚙️ Setup Instructions

### 1 Clone the repository

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

### 2 Create and activate virtual environment

```bash
# Create venv
python -m venv venv

# Activate (Linux / Mac)
source venv/bin/activate    

# Activate (Windows)
venv\Scripts\activate       
```

### 3 Install dependencies

Install all required Python packages:

```bash
pip install -r requirement.txt
```

### 4 Environment Configuration

Create a file named **`.env`** in the project root to store sensitive configuration details:

```ini
DB_URL=postgresql://username:password@localhost:5432/your_database
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> ⚠️ **Security Note:** Ensure your `.gitignore` file includes `.env` to prevent accidentally committing credentials.

### 5 Database & Alembic Migrations

If this is the first time running the project, you need to create and apply the database schema:

```bash
# 1. Generate migration script (if models in db_models.py have changed)
alembic revision --autogenerate -m "initial migration"

# 2. Apply migration to the database
alembic upgrade head
```

### 6 Run the Application

Start the FastAPI application using Uvicorn with auto-reload enabled:

```bash
uvicorn main:app --reload
```

The API will be available at:

  * **API Root:** `http://127.0.0.1:8000`
  * **Interactive Docs (Swagger UI):** `http://127.0.0.1:8000/docs`

-----

## Key Concepts Practiced

  * FastAPI routing and dependency injection
  * Pydantic request/response models
  * SQLAlchemy ORM models and relationships
  * Alembic migrations
  * JWT authentication flow
  * Middleware usage
  * Secure environment configuration

-----

## 📜 License

This project is licensed under the **MIT License**.