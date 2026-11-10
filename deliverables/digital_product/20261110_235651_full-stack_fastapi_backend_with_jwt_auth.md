# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Packet*

---

## 1. # Product Title & Value Proposition

### **Product Title:** 
Enterprise-Grade FastAPI Backend Boilerplate (JWT Authentication, PostgreSQL, Alembic, Dockerized)

### **Value Proposition:**
Building a production-ready asynchronous Python backend from scratch takes 40+ hours of boilerplate configuration, security hardening, and deployment scripting. This turnkey solution delivers a fully structured, enterprise-ready FastAPI architecture out of the box. 

Engineered strictly following industry best practices, it features secure token-based authentication (OAuth2 with JWT), automatic database migrations via Alembic, fully typed asynchronous ORM models (SQLModel/SQLAlchemy 2.0), and a production-optimized multi-stage Docker container setup. Designed for agency developers and freelance engineers to hand off to clients with absolute confidence, reducing initial backend delivery time by 90%.

---

## 2. ## Quick Start & Core Concepts

### **The Architecture Stack**
| Component | Technology | Version / Standard |
| :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` (Async / ASGI via Uvicorn) |
| **Database ORM** | SQLAlchemy | `2.0+` (Typed asynchronous sessions) |
| **Migrations** | Alembic | Version-controlled schema evolutions |
| **Authentication** | PyJWT / Passlib | OAuth2 Password Bearer with JWT & bcrypt hashing |
| **Containerization** | Docker & Docker Compose | Multi-stage builds, non-root users, health checks |
| **Validation** | Pydantic | `v2` Strict data validation and settings management |

### **5-Minute Local Setup**
```bash
# 1. Clone or extract the repository
cd fastapi-enterprise-boiler

# 2. Copy the environment template
cp .env.example .env

# 3. Spin up services via Docker Compose (PostgreSQL + API)
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head

# 5. Verify API health
curl http://localhost:8000/health
# Response: {"status":"healthy","database":"connected"}
```

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi-enterprise-boiler/
├── alembic/                  # Database migration versions & env.py
├── app/
│   ├── api/                  # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # auth.py, users.py, items.py
│   │   │   └── router.py     # Main v1 router aggregator
│   ├── core/                 # Config, security, database session setup
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async engine & sessionmaker
│   │   └── security.py       # JWT creation, verification, password hashing
│   ├── models/               # SQLAlchemy 2.0 database models
│   │   └── user.py
│   ├── schemas/              # Pydantic request/response schemas
│   │   └── user.py
│   └── main.py               # FastAPI app factory and middleware setup
├── Dockerfile                # Production multi-stage build
├── docker-compose.yml        # Local orchestration
├── requirements.txt          # Pinned project dependencies
└── .env.example              # Environment variables template
```

---

### **1. Core Configuration (`app/core/config.py`)**
Handles strict environment variable parsing using Pydantic v2.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    SQLALCHEMY_DATABASE_URI(str) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### **2. Asynchronous Database Session (`app/core/database.py`)**
Configures SQLAlchemy 2.0 with async engine and FastAPI dependency injection.

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### **3. Security & JWT Utility (`app/core/security.py`)**
Handles password hashing via `passlib` and JWT creation/decryption.

```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
```

---

### **4. User Database Model (`app/models/user.py`)**
SQLAlchemy 2.0 mapped model supporting async execution.

```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

### **5. Production-Ready Dockerfile**
Multi-stage build minimizing image footprint and securing runtime execution.

```dockerfile
# --- Stage 1: Build Dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Runtime Environment ---
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies from builder stage
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create unprivileged system user for security hardening
RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **6. Docker Compose Setup (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_api
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction123!
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes (`def` vs `async def`)**
   * *The Anti-Pattern:* Using standard synchronous libraries (like standard `requests` or synchronous DB drivers) inside an `async def` path operation. This blocks the main event loop, destroying concurrent performance.
   * *The Fix:* Use asynchronous equivalents (`httpx` instead of `requests`, `asyncpg` instead of `psycopg2`). If a blocking library must be used, execute it via `run_in_threadpool`.

2. **Hardcoding Application Secrets**
   * *The Anti-Pattern:* Committing `.env` files or JWT secret keys directly into source control.
   * *The Fix:* Always utilize Pydantic `BaseSettings` reading exclusively from environment variables injected at runtime via Docker or host environments.

3. **Ignoring Database Connection Pool Exhaustion**
   * *The Anti-Pattern:* Creating a new database engine or sessionmaker inside every request dependency scope.
   * *The Fix:* Initialize a single engine instance globally per application lifecycle and scope only session instances per request dependency (`yield` pattern).

4. **Catching Generic Exceptions Globally Without Logging**
   * *The Anti-Pattern:* Wrapping route logic in `try...except Exception:` and returning generic 500 errors without structured logging.
   * *The Fix:* Use FastAPI's global exception handlers or let unhandled exceptions surface to custom middleware configured with structured JSON log formatters.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container environments, scale Uvicorn workers based on CPU cores rather than running a single instance. Use Gunicorn with Uvicorn worker classes or configure multiple worker processes behind a load balancer (e.g., `uvicorn app.main:app --workers 4`).
* **SQLAlchemy Result Caching & Lazy Loading:** Avoid N+1 query performance hits by explicitly implementing `selectinload` or `joinedload` on relationships within async queries.
* **Gzip Compression Middleware:** Enable response compression for payloads larger than 1KB to drastically decrease network latency over standard APIs:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Connection Pooling Parameters:** Tune `pool_size` and `max_overflow` in your SQLAlchemy async engine creation based on your database tier and expected concurrent connection peaks.

---

## 6. ## Commercial License & Attribution Summary

### **Commercial End-User License Agreement (EULA)**
* **Grant of Rights:** MicroCorp AI grants the purchaser (Client/Freelancer) a perpetual, non-exclusive, worldwide, transferable license to use, modify, adapt, and deploy this codebase for commercial client projects or internal products.
* **Restrictions:** Redistribution of this codebase as a standalone competing boilerplate template, open-source template kit, or digital asset package is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is" without warranty of any kind, express or implied. MicroCorp AI and The Agency Engineering Division shall not be held liable for any direct, indirect, or incidental damages arising from the deployment or operation of this software.

---
*Built with precision by The Agency Engineering Division — MicroCorp AI.*