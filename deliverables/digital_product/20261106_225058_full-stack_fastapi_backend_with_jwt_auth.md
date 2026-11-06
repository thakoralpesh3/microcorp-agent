# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

## 1. Product Title & Value Proposition

### 🚀 Production-Grade FastAPI Backend Boilerplate
*A battle-tested, highly scalable, asynchronous Python backend boilerplate featuring secure JWT authentication, SQLAlchemy 2.0 (async), Alembic migrations, Pydantic v2 validation, and a fully orchestrated Docker Compose environment.*

---

### Why Engineers & Clients Choose This Solution
* **Zero Technical Debt Setup:** Avoid weeks of trial-and-error configuring secure password hashing, CORS, environment variables, and database connection pooling.
* **Modern Async Architecture:** Built natively on Python's `asyncio`, Starlette, and FastAPI for non-blocking I/O performance capable of handling thousands of concurrent requests.
* **Production-Ready Security:** Implements stateless JSON Web Tokens (JWT) with secure expiration, HTTP-only cookie support strategy patterns, and robust role-based access control (RBAC).
* **Instant Containerization:** One-command deployment using Docker and Docker Compose with multi-stage builds minimizing image footprints and isolating environments.

---

## 2. Quick Start & Core Concepts

### System Requirements
* Python 3.11+
* Docker & Docker Compose v2+
* Git

### 3-Step Local Initialization
```bash
# 1. Clone the repository and navigate to the project root
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Initialize the environment variables file
cp .env.example .env

# 3. Spin up the containers in detached mode
docker-compose up --build -d
```

### Core Architecture Concepts & Syntax Mapping

| Component | Technology | Primary Purpose | Clean Syntax Example |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI / Starlette | High-performance API routing & docs | `@app.get("/items/{id}")` |
| **Validation** | Pydantic v2 | Strict payload deserialization & types | `class UserIn(BaseModel): email: EmailStr` |
| **ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database session management | `result = await db.execute(select(User))` |
| **Migrations** | Alembic | Version control for database schemas | `alembic revision --autogenerate -m "Init"` |
| **Auth** | python-jose & passlib | Stateless cryptographic JWT verification | `encode_jwt(data={"sub": user.email})` |

---

## 3. Production Code Patterns & Architecture Examples

### Directory Structure
```text
.
├── alembic/                  # Database migration versions
├── app/
│   ├── api/                  # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # auth.py, users.py, items.py
│   │   │   └── api.py        # Router aggregator
│   ├── core/                 # Config, security, database session
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async engine & sessionmaker
│   │   └── security.py       # JWT creation & password hashing
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic input/output schemas
│   └── main.py               # Application factory & middleware
├── Dockerfile                # Multi-stage production container build
├── docker-compose.yml        # Local orchestration (App + PostgreSQL)
└── requirements.txt          # Pinned project dependencies
```

---

### Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )


settings = Settings()
```

---

### Database Session Provider (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

async_engine = create_async_engine(
    settings.DATABASE_URL, echo=False, pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


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

### Security & JWT Handling (`app/core/security.py`)
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
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

---

### Authentication API Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### Application Factory (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)
    return application


app = get_application()
```

---

### Docker Configuration (`Dockerfile`)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime Image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=app_db
      - SECRET_KEY=super-secret-production-key-change-this
    depends_on:
      db:
        condition: service_healthy
    restart: always

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Mixing Synchronous DB Drivers with Async FastAPI
* **The Antipattern:** Using standard `psycopg2` or synchronous SQLAlchemy sessions inside `async def` route handlers, which blocks the entire event loop thread during I/O operations.
* **The Correct Way:** Always use an asynchronous driver like `asyncpg` combined with `sqlalchemy.ext.asyncio` session handlers.

### ❌ 2. Storing Secrets Directly in Source Code
* **The Antipattern:** Hardcoding JWT secret keys, database credentials, or third-party API keys directly into Python files.
* **The Correct Way:** Leverage Pydantic's `BaseSettings` combined with `.env` file injection, keeping configuration strictly isolated from runtime code.

### ❌ 3. Catching Universal Exceptions Blindly
* **The Antipattern:** Writing broad `except Exception:` blocks without logging or re-raising, hiding database constraint violations or critical application bugs.
* **The Correct Way:** Intercept explicitly known operational exceptions (e.g., `IntegrityError`), raise clean FastAPI `HTTPException` codes, and log internal errors securely.

---

## 5. Performance & Optimization Tips

1. **Connection Pooling Tuning:** Adjust SQLAlchemy engine parameters `pool_size` and `max_overflow` based on your worker concurrency and database max connections threshold.
2. **Gzip Compression Middleware:** Enable Starlette's `GZipMiddleware` for high-payload JSON responses to drastically reduce network transmission footprint.
3. **Uvicorn Worker Scaling:** In production container deployments, run multiple Uvicorn worker processes behind an Nginx reverse proxy using process managers or Gunicorn managed workers (`gunicorn -k uvicorn.workers.UvicornWorker`).
4. **Select Specific Columns:** Avoid wildcard queries (`select(User)`) on tables with heavy text or binary columns when returning lightweight lists. Select explicitly required attributes via Pydantic projection models.

---

## 6. Commercial License & Attribution Summary

### MIT Commercial License Grant
*Copyright (c) 2026 MicroCorp AI. All rights reserved.*

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.**