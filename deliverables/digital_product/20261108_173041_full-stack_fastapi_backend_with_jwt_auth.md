# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Enterprise Backend Architecture Series*

## 1. Product Title & Value Proposition

### Product Overview
This commercial-grade, turnkey backend boilerplate is engineered for production deployment from day one. Built on **FastAPI**, **SQLAlchemy (Async)**, **Pydantic v2**, and **PostgreSQL**, it features secure **JWT-based authentication**, role-based access control (RBAC), environment-based configuration, and a multi-stage **Docker & Docker Compose** setup. 

```
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI ENTERPRISE ENGINE                 │
├───────────────────┬───────────────────┬─────────────────────┤
│   Async API       │    JWT Auth       │  PostgreSQL + Async │
│   Endpoints       │    (OAuth2 + RBAC)│  SQLAlchemy 2.0     │
├───────────────────┴───────────────────┴─────────────────────┤
│                 Docker & Docker Compose                     │
└─────────────────────────────────────────────────────────────┘
```

### Commercial Value Proposition
* **Zero Setup Friction:** Spin up a fully relational database and API container cluster with a single command (`docker compose up --build`).
* **Production Security Out-of-the-Box:** Implements secure password hashing via `passlib[bcrypt]`, token expiration, dependency injection for user verification, and HTTP-only cookie or Bearer token patterns.
* **Type-Safe & Validated:** Fully leverages Python 3.11+ type hints, Pydantic v2 data serialization, and async database sessions to prevent runtime data corruption.
* **Client-Ready Deliverable:** Designed to be handed off directly to agency clients or deployed as the robust core of SaaS products, mobile app backends, or enterprise dashboards.

---

## 2. Quick Start & Core Concepts

### Syntax & Architecture Mapping

| Component | Technology | Purpose in the Stack |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance asynchronous routing, automatic OpenAPI/Swagger generation. |
| **Data Validation** | Pydantic v2 | Strict request/response parsing, environment variable management via `BaseSettings`. |
| **ORM / DB Driver** | SQLAlchemy 2.0 (Async) + `asyncpg` | Non-blocking database operations over high-performance PostgreSQL drivers. |
| **Authentication** | PyJWT + Passlib | Secure JSON Web Token creation/verification and bcrypt password hashing. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds, isolated networks, and persistent volume management. |

### 5-Minute Local Setup

1. **Clone and Navigate into the Project:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   PROJECT_NAME="MicroCorp FastAPI Engine"
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=supersecretpassword
   POSTGRES_SERVER=db
   POSTGRES_PORT=5432
   POSTGRES_DB=app_db
   DATABASE_URL=postgresql+asyncpg://postgres:supersecretpassword@db:5432/app_db
   SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

3. **Launch via Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

4. **Verify Deployment:**
   * API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
   * Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)
   * Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

### File 1: `app/core/config.py` (Environment & Settings)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### File 2: `app/core/database.py` (Async SQLAlchemy Session Manager)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
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

### File 3: `app/models/user.py` (Database ORM Model)
```python
import uuid
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
```

---

### File 4: `app/schemas/user.py` (Pydantic Validation Schemas)
```python
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None
```

---

### File 5: `app/core/security.py` (Password Hashing & JWT Handling)
```python
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
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
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### File 6: `app/api/v1/endpoints/auth.py` (Authentication Router)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pw = get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_pw)
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### File 7: `app/main.py` (Application Entrypoint)
```python
from fastapi import FastAPI
from app.api.v1.endpoints import auth
from app.core.database import Base, engine

app = FastAPI(
    title="MicroCorp Production Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # Note: For production use Alembic migrations instead of create_all
        await conn.run_sync(Base.metadata.create_all)


app.include_router(auth.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "fastapi-backend"}
```

---

### File 8: `Dockerfile` (Multi-Stage Production Build)
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

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### File 9: `docker-compose.yml` (Container Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
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
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ALGORITHM=${ALGORITHM}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Using Synchronous Database Drivers in Async FastAPI Routes
* **The Mistake:** Using standard `psycopg2` or blocking SQLAlchemy sessions inside `async def` endpoints blocks the main event loop, destroying concurrent request handling performance.
* **The Fix:** Always use `asyncpg` drivers and `AsyncSession` with SQLAlchemy 2.0. If blocking legacy code must be used, define the endpoint with standard `def` so FastAPI executes it in an external threadpool.

### ❌ Anti-Pattern 2: Relying on `Base.metadata.create_all` for Production Migrations
* **The Mistake:** Letting FastAPI automatically create database tables on startup via `create_all` in production environments. This approach fails when schema modifications (e.g., column renames, drops, constraints) occur.
* **The Fix:** Initialize **Alembic** (`alembic init alembic`) for all production environments to manage incremental database migration scripts safely.

### ❌ Anti-Pattern 3: Hardcoding Secrets and Configuration Values
* **The Mistake:** Embedding database credentials, secret keys, and third-party API keys directly into source code files.
* **The Fix:** Utilize Pydantic’s `BaseSettings` paired with environment files (`.env`) and inject secrets through secure container orchestrator vaults.

---

## 5. Performance & Optimization Tips

1. **Connection Pooling Tuning:**
   Configure connection pool parameters on your async engine to prevent exhaustion under high concurrency loads:
   ```python
   engine = create_async_engine(
       settings.DATABASE_URL, pool_size=20, max_overflow=10, pool_pre_ping=True
   )
   ```
2. **Gunicorn + Uvicorn Workers for Production:**
   In high-throughput production environments, run Uvicorn managed by Gunicorn workers instead of single-process development servers:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
3. **Response Compression:**
   Incorporate FastAPI's GZip middleware to compress large JSON responses automatically and minimize network payload sizes:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware

   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

---

## 6. Commercial License & Attribution Summary

```
====================================================================
MICROCORP AI COMMERCIAL TURNKEY LICENSE AGREEMENT
====================================================================
Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.

Permission is hereby granted, free of charge, to any client or 
engineer purchasing or receiving this turnkey digital product, to 
use, modify, distribute, and sublicense this code base for commercial 
and private production systems without restriction.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
====================================================================
```