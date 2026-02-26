# ⚡ FastAPI Notes API

## 📝 Project Intention

The FastAPI Notes API is primarily built as a learning and practice project for mastering modern backend development with FastAPI. The goal is not just to create a CRUD app, but to understand and implement real-world backend patterns that are essential for production-ready applications.

---

## ✨ Features

*   **FastAPI**-based REST API
*   **PostgreSQL** database with **SQLAlchemy** ORM
*   Database migrations using **Alembic**
*   **Pydantic** models for request and response validation
*   JWT-based authentication
*   Dependency Injection for database sessions
*   Middleware support (logging / response time)
*   Environment-based configuration
*   CORS configuration

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
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml
├── .env.example
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

This project offers two ways to set up and run the application: a traditional local development environment using a virtual environment, and a Dockerized web application that connects to a local PostgreSQL database.

### Environment Variables (`.env` and `.env.example`)

Configuration for the project is managed through environment variables. A `.env.example` file is provided to illustrate the required variables. You should create a `.env` file in the project root, copying the structure from `.env.example` and filling in your specific values.

```ini
# Database Internal Config
DB_USER= #database username
DB_PASSWORD= #database password
DB_NAME= #data base name for the current project

# App Connection String (Notice it uses 'db' as the hostname)
DB_URL= #the url which include the db engine username and password with the database name for the project.
ACCESS_SECRET_KEY= #secret key for access token 
REFRESH_SECRET_KEY= #secret key for refresh token

# Secrets & Other Confi
ALGORITHUM= #token hashing algorithum
TOKEN_EXPIRY_DATE= #token expiry date
UPLOAD_DIR= #folder names for upload files
LOGFILEDIR= #folder name for the system to store log files
ORIGIN= #the origin or the url of the system
```

> ⚠️ **Security Note:** Ensure your `.gitignore` file includes `.env` to prevent accidentally committing credentials.
### Option 1: Local Development (Virtual Environment)

This option sets up the FastAPI application directly on your machine using a Python virtual environment, connecting to a locally installed PostgreSQL database.

#### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

#### 2. Create and activate virtual environment

```bash
# Create venv
python -m venv venv

# Activate (Linux / Mac)
source venv/bin/activate    

# Activate (Windows)
virtual_env\Scripts\activate       
```

#### 3. Install dependencies

Install all required Python packages:

```bash
pip install -r requirement.txt
```

#### 4. Environment Configuration

Create a file named **`.env`** in the project root to store sensitive configuration details. Ensure your local PostgreSQL database is running and accessible. The `DB_URL` should point to your local database instance.

```ini
DB_URL=postgresql://username:password@localhost:5432/your_database
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=DIR_NAME
```

> ⚠️ **Security Note:** Ensure your `.gitignore` file includes `.env` to prevent accidentally committing credentials.

#### 5. Database & Alembic Migrations

If this is the first time running the project, you need to create and apply the database schema:

```bash
# 1. Generate migration script (if models in db_models.py have changed)
alembic revision --autogenerate -m "initial migration"

# 2. Apply migration to the database
alembic upgrade head
```

#### 6. Run the Application

Start the FastAPI application using Uvicorn with auto-reload enabled:

```bash
uvicorn main:app --reload
```

### Option 2: Dockerized Web Application (Local Database)

This option runs the FastAPI application inside a Docker container using Docker Compose, while connecting to a locally installed PostgreSQL database. This provides environment isolation for the web application.

#### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

#### 2. Environment Configuration

**`.env` file (for local virtual environment):**

As described in Option 1, create a `.env` file in the project root with your local database connection string (e.g., `DB_URL=postgresql://username:password@localhost:5432/your_database`). This file is primarily for the virtual environment setup.

**`docker-compose.override.yml` (for Dockerized setup):**

To allow the Dockerized application to connect to your local PostgreSQL database, you will use a `docker-compose.override.yml` file. This file will override the `DB_URL` environment variable specifically for the Docker Compose setup.



> ⚠️ **Security Note:** Ensure your `.gitignore` file includes `.env`to prevent accidentally committing credentials.

#### 3. Build and Run with Docker Compose

Navigate to the project root directory where `Dockerfile`, `docker-compose.yml`, and `docker-compose.override.yml` are located. Run the following command to build the Docker image and start the application service. Docker Compose will automatically pick up both `docker-compose.yml` and `docker-compose.override.yml`.

```bash
docker compose up --build
```

This command will:
*   Build the `app` service Docker image based on the `Dockerfile`.
*   Start the FastAPI application service (`app`), using the `DB_URL` provided in `docker-compose.override.yml`.

*Note: Alembic migrations should be run manually in your local virtual environment (Option 1, Step 5) as the database is local. If you need to run migrations within the Docker container, you would need to adjust the `CMD` in the `Dockerfile` or execute them in a temporary container.*

### Access the Application (Both Options)

Once the application is running (either locally or via Docker), the API will be available at:

  * **API Root:** `http://127.0.0.1:8080`
  * **Interactive Docs (Swagger UI):** `http://127.0.0.1:8080/docs`

-----

## Key Concepts Practiced

  * FastAPI routing and dependency injection
  * Pydantic request/response models
  * SQLAlchemy ORM models and relationships
  * Alembic migrations
  * JWT authentication flow
  * Middleware usage
  * Secure environment configuration
  * Docker containerization (for web application) with Docker Compose and override files

-----
📂 Log Files

The LOGFILE_DIR directory is used to store all application log files.

Each log file is created per day, named with the current date (e.g., 2025-12-22.log).

The logs record request time, method, URL, user ID, status code, request id and response time, helping track user activity and API performance.

----
## 📜 License

This project is licensed under the **MIT License**.
