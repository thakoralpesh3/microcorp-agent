# Enterprise FastAPI Backend: JWT Auth, PostgreSQL, & Docker Setup
**Product Type:** Full Turnkey Solution for Fiverr Client  
**Author:** Backend Architect 🏗️ | MicroCorp AI Engineering Division

---

## 1. # Product Title & Value Proposition

### Title
**FastAPI Production-Grade Boilerplate: Enterprise Architecture, Asynchronous PostgreSQL, Secure JWT Authentication, and Multi-Stage Docker Deployment.**

### Value Proposition
Building a modern web application requires spinning up dozens of boilerplate configurations: CORS middleware, database connection pools, secure password hashing, JWT token rotation, structured logging, and containerization. 

This turnkey solution eliminates weeks of repetitive setup. It provides a production-ready, highly scalable, and secure backend foundation built entirely on asynchronous Python standards (FastAPI + SQLAlchemy 2.0 + Pydantic v2). Designed for senior developers and agency deliverables, this package guarantees a clean separation of concerns, robust type safety, and zero-configuration containerization out of the box.

---

## 2. ## Quick Start & Core Concepts

### System Architecture Overview
The project follows a modified Domain-Driven Clean Architecture pattern designed to keep routing logic completely decoupled from database queries and business logic.

```
├── app/
│   ├── api/          # API routers (v1 endpoints)
│   ├── core/         # Config, security, database session setup
│   ├── models/       # SQLAlchemy ORM database models
│   ├── schemas/      # Pydantic data validation schemas
│   ├── services/     # Business logic & external integrations
│   └── main.er.py    # FastAPI application entrypoint
├── alembic/          # Database migrations
├── Dockerfile        # Multi-stage production container
├── docker-compose.yml# Local orchestration (App + DB)
└── requirements.txt  # Pinned dependency manifest
```

### Syntax & Component Reference Table

| Component | Library / Tool | Purpose & Architectural Role |
| :--- | :--- | :--- |
| **Web Framework** | `FastAPI` | Asynchronous routing, automatic OpenAPI/Swagger generation, dependency injection. |
| **Data Validation** | `Pydantic v2` | Runtime data parsing, serialization, and environment configuration management. |
| **ORM / Database** | `SQLAlchemy 2.0` | Asynchronous ORM (`async_sessionmaker`), type-safe querying against PostgreSQL. |
| **Migrations** | `Alembic` | Version control for database schemas. |
| **Authentication** | `python-jose` & `passlib` | JWT generation/verification and bcrypt password hashing. |
| **Containerization**| `Docker (Multi-stage)`| Lightweight, secure production images using slim Python base runners. |

---

## 3. ## Production Code Patterns & Architecture Examples

### 3.1. Application Entrypoint (`app/main.py`)
Sets up CORS policies, exception handling, and lifespan database connection checks.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB connection pools or cache layers here
    print("🚀 Starting up MicroCorp FastAPI Engine...")
    yield
    # Shutdown: Clean up connections
    print("🛑 Shutting down engine...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}
```

### 3.2. Configuration Management (`app/core/config.py`)
Leverages Pydantic v2 BaseSettings for strict environment variable parsing.

```python
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Union[str, None] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Union[str, None], values) -> str:
        if isinstance(v, str):
            return v
        data = values.data
        return f"postgresql+asyncpg://{data.get('POSTGRES_USER')}:{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}/{data.get('POSTGRES_DB')}"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
```

### 3.3. Asynchronous Database Engine (`app/core/database.py`)
Configures the async session factory using SQLAlchemy 2.0.

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    future=True,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

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

### 3.4. Security & JWT Authentication (`app/core/security.py`)
Handles password hashing and JWT token issuance/decryption.

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
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### 3.5. Protected User Dependency (`app/api/deps.py`)
Extracts and validates bearer tokens, fetching the active user from the database.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = payload.get("sub")
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == int(token_data)))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

### 3.6. Production Dockerfile (`Dockerfile`)
Multi-stage build reducing attack surface and final image size.

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

# Stage 2: Runtime Environment
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.7. Local Orchestration (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    restart: always

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=MicroCorp API
      - SECRET_KEY=supersecretkeychangemeinproduction
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
      - BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous DB Calls in Async Paths:** Using standard `psycopg2` or synchronous SQLAlchemy sessions inside async `asyncdef` paths will block the event loop, completely destroying concurrency performance. Always use `asyncpg` and `AsyncSession`.
2. **Hardcoding Secrets:** Storing database passwords or JWT secret keys directly inside source code. Always enforce environment injection via Pydantic `BaseSettings`.
3. **Not Expiring JWTs:** Issuing tokens without an expiration date (`exp`) means compromised tokens remain valid indefinitely. Always include strict expiration limits (e.g., 15-30 minutes for access tokens).
4. **Unbounded Connection Pools:** Leaving SQLAlchemy pool sizes unconfigured can cause connection exhaustion under high traffic loads. Set explicit `pool_size` and `max_overflow` parameters.
5. **Catching Generic Exceptions blindly:** Using `except Exception:` without rolling back the active database transaction leads to broken session states and locks.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a load balancer (like Nginx or AWS ALB), run Uvicorn with multiple worker processes managed by Gunicorn or optimized via process managers:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (like `email` in User models) have explicit database indexes (`index=True`).
* **Response Serialization Tuning:** For high-throughput endpoints returning large lists of records, consider using `orjson` response classes instead of standard library json parsing for up to 10x serialization speedups:
  ```python
  from fastapi.responses import ORJSONResponse
  app = FastAPI(default_response_class=ORJSONResponse)
  ```
* **Connection Pooling tuning:** Tune PostgreSQL `max_connections` in tandem with your container pool sizes to ensure efficient socket reuse without hitting database limits.

---

## 6. ## Commercial License & Attribution Summary

### Terms of Commercial Distribution
* **Client Handover Rights:** This software template is fully licensed for direct commercial resale, client delivery on platforms like Fiverr or Upwork, and integration into proprietary closed-source SaaS products.
* **Attribution Waiver:** You are not required to display MicroCorp AI attribution within production API responses or user interfaces.
* **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. The author and MicroCorp AI accept zero liability for infrastructure downtime, security vulnerabilities arising from altered configurations, or database loss.

---
*Built with precision by the Backend Engineering Division — MicroCorp AI.*