# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Commercial Assets*  
> **Product ID:** `MC-BE-FASTAPI-JWT-001`  
> **Target Audience:** Enterprise Clients, Senior Engineers, Full-Stack Developers  

---

## 1. # Product Title & Value Proposition

### Product Title
**The Enterprise-Grade FastAPI & PostgreSQL Boilerplate with Secure JWT Authentication & Dockerized Orchestration**

### Value Proposition
Building modern, high-throughput microservices requires a solid foundation. This turnkey backend architecture eliminates weeks of boilerplate setup by providing a production-ready, highly secure, and horizontally scalable API template. 

Engineered strictly following industry best practices, it couples **FastAPI** (for async performance and automatic OpenAPI documentation) with **SQLAlchemy 2.0** (async ORM), **Alembic** (database migrations), **Pydantic v2** (strict data validation), and **JWT-based stateless authentication** with refresh token rotation. Fully containerized with **Docker Compose**, it deploys instantly across local development, staging, and production environments.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview & Technology Stack
| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous REST API routing and auto-docs |
| **Data Validation** | Pydantic v2 | Runtime type checking, settings management, and request/response schemas |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database interactions and schema definition |
| **Migrations** | Alembic | Version-controlled database schema evolution |
| **Authentication** | python-jose & passlib | Cryptographic JWT creation, verification, and bcrypt password hashing |
| **Containerization** | Docker & Compose | Multi-container orchestration for API, Database, and Adminer |

### 5-Minute Quick Start

1. **Clone the Repository & Configure Environment**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Containers via Docker Compose**
   ```bash
   docker compose up --build -d
   ```

3. **Run Database Migrations**
   ```bash
   docker compose exec api alembic upgrade head
   ```

4. **Verify the Installation**
   * API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   * Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
.
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API route handlers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/   # auth.py, users.py, items.py
│   │   │   └── router.py
│   ├── core/                # Configuration, security, database sessions
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/              # SQLAlchemy database models
│   │   └── user.py
│   ├── schemas/             # Pydantic validation schemas
│   │   └── user.py
│   └── main.py              # FastAPI application entrypoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

### 1. Environment & Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp AI FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

---

### 2. Database Session Management (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

### 3. Cryptography & JWT Security (`app/core/security.py`)
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
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### 4. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

---

### 5. Pydantic Schemas (`app/schemas/user.py`)
```python
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters required")


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

---

### 6. Authentication API Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### 7. FastAPI Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 8. Docker Configuration (`Dockerfile`)
```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 9. Container Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: microcorp_postgres
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
    container_name: microcorp_fastapi
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-access-key-change-in-production
      - JWT_REFRESH_SECRET_KEY=super-secret-refresh-key-change-in-production
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous DB Drivers with Async FastAPI Routes**
   * *Anti-Pattern:* Utilizing standard `psycopg2` or standard SQLAlchemy Sessions inside `async def` route handlers, which blocks the event loop.
   * *Correction:* Always leverage `asyncpg` with SQLAlchemy's `AsyncSession` to maintain true asynchronous non-blocking throughput.

2. **Hardcoding Secrets and Configurations**
   * *Anti-Pattern:* Declaring JWT secrets, database connection strings, and API keys directly inside application files.
   * *Correction:* Strictly use Pydantic-Settings coupled with environmental variables loaded through `.env` containers.

3. **Failing to Handle Database Rollbacks on Exception**
   * *Anti-Pattern:* Leaving database transactions open or uncommitted when an internal error interrupts execution.
   * *Correction:* Wrap session yields in strict `try/except` blocks that execute explicit `session.rollback()` operations upon failure.

4. **Storing State in Application Memory**
   * *Anti-Pattern:* Keeping authenticated tokens or active session data inside Python dictionaries or local variables within container memory.
   * *Correction:* Maintain entirely stateless architectures utilizing signed JWTs and centralized session caches (such as Redis) for distributed invalidation.

---

## 5. ## Performance & Optimization Tips

* **Connection Pooling:** Tune your SQLAlchemy engine `pool_size` and `max_overflow` settings relative to your database server CPU core allocation and maximum expected concurrent requests.
* **Gunicorn + Uvicorn Workers:** For bare-metal or single-instance Linux deployments, scale Uvicorn via Gunicorn process managers to fully saturate multi-core processors:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Payload Compression:** Integrate Starlette's `GZipMiddleware` to automatically compress large JSON responses payloads over the network:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure foreign keys and high-frequency search columns (such as `users.email`) are explicitly indexed within your Alembic migration specifications.

---

## 6. ## Commercial License & Attribution Summary

```text
====================================================================
MICROCORP AI COMMERCIAL SOFTWARE LICENSE AGREEMENT
Version 1.0 - Enterprise Tier
====================================================================
Copyright (c) 2026 MicroCorp AI. All rights reserved.

1. GRANT OF LICENSE: MicroCorp AI grants the Purchaser (Fiverr Client / 
   Internal Enterprise Engineering Team) a perpetual, worldwide, 
   non-exclusive, non-transferable license to modify, deploy, scale, 
   and distribute this backend software boilerplate within commercial 
   applications, SaaS platforms, and internal microservices.

2. RESTRICTIONS: Purchaser shall NOT resell, sublicense, or distribute 
   this exact source code package as a standalone boilerplate, open-source 
   template, or competing digital product kit on marketplaces such as 
   Gumroad, GitHub Sponsors, or Envato.

3. DISCLAIMER: THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF 
   ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES 
   OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
====================================================================
```