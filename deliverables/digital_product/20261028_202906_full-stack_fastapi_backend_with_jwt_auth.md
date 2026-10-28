# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Architectural Blueprint & Delivery Kit*  
> **Target Audience:** Enterprise Clients, Senior Engineers, and Freelance Delivery Teams  
> **Product Code:** MC-FASTAPI-JWT-001

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Blueprint: JWT Authentication & Dockerized Infrastructure

Building a production-grade backend from scratch requires stitching together dozens of independent technologies: database ORMs, asynchronous drivers, token-based security, environment validation, container orchestration, and automated migrations. Getting these integrations wrong leads to security vulnerabilities, memory leaks, and scaling bottlenecks.

This digital product provides a **fully tested, turnkey FastAPI backend architecture** designed for immediate deployment to production environments (AWS, GCP, DigitalOcean, or private VPS). 

### What You Get:
* **Zero-Config-to-Scale Architecture:** Clean, modular directory layout separating routing, database access, business logic, and security schemas.
* **Cryptographically Secure Auth Engine:** Token-based JSON Web Token (JWT) implementation using industry-standard `bcrypt` password hashing and `python-jose` expiration management.
* **Asynchronous Database Layer:** High-performance database operations powered by SQLModel/SQLAlchemy 2.0 with native `async/await` syntax and Alembic database migrations.
* **Production Containerization:** Optimized multi-stage Dockerfiles and a fully orchestrated `docker-compose.yml` stack featuring PostgreSQL and automated health checks.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
The backend follows a strict Layered Service Pattern to decouple HTTP transport logic from database operations and business rules.

```
[ Client Request ] 
       │
       ▼
[ FastAPI Routers ] (Input validation via Pydantic v2)
       │
       ▼
[ Security Dependencies ] (JWT Decryption & RBAC Checks)
       │
       ▼
[ Service / CRUD Layer ] (Business Logic & SQLModel Queries)
       │
       ▼
[ PostgreSQL Database ] (Async Engine via asyncpg)
```

### Core Technology Stack & Configuration Syntax

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous REST API framework |
| **Data Validation** | Pydantic v2 | `2.6+` | Runtime data parsing and settings management |
| **ORM / Database** | SQLModel / SQLAlchemy | `0.0.16+` | Type-safe database mapping and async sessions |
| **Migrations** | Alembic | `1.13+` | Database schema migration management |
| **Authentication** | python-jose & passlib | Latest | JWT generation, verification, and password hashing |
| **Containerization** | Docker & Compose | Latest | Reproducible runtime environments |

---

## 3. Production Code Patterns & Architecture Examples

### 📁 Project Directory Structure
```text
fastapi-production-kit/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application factory & middleware
│   ├── config.py               # Pydantic BaseSettings environment parsing
│   ├── database.py             # Async engine & session factories
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # SQLModel database tables
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py             # Pydantic request/response DTOs
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Reusable FastAPI dependencies (DB, Current User)
│   │   └── v1/
│   │       ├── api.py          # API router aggregation
│   │       endpoints/
│   │           ├── auth.py     # Login, token refresh
│   │           └── users.py    # User registration & profile management
│   └── core/
│       ├── __init__.py
│       └── security.py         # Password hashing & JWT creation
├── alembic/                    # Database migrations
├── Dockerfile                  # Multi-stage production image
├── docker-compose.yml          # Local development orchestration
├── requirements.txt            # Pinned Python dependencies
└── .env.example                # Template environment variables
```

---

### ⚙️ 1. Configuration Engine (`app/config.py`)
Uses Pydantic v2 `BaseSettings` to enforce type safety and strict environment variable validation at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    def model_post_init(self, __context) -> None:
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### 🗄️ 2. Database Asynchronous Session Management (`app/database.py`)
Configures the SQLAlchemy async engine and provides a dependency injection generator for request-scoped sessions.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
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
    """Dependency function that yields db sessions per request."""
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

### 👤 3. Database Models (`app/models/user.py`)
Type-safe database definition using SQLModel.

```python
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
```

---

### 🔐 4. Security & Cryptography Engine (`app/core/security.py`)
Handles hashing with `passlib` and JWT issuance/validation using `python-jose`.

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 🔌 5. Request Dependencies & RBAC (`app/api/deps.py`)
Extracts and validates the JWT Bearer token from incoming requests and fetches the current user from the database.

```python
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == uuid.UUID(token_data.sub)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user


def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

---

### 🚀 6. Application Factory (`app/main.py`)
Initializes FastAPI, adds middleware (CORS, trusted hosts), and registers the main API router.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.config import settings

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)
    return application

app = get_application()
```

---

### 🐳 7. Infrastructure Deployment

#### `Dockerfile` (Multi-Stage Production Build)
```dockerfile
# Stage 1: Build Dependencies
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

#### `docker-compose.yml` (Local Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
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
      - PROJECT_NAME=Enterprise Service
      - SECRET_KEY=supersecretkeychangeinproduction123!@#
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=production_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints**
   * *Anti-Pattern:* Calling blocking libraries (like standard `requests` or synchronous database drivers) directly inside an `async def` function. This halts the event loop and destroys concurrent throughput.
   * *Solution:* Use async drivers (`asyncpg`, `httpx`) or wrap blocking operations using `run_in_threadpool`.

2. **Hardcoding Secret Keys & Configuration**
   * *Anti-Pattern:* Defining JWT secrets or database connection strings inline in code files.
   * *Solution:* Always leverage Pydantic `BaseSettings` reading exclusively from environment variables or secure secret managers (AWS Secrets Manager, HashiCorp Vault).

3. **Session Leakage & Missing Rollbacks**
   * *Anti-Pattern:* Opening database sessions manually inside route handlers without ensuring they close during unhandled exceptions.
   * *Solution:* Always use FastAPI's dependency injection generator pattern (`Yield` with `try/except/finally` blocks as shown in `app/database.py`).

4. **Catching Generic Exceptions Globally**
   * *Anti-Pattern:* Using `except Exception:` without logging or re-raising, hiding critical bugs and returning ambiguous `500 Internal Server Error` responses.
   * *Solution:* Handle specific domain exceptions and let FastAPI's global exception handler catch unhandled errors cleanly.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production containers, run Uvicorn with multiple worker processes mapped to CPU cores: `--workers 4` (or `$(nproc)`).
* **Connection Pooling:** Tune `pool_size` and `max_overflow` parameters on your SQLAlchemy async engine based on your database instance limits and expected concurrent load.
* **Response Model Optimization:** Always specify `response_model` in your FastAPI route decorators (`@app.get("/", response_model=UserRead)`) to leverage Pydantic's C-compiled serialization speed and strip unwanted internal database fields (like hashes).
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (`email`, `username`) have explicit database indexes defined in your SQLModel definitions.

---

## 6. Commercial License & Attribution Summary

```text
================================================================================
MICROCORP AI COMMERCIAL LICENSE AGREEMENT (TEMPLATE)
================================================================================
Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:
1. Commercial client deployment rights are granted in perpetuity for the 
   purchasing entity.
2. This copyright notice and attribution header must remain intact within 
   source code files.
3. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
================================================================================
```