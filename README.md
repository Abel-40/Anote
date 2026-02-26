# ⚡ FastAPI Notes API

## 📝 Project Intention

The FastAPI Notes API is primarily built as a learning and practice project for mastering modern backend development with FastAPI. The goal is not just to create a CRUD app, but to understand and implement real-world backend patterns that are essential for production-ready applications.

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
├── Dockerfile
├── docker-compose.yml
|-- docker-compose.override.yml
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
| **Containerization** | Docker |

-----

## ⚙️ Setup Instructions (Dockerized)

This project is now containerized using Docker, providing a consistent and isolated development environment. Follow these steps to get the application running.

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

### 2. Environment Configuration

Create a file named **`.env`** in the project root to store sensitive configuration details. This file will be used by `docker-compose` to set environment variables for the application service. Make sure to replace the placeholder values with your actual credentials.

```ini
DB_URL=postgresql://username:password@db:5432/your_database
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
UPLOAD_DIR=DIR_NAME
```

> ⚠️ **Security Note:** Ensure your `.gitignore` file includes `.env` to prevent accidentally committing credentials.

### 3. Build and Run with Docker Compose

Navigate to the project root directory where `docker-compose.yml` is located and run the following command to build the Docker images and start the services. This will also apply Alembic migrations automatically.

```bash
docker-compose up --build
```

This command will:
* Build the `app` service Docker image based on the `Dockerfile`.
* Start a PostgreSQL database service (`db`).
* Apply any pending Alembic database migrations.
* Start the FastAPI application service (`app`).

### 4. Access the Application

Once the services are up and running, the API will be available at:

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
  * Docker containerization for development and deployment

-----
📂 Log Files

The LOGFILE_DIR directory is used to store all application log files.

Each log file is created per day, named with the current date (e.g., 2025-12-22.log).

The logs record request time, method, URL, user ID, status code, request id and response time, helping track user activity and API performance.

----
## 📜 License

This project is licensed under the **MIT License**.
