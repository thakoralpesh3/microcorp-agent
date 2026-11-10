# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Backend Architecture & Boilerplate*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Enterprise Engine
Stop wasting 40+ hours configuring boilerplate architecture, setting up secure password hashing, wiring up JWT token lifecycle management, and fighting Docker multi-stage builds. 

This turnkey solution provides an enterprise-ready, strictly typed, asynchronous backend foundation built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL**, **Pydantic v2**, and **Docker**. Designed specifically for freelance developers, agencies, and enterprise teams needing to deliver secure APIs to clients on day one.

### 💼 What’s Included in This Package:
*   **Zero-Config Security:** Complete OAuth2 Password Bearer flow with access & refresh token rotation.
*   **Asynchronous Database Layer:** Non-blocking database sessions using `asyncpg` and SQLAlchemy 2.0 async engine.
*   **Type-Safe Validation:** Strict request/response validation utilizing Pydantic v2 schemas.
*   **Production Containerization:** Optimized multi-stage Dockerfiles and Docker Compose orchestration for local development and production deployment.
*   **Extensible Architecture:** Modular directory structure designed for high scale and easy feature additions.

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts & Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance asynchronous API routing and automatic OpenAPI generation. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and strict environment configuration. |
| **ORM & Database** | SQLAlchemy 2.0 + Asyncpg | High-speed, non-blocking asynchronous relational database operations. |
| **Authentication** | PyJWT + Passlib (Bcrypt) | Cryptographically secure JWT issuance, validation, and password hashing. |
| **Containerization** | Docker & Docker Compose | Isolated, reproducible development and production deployment environments. |

---

## 3. Production Code Patterns & Architecture Examples

### 📂 Directory Structure
```text
fastapi-enterprise-engine/
│
├── alembic/                 # Database migrations
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py          # Dependency injection (DB session, current user)
│   ├── core/
│   │   ├── config.py        # Pydantic BaseSettings management
│   │   ├── database.py      # Async engine and session factory
│   │   └── security.py      # JWT hashing and verification logic
│   ├── models/
│   │   └── user.py          # SQLAlchemy declarative models
│   ├── schemas/
│   │   └── user.py          # Pydantic request/response models
│   └── main.py              # FastAPI application entrypoint
│
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### ⚙️ 1. Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
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
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### 🗄️ 2. Database Setup (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
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

### 🔒 3. Security & JWT Utility (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 🛡️ 4. Dependency Injection (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### 🐳 5. Containerization (`Dockerfile`)
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

# Stage 2: Final runtime image
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 📦 6. Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
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
      - PROJECT_NAME=FastAPI Enterprise Engine
      - SECRET_KEY=supersecretkeychangeinproduction
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1.  **Mixing Sync and Async Code (Blocking the Event Loop):**
    *   *Anti-Pattern:* Using standard `requests` or synchronous database drivers (`psycopg2`) inside async FastAPI path operations.
    *   *Fix:* Always use async drivers (`asyncpg`) and async HTTP clients (`httpx`) to ensure the event loop remains unblocked.
2.  **Hardcoding Secrets & Configuration:**
    *   *Anti-Pattern:* Writing database credentials or JWT secrets directly into code files.
    *   *Fix:* Use `pydantic-settings` to enforce runtime environment variable loading with validation.
3.  **Leaning on `expire_on_commit=True` in Async Sessions:**
    *   *Anti-Pattern:* Accessing model attributes after a commit without refreshing, leading to `MissingGreenlet` errors in SQLAlchemy 2.0.
    *   *Fix:* Configure session makers with `expire_on_commit=False` and explicitly refresh instances when required.

---

## 5. Performance & Optimization Tips

*   **Connection Pooling:** Configure optimal `pool_size` and `max_overflow` on the SQLAlchemy engine based on your underlying PostgreSQL instance sizing.
*   **Response Compression:** Integrate `GZipMiddleware` in `app/main.py` to automatically compress large JSON payloads and reduce network transit overhead.
*   **Uvicorn Worker Scaling:** In production environments behind a reverse proxy (like Nginx), scale Uvicorn workers using process managers or container replicas rather than single-process concurrency.

---

## 6. Commercial License & Attribution Summary

*   **License:** Commercial Turnkey License — Granted for use in client projects, SaaS products, and freelance deliverables. 
*   **Attribution:** Provided by **MicroCorp AI / The Agency Engineering Division**. Redistribution of the raw boilerplate as a competing commercial product is strictly prohibited.