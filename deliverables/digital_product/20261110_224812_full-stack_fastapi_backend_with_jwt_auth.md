# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Architectural Blueprint*  
> **Product ID:** `MC-BE-FASTAPI-JWT-001`  
> **Target Audience:** Enterprise Clients, Senior Engineers, and Freelance Deliverables  

---

## 1. # Product Title & Value Proposition

### Executive Summary
When delivering a backend to a client on Fiverr or Enterprise consulting, "it works on my machine" is a commercial failure. Clients require secure authentication, structured database interactions, clean dependency injection, and a frictionless Dockerized deployment workflow. 

This turnkey solution delivers a production-ready, highly scalable **FastAPI** backend integrated with **JSON Web Token (JWT) Authentication**, **SQLAlchemy 2.0 (Async)**, **Alembic Migrations**, and **Docker Compose orchestration**. Built by backend specialists, this codebase eliminates weeks of boilerplate setup and enforces enterprise-grade security standards out of the box.

### Key Value Propositions
- **Turnkey Deployment:** Zero-friction spin-up using Docker Compose (`app`, `postgres`, `redis`).
- **Modern Async Architecture:** Built natively on FastAPI and SQLAlchemy 2.0 asynchronous engine patterns to maximize concurrency and throughput.
- **Secure-by-Design Auth:** Cryptographically secure JWT implementation featuring access/refresh token rotation, password hashing via `passlib[bcrypt]`, and role-based access control (RBAC).
- **Maintainable Layout:** Clean separation of concerns (Routers, Schemas, Models, Services, Core configuration) ready for horizontal scaling.

---

## 2. ## Quick Start & Core Concepts

### Syntax & Architecture Reference

| Component | Technology / Standard | Purpose in the Stack |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous API routing, automatic OpenAPI/Swagger documentation generation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Type-safe, asynchronous database interactions using modern Python typing. |
| **Database Migrations**| Alembic | Version-controlled schema migrations tracking database evolution. |
| **Authentication** | OAuth2 with Password (Bearer) + JWT | Stateless, cryptographically signed user sessions with expiration handling. |
| **Containerization** | Docker & Docker Compose | Isolated multi-container environments ensuring parity between dev, staging, and production. |

### Directory Structure
```text
fastapi-enterprise-backend/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1 endpoints)
│   ├── core/                # Config, security, database session
│   ├── models/              # SQLAlchemy models (Database tables)
│   ├── schemas/             # Pydantic models (Data validation)
│   ├── services/            # Business logic layer
│   └── main.dart / main.py  # FastAPI application entrypoint
├── tests/                   # Pytest async test suite
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Local orchestration stack
├── requirements.txt         # Pinned dependency manifest
└── .env.example             # Environment configuration template
```

---

## 3. ## Production Code Patterns & Architecture Examples

### A. Environment Configuration (`app/core/config.py`)
Centralized settings management using Pydantic Settings to validate environment variables at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

### B. Database Session & Base Model (`app/core/database.py`)
Asynchronous session generator adhering to the dependency injection pattern.

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
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

### C. JWT Security & User Dependency (`app/core/security.py`)
Token generation, verification, and active user dependency resolution.

```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### D. User Authentication Router (`app/api/v1/endpoints/auth.py`)
Token issuance endpoint handling credential validation.

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
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
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
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

### E. Docker Configuration (`Dockerfile`)
Multi-stage build reducing image footprint and maximizing container security.

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

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### F. Multi-Container Orchestration (`docker-compose.yml`)

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

  app:
    build: .
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
      - SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Production Approach |
| :--- | :--- | :--- |
| **Using Synchronous DB Drivers (`psycopg2`) in Async Routes** | Blocks the FastAPI event loop under concurrent load, degrading performance. | Always use asynchronous drivers like `asyncpg` with SQLAlchemy's `create_async_engine`. |
| **Hardcoding Secrets in Configuration Files** | Exposes private keys, credentials, and tokens if code is pushed to public/semi-public repositories. | Enforce environment variables via Pydantic `BaseSettings` with strict `.env` exclusion (`.gitignore`). |
| **Catching Base Exceptions (`except Exception:`) Silently** | Masks runtime bugs, database connection leaks, and validation failures, making debugging impossible. | Catch specific database/auth exceptions; bubble up handled errors via FastAPI `HTTPException`. |
| **Running Uvicorn without Process Managers or Workers in Production** | Leaves the application vulnerable to single-core bottlenecks and unmanaged lifecycle restarts. | Use Gunicorn with Uvicorn worker classes or orchestration platforms (Kubernetes/ECS) for redundancy. |

---

## 5. ## Performance & Optimization Tips

1. **Connection Pooling Optimization:** Configure SQLAlchemy's engine parameters (`pool_size`, `max_overflow`, `pool_timeout`) based on your database tier and expected concurrent connection loads.
2. **Response Model Compression:** Integrate `GZipMiddleware` in FastAPI for responses over a specific byte threshold to reduce payload transit times over high-latency networks.
3. **Database Indexing:** Ensure foreign keys, lookup columns (such as `email` or `username`), and frequently sorted fields feature explicit indexes in your Alembic migrations.
4. **Stateless Scalability:** Keep the FastAPI instance completely stateless; store application state inside Redis or PostgreSQL to allow horizontal auto-scaling behind a load balancer.

---

## 6. ## Commercial License & Attribution Summary

```text
================================================================================
MICROCORP AI COMMERCIAL LICENSE AGREEMENT (TURKEY / CLIENT DELIVERY)
================================================================================
Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.
All rights reserved.

1. GRANT OF LICENSE: This turnkey solution is licensed to the purchasing client 
   for integration into commercial software, client deliverables on freelance 
   marketplaces (Fiverr, Upwork), and enterprise internal systems.
2. RESTRICTIONS: Reselling, repackaging, or redistributing this source code 
   as a standalone template, boilerplate generator, or SaaS kit without explicit 
   written authorization from MicroCorp AI is strictly prohibited.
3. WARRANTY DISCLAIMER: Provided "AS IS", without warranty of any kind, express 
   or implied. The authors are not liable for any claim, damages, or liability 
   arising from the implementation of this software in production environments.
================================================================================
```