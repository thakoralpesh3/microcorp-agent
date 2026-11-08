# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*
> *Turnkey Enterprise Solution for High-Performance Microservices*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate with Async SQLAlchemy, JWT Authentication, and Production-Ready Dockerization**

#### **The Value Proposition**
Building secure, high-performance, asynchronous Python microservices from scratch is time-consuming and error-prone. This turnkey solution delivers a battle-tested, production-ready backend architecture designed for immediate deployment. 

Engineered strictly following industry best practices, this boilerplate eliminates weeks of boilerplate setup—including database session management, secure password hashing, JWT access/refresh token rotation, dependency injection, and containerized orchestration via Docker Compose. 

Whether you are delivering a custom backend for a Fiverr client or bootstrapping your own SaaS, this kit provides an uncompromised foundation built for horizontal scale and maintainability.

---

## 2. ## Quick Start & Core Concepts

### **The Architecture Stack**
* **Framework:** FastAPI (Asynchronous, High-Performance, Automatic OpenAPI/Swagger Docs)
* **Database Layer:** PostgreSQL + SQLAlchemy 2.0 (AsyncIO) + Alembic (Migrations)
* **Authentication:** OAuth2 with Password (Bearer), JWT (JSON Web Tokens), Bcrypt Password Hashing
* **Containerization:** Docker & Docker Compose (Multi-stage builds, non-root execution)

### **Clean Syntax & Configuration Table**

| Component | Technology | Purpose / Configuration Key |
| :--- | :--- | :--- |
| **ASGI Server** | Uvicorn | High-performance asynchronous server running worker loops. |
| **Env Management**| Pydantic `BaseSettings` | Type-safe environment variable parsing with validation. |
| **Auth Flow** | JWT (HS256) | Stateless authentication using Access (15m) & Refresh (7d) tokens. |
| **DB Driver** | `asyncpg` | Non-blocking PostgreSQL driver for high concurrent throughput. |
| **Migration Engine**| Alembic | Version control for database schemas. |

### **5-Minute Quick Start**

```bash
# 1. Clone the repository and navigate to the project root
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Copy the environment template
cp .env.example .env

# 3. Spin up the containers using Docker Compose
docker-compose up --build -d

# 4. Run database migrations inside the container
docker-compose exec api alembic upgrade head

# 5. Access the interactive Swagger documentation
open http://localhost:8000/docs
```

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi_backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   └── main.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### **1. Configuration Management (`app/core/config.py`)**
Using Pydantic v2 for robust validation of runtime environment variables.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### **2. Asynchronous Database Engine (`app/core/database.py`)**
Configuring SQLAlchemy 2.0 with asynchronous session factories.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
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
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session per request."""
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

### **3. Security & JWT Utilities (`app/core/security.py`)**
Password hashing via Passlib (Bcrypt) and secure token generation.

```python
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

---

### **4. Dependency Injection for Authentication (`app/api/deps.py`)**
Extracting and validating current users from incoming JWT Bearer tokens.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from sqlalchemy import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

---

### **5. Production Dockerfile (`Dockerfile`)**
Multi-stage build ensuring minimal image footprint and enhanced security (non-root execution).

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -u 1000 microcorp && chown -R microcorp:microcorp /app
USER microcorp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **6. Production Docker Compose (`docker-compose.yml`)**
Orchestrating API and PostgreSQL services with health checks.

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: microcorp_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: microcorp_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d microcorp_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    build: .
    container_name: microcorp_fastapi
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=microcorp_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-access-key-change-in-production
      - JWT_REFRESH_SECRET_KEY=super-secret-refresh-key-change-in-production
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints**
   * *The Antipattern:* Using standard `requests` library or synchronous database operations (like standard SQLAlchemy Session without `asyncio`) inside `async def` route handlers, which blocks the entire Uvicorn event loop.
   * *The Fix:* Always use `asyncpg` / SQLAlchemy async drivers or offload heavy CPU-bound tasks to background threadpools using `run_in_threadpool`.

2. **Hardcoding Secrets in Codebase or Dockerfiles**
   * *The Antipattern:* Committing `.env` files or hardcoding database passwords/JWT secrets directly in `docker-compose.yml` for production deployments.
   * *The Fix:* Use environment injection via CI/CD pipelines (GitHub Actions Secrets, AWS Secrets Manager) and keep `.env.example` scrubbed.

3. **Catching Generic Exceptions Blindly**
   * *The Antipattern:* Writing `except Exception:` blocks that swallow critical database disconnection errors or validation mismatches, returning vague 500 server errors.
   * *The Fix:* Catch specific SQLAlchemy exceptions (`IntegrityError`, `NoResultFound`) and map them explicitly to appropriate HTTP 409 or 404 responses.

---

## 5. ## Performance & Optimization Tips

* **Database Connection Pooling:** Fine-tune `pool_size` and `max_overflow` in the SQLAlchemy engine based on your container resource allocations and database maximum connection limits.
* **Response Serialization Compression:** Integrate GZip middleware (`from fastapi.middleware.gzip import GZipMiddleware`) to compress large JSON responses over the network wire.
* **Uvicorn Worker Scaling:** In production container environments, run multiple worker processes per CPU core by invoking Uvicorn with `--workers 4` or orchestrating instances via Kubernetes.
* **Selective Field Loading:** Avoid loading full relational graphs using lazy loading; explicitly use SQLAlchemy `.options(selectinload(...))` to prevent N+1 query problems.

---

## 6. ## Commercial License & Attribution Summary

### **Commercial License (MicroCorp AI Enterprise License)**
* **Copyright (c) 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, worldwide, non-exclusive license to use, modify, adapt, and deploy this codebase for commercial client deliverables (e.g., Fiverr, Upwork, Enterprise consulting) or proprietary SaaS applications.
* **Restrictions:** Redistribution of this boilerplate as a competing commercial template, boilerplate generator, or open-source framework without explicit written authorization from MicroCorp AI is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The Agency Engineering Division assumes no liability for production misconfigurations or security breaches arising from modified implementations.

---
*Generated by Backend Architect 🏗️ | The Agency Engineering Division*