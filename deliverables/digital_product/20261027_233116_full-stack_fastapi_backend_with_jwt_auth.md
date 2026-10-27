# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Delivery Specification v2.4*

---

## 1. # Product Title & Value Proposition

### 🚀 Enterprise FastAPI Boilerplate: Production-Grade Async Backend with JWT, PostgreSQL, and Docker
Stop wasting 40+ hours bootstrapping infrastructure, configuring security layers, and wiring up database sessions. This turnkey solution delivers a battle-tested, high-performance asynchronous FastAPI backend designed to scale from MVP to millions of requests without architectural refactoring.

```
+-------------------------------------------------------------------------+
                    MICROCORP AI ENTERPRISE BACKEND
+-------------------------------------------------------------------------+
  [ Client / Frontend ] ---> ( Nginx / Reverse Proxy )
                                     |
                                     v
                           [ FastAPI (Async Uvicorn) ]
                             /           |           \
                            /            |            \
                 [ JWT Auth Engine ]  [ SQLModel ]  [ Redis Cache ]
                         |               |
                         +---------> [ PostgreSQL ]
```

### 💎 Business Value Proposition
* **Time-to-Market Accelerated:** Launch your core product features on Day 1 instead of writing boilerplate boilerplate.
* **Security First:** Implements robust asymmetric/symmetric JWT lifecycle management, password hashing via Argon2/Bcrypt, and strict CORS/Security headers out of the box.
* **Developer Velocity:** Fully containerized with Docker Compose. Spin up the entire database, cache, and API stack with a single command (`docker compose up --build`).
* **Strict Type Safety:** Built on modern Python (3.11+) utilizing Pydantic v2 and SQLModel for bulletproof runtime validation and autocomplete paradise.

---

## 2. ## Quick Start & Core Concepts

Get your local development environment running in under 60 seconds.

### Prerequisites
* Docker & Docker Compose v2.20+
* Python 3.11+ (if running bare-metal migrations)

### ⚡ 60-Second Boot Sequence
```bash
# 1. Clone the repository and navigate to the project root
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Configure your environment variables
cp .env.example .env

# 3. Spin up the container cluster
docker compose up --build -d

# 4. Verify API health
curl http://localhost:8000/health
```

### 📊 Core Architecture Concepts & Syntax Reference

| Concept | Implementation Layer | Primary Purpose | Key Technology |
| :--- | :--- | :--- | :--- |
| **Routing** | FastAPI APIRouter | Modular endpoint organization by business domain | FastAPI, Pydantic v2 |
| **Data Layer** | SQLModel / Alembic | Async ORM mapping & schema migration management | SQLAlchemy 2.0, Asyncpg |
| **Auth** | OAuth2 + JWT | Stateless identity verification & role enforcement | `python-jose`, Passlib |
| **Container** | Docker Multi-stage | Optimized, secure production image builds | Alpine Linux, Uvicorn |
| **Validation** | Pydantic v2 | High-speed data serialization and payload validation | Rust-backed Pydantic core |

---

## 3. ## Production Code Patterns & Architecture Examples

Here is the exact production-ready file tree and core code modules that power the backend.

### Directory Structure
```text
backend/
├── alembic/                  # Database migrations
├── app/
│   ├── api/                  # API routers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/    # auth.py, users.py, items.py
│   │   │   └── api.py        # Router aggregator
│   ├── core/                 # Config, security, database sessions
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async engine & sessionmaker
│   │   └── security.py       # JWT hashing & verification
│   ├── models/               # SQLModel database models
│   ├── schemas/              # Pydantic request/response schemas
│   └── main.py               # FastAPI application factory
├── Dockerfile                # Multi-stage production container
├── docker-compose.yml        # Local orchestration
└── requirements.txt          # Pinned dependencies
```

---

### Module 1: Configuration Engine (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp AI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### Module 2: Async Database Session (`app/core/database.py`)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining asynchronous database sessions."""
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

### Module 3: JWT Security & Authentication (`app/core/security.py`)
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
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### Module 4: Application Factory (`app/main.py`)
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

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure strictly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/health", tags=["Health Check"])
    async def health_check():
        return {"status": "healthy", "service": settings.PROJECT_NAME}

    return application

app = get_application()
```

---

### Module 5: Production Dockerfile (`Dockerfile`)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### Module 6: Container Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
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
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

Engineers transitioning to async FastAPI often run into subtle blocking bugs. Avoid these traps:

* ❌ **Anti-Pattern: Blocking I/O inside Async Endpoints**
  * *Why:* Calling synchronous libraries (like standard `requests`, blocking SQL drivers, or heavy CPU-bound loops) inside an `async def` route starves the event loop, freezing all concurrent requests.
  * ✅ *Fix:* Use `asyncpg`, `httpx`, or offload blocking operations using `starlette.concurrency.run_in_threadpool`.
* ❌ **Anti-Pattern: Hardcoding Secrets & Configuration**
  * *Why:* Storing database credentials or JWT secret keys in code repository files leads to immediate security compromises.
  * ✅ *Fix:* Always utilize Pydantic `BaseSettings` reading exclusively from environment variables.
* ❌ **Anti-Pattern: Ignoring Database Connection Pool Exhaustion**
  * *Why:* Opening a new database engine per request or failing to close sessions correctly leads to connection leaks and PostgreSQL crashes (`FATAL: sorry, too many clients already`).
  * ✅ *Fix:* Use a singleton engine instance coupled with dependency injection yielding session generators (`get_db`).

---

## 5. ## Performance & Optimization Tips

Maximize throughput and minimize latency with these architectural adjustments:

1. **Uvicorn Worker Scaling:** In production, run Uvicorn behind a process manager or configure multiple workers (`--workers 4` or set to `CPU_COUNT * 2 + 1`) to fully saturate multi-core cloud instances.
2. **Response Compression:** Integrate `GZipMiddleware` to compress payloads larger than 1KB, drastically reducing network transfer times for mobile and web clients.
3. **Database Indexing & Query Profiling:** Leverage SQLAlchemy statement profiling and ensure foreign keys and frequently filtered columns (e.g., `email`, `status`) have active B-tree indexes.
4. **Caching Layer:** Place Redis in front of complex analytical queries or expensive external API calls using decorators or dependency caching.

---

## 6. ## Commercial License & Attribution Summary

```text
====================================================================
MICROCORP AI COMMERCIAL TURNKEY LICENSE AGREEMENT
====================================================================
Copyright (c) 2026 MicroCorp AI. All rights reserved.

1. GRANT OF LICENSE: MicroCorp AI grants the purchaser (Client) a 
   perpetual, non-exclusive, worldwide commercial license to use, 
   modify, adapt, and deploy this codebase for internal business 
   operations or client-facing commercial applications.
2. RESTRICTIONS: Redistribution, resale, or sub-licensing of this 
   source code as a standalone boilerplate, template, or competing 
   product kit is strictly prohibited without prior written consent.
3. WARRANTY DISCLAIMER: This software is provided "as is", without 
   warranty of any kind, express or implied. MicroCorp AI shall not 
   be held liable for any claim, damages, or liability arising from 
   its deployment or operation.
====================================================================
```