# 🚀 Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*Enterprise-Grade Turnkey Solution for High-Performance Microservices*

---

## 1. # Product Title & Value Proposition

### 💎 Executive Value Proposition
Building production-ready, secure, and horizontally scalable backends from scratch is time-consuming and fraught with architectural pitfalls. This turnkey solution provides a **battle-tested, enterprise-grade FastAPI boilerplate** pre-configured with secure JWT authentication, asynchronous database pooling via SQLAlchemy 2.0, Pydantic v2 validation, Alembic migrations, and fully containerized Docker multi-stage builds. 

Designed for rapid deployment, this codebase eliminates boilerplate setup overhead, ensures strict type safety, and adheres to modern 12-factor app principles—allowing you to ship secure APIs to production in hours, not weeks.

### 📦 What's Included in This Package
* **Clean Architecture Layout**: Separation of concerns (Routers, Services, Repositories, Schemas, Models).
* **Robust Security Layer**: Access & Refresh token rotation with bcrypt password hashing and OAuth2 password flow.
* **Asynchronous Database Layer**: PostgreSQL integration utilizing asyncpg and SQLAlchemy 2.0 async sessions.
* **Zero-Downtime Infrastructure**: Production-optimized `Dockerfile` (multi-stage) and `docker-compose.yml` with health checks.
* **Automated Migrations**: Pre-configured Alembic environment for schema version control.

---

## 2. ## Quick Start & Core Concepts

### 🚀 Rapid Deployment Guide

```bash
# 1. Clone or extract the repository
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Configure your environment variables
cp .env.example .env
# Edit .env with your secure SECRET_KEY and database credentials

# 3. Spin up the infrastructure via Docker Compose
docker-compose up --build -d

# 4. Run database migrations inside the container
docker-compose exec web alembic upgrade head

# 5. Verify the deployment
curl http://localhost:8000/health
```

### 📋 Architectural Syntax & Component Reference

| Component | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous routing, automatic OpenAPI/Swagger docs generation. |
| **Data Validation** | Pydantic v2 | Strict payload serialization, deserialization, and runtime type checking. |
| **ORM / Database** | SQLAlchemy 2.0 + Asyncpg | Non-blocking database queries and declarative object-relational mapping against PostgreSQL. |
| **Auth Engine** | Python-JOSE + Passlib | Cryptographic JWT generation, verification, and secure password hashing (Bcrypt). |
| **Migration Tool** | Alembic | Version-controlled database schema migrations. |
| **Containerization** | Docker & Compose | Isolated, reproducible multi-container production runtimes. |

---

## 3. ## Production Code Patterns & Architecture Examples

### 📂 Directory Structure
```text
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   └── users.py
│   │   └── router.py
│   └── deps.py
├── core/
│   ├── config.py
│   ├── security.py
│   └── database.py
├── models/
│   └── user.py
├── schemas/
│   └── user.py
├── services/
│   └── user_service.py
├── main.py
└── alembic.ini
```

---

### ⚙️ 1. Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### 🔌 2. Asynchronous Database Session (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
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

### 🛡️ 3. Security & JWT Handling (`app/core/security.py`)
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

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 📦 4. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from sqlalchemy import select

router = APIRouter()

@router.post("/login", summary="Generate Access and Refresh Tokens")
async def login_access_token(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### 🐳 5. Production Dockerfile
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

# Stage 2: Runtime Image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### 🐙 6. Docker Compose Configuration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_core
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
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

  web:
    build: .
    container_name: fastapi_core
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=supersecretaccesskeychangeinproduction
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Synchronous Operations in Async Endpoints**
   * *Anti-Pattern*: Calling standard `requests` or blocking ORM operations inside an `async def` path operation without `run_in_threadpool`. This blocks the main event loop and destroys concurrency.
   * *Fix*: Always use `asyncpg`, `httpx`, and native async drivers. Wrap legacy blocking code in `anyio` or FastAPI's `run_in_threadpool`.

2. ❌ **Hardcoding Secrets & Configuration Settings**
   * *Anti-Pattern*: Placing database URLs and JWT secrets directly inside Python files.
   * *Fix*: Leverage Pydantic BaseSettings to read strictly from environment variables and fail fast at startup if required variables are missing.

3. ❌ **Global Database Engine Instantiation Without Connection Pooling Configuration**
   * *Anti-Pattern*: Creating new database connections on every incoming request.
   * *Fix*: Use a singleton connection pool manager (`create_async_engine`) with configured `pool_size` and `max_overflow` limits.

4. ❌ **Improper Exception Handling for Database Rollbacks**
   * *Anti-Pattern*: Committing database sessions manually inside business logic without handling failure states, leaving hanging uncommitted transactions.
   * *Fix*: Encapsulate session lifecycles in dependency generators (`yield session`) ensuring auto-rollback on exception.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling**: In production container environments, run Uvicorn with multiple worker processes mapped to available CPU cores (`--workers N`), or place a high-performance reverse proxy (like Nginx or Envoy) in front of Uvicorn.
* **Response Caching**: Implement Redis caching layers for read-heavy API endpoints that do not require real-time state consistency.
* **Database Indexing**: Ensure high-cardinality search fields (such as user email addresses, foreign keys, and UUID primary keys) are properly indexed in PostgreSQL via Alembic migrations.
* **Payload Compression**: Integrate GZip middleware (`from fastapi.middleware.gzip import GZipMiddleware`) for large JSON response payloads to reduce network transfer bottlenecks.

---

## 6. ## Commercial License & Attribution Summary

### 📜 MicroCorp AI Enterprise Commercial License (v2.1)
* **Copyright (c) 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights**: This commercial digital product is licensed to the purchaser for internal development, client delivery, and commercial SaaS deployment.
* **Restrictions**: You may **not** resell, redistribute, sub-license, or open-source this codebase as a standalone boilerplate, template, or competing digital toolkit on platforms such as GitHub, Gumroad, or theme marketplaces.
* **Warranty Disclaimer**: Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claim, damages, or liability arising from the deployment of this software.