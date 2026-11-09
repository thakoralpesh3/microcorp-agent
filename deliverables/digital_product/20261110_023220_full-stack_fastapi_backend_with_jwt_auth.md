# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Backend Architecture Series*
*Product SKU: MC-FASTAPI-TURKEY-009*

---

## 1. Product Title & Value Proposition

### Title
**FastAPI Production-Ready Starter: Enterprise JWT Authentication, SQLAlchemy 2.0 Async, and Dockerized Architecture**

### Value Proposition
Stop wasting 40+ hours configuring boilerplate architecture, setting up secure password hashing, wiring token-refresh lifecycles, and debugging Docker multi-stage builds. 

This turnkey solution delivers a battle-tested, highly performant, asynchronous FastAPI backend designed to scale cleanly from day one. Complete with type safety, dependency injection, Alembic database migrations, and a containerized PostgreSQL setup, this product lets developers skip the infrastructure setup phase and immediately focus on building core business logic.

---

## 2. Quick Start & Core Concepts

Get your backend running locally in under 60 seconds with Docker Compose.

### Prerequisites
*   Docker & Docker Compose (v2.20+)
*   Python 3.11+ (for local development)

### One-Command Setup
```bash
# Clone and spin up containers
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-starter.git
cd fastapi-jwt-docker-starter
cp .env.example .env
docker compose up --build -d
```

### Core Architecture & Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance asynchronous API routing and validation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database queries via `asyncpg`. |
| **Migrations** | Alembic | Version control for database schema evolution. |
| **Authentication** | PyJWT / Passlib (Bcrypt) | Stateless access/refresh token rotation and secure hashing. |
| **Containerization** | Docker & Docker Compose | Isolated, reproducible development and production environments. |

---

## 3. Production Code Patterns & Architecture Examples

Here is the structural blueprint for the codebase. Every file is copy-paste ready and follows strict enterprise Python typing and design patterns.

```
fastapi_backend/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py       # Pydantic Settings
│   │   ├── database.py     # Async session maker
│   │   └── security.py     # JWT & Password hashing
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py         # SQLAlchemy User Model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py         # Pydantic validation schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py         # FastAPI Dependencies
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           └── users.py
│   └── main.py             # FastAPI entrypoint
├── alembic/                # Database migrations
├── Dockerfile              # Multi-stage production build
├── docker-compose.yml      # Local orchestration
├── requirements.txt        # Pinned dependencies
└── .env.example            # Environment template
```

### 3.1. Environment Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise"
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
        env_file=".env", case_sensitive=True, extra="ignore"
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

### 3.2. Asynchronous Database Engine (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
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

### 3.3. JWT Security Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
import jwt
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
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

### 3.4. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 3.5. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    new_user = User(
        email=user_in.email, hashed_password=get_password_hash(user_in.password)
    )
    db.add(new_user)
    await db.flush()

    access_token = create_access_token({"sub": str(new_user.id)})
    refresh_token = create_refresh_token({"sub": str(new_user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

### 3.6. Production Dockerfile (`Dockerfile`)
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

### 3.7. Production Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - .:/app
    environment:
      - POSTGRES_SERVER=db
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   ❌ **Blocking I/O in Async Routes:** Never use synchronous libraries like `requests` or blocking ORM patterns inside async FastAPI endpoints. Use `httpx` or native async drivers (`asyncpg`). Doing so blocks the event loop and completely ruins concurrent performance.
*   ❌ **Hardcoding Secrets:** Storing JWT secret keys or database credentials directly in code. Always leverage Pydantic Settings coupled with isolated `.env` files or orchestration secrets managers.
*   ❌ **Neglecting Session Closures:** Forgetting to close database sessions on error paths will cause connection leaks, eventually exhausting your database connection pool. Use FastAPI's `yield` pattern within `Depends()` to ensure safe lifecycle cleanup.
*   ❌ **Monolithic Docker Images:** Copying source code *before* installing dependencies in your Dockerfile. This breaks layer caching, making subsequent builds sluggish. Always copy `requirements.txt` first.

---

## 5. Performance & Optimization Tips

*   **Uvicorn Worker Scaling:** In production, do not run a single Uvicorn process. Use `--workers N` (where $N = 2 \times \text{number of CPU cores} + 1$) or pair Uvicorn with Gunicorn process managers to scale across multiple CPU cores inside containers.
*   **Connection Pooling:** Adjust SQLAlchemy's pool size parameters (`pool_size` and `max_overflow`) based on your maximum concurrent database load to avoid connection starvation under heavy user traffic.
*   **Response Compression:** Enable GZip middleware in FastAPI (`app.add_middleware(GZipMiddleware, minimum_size=1000)`) to compress large JSON payloads, drastically reducing network latency.
*   **Database Indexing:** Ensure frequently queried fields (such as foreign keys, user emails, and lookup identifiers) have explicit indexes created via SQLAlchemy or Alembic migrations.

---

## 6. Commercial License & Attribution Summary

### Commercial License Agreement
*   **Grant of Rights:** MicroCorp AI grants the purchasing client (or developer) a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, adapt, and deploy this codebase for commercial, personal, or client-facing production applications.
*   **Restrictions:** You may **not** resell, redistribute, sub-license, or open-source this exact boilerplate architecture as a competing digital product template on marketplaces (such as Gumroad, GitHub, or ThemeForest).
*   **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claim, damages, or liability arising from the deployment of this code in production environments.

*© 2026 MicroCorp AI Engineering Division. All rights reserved.*