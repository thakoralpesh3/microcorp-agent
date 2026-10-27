# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*A Turnkey Enterprise Boilerplate for High-Performance Microservices*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Architecture
Stop wasting weeks scaffolding authentication, database connections, and Dockerfiles for every new client project. This enterprise-grade boilerplate delivers a robust, secure, and horizontally scalable backend built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL**, **Pydantic v2**, and **JWT Authentication**, all containerized with **Docker Compose**.

#### **Value Proposition Matrix**
| Metric / Benefit | Traditional Setup | MicroCorp AI Turnkey Boilerplate |
| :--- | :--- | :--- |
| **Time to First API Call** | 3–5 Days | **< 5 Minutes** |
| **Security Standards** | Manual hashing, fragile tokens | **Bcrypt + RS256/HS256 JWT + CORS + Rate Limiting** |
| **Database Layer** | Synchronous, blocks event loop | **100% Asynchronous SQLAlchemy 2.0 + Alembic Migrations** |
| **Containerization** | Single bloated Dockerfile | **Multi-stage, distroless-ready Docker + Hot-reload Dev Env** |
| **Client Handoff Readiness**| Low (Requires cleanup) | **High (Enterprise documentation & modular layout)** |

---

## 2. Quick Start & Core Concepts

### System Architecture Flow
```
[ Client / Frontend ] 
       │ (HTTPS / Bearer Token)
       ▼
[ Nginx / Reverse Proxy ] (Optional)
       │
       ▼
[ FastAPI Application Container ] 
       ├── /api/v1/auth (JWT Issuance & Refresh)
       ├── /api/v1/users (RBAC Protected Endpoints)
       └── Dependency Injection (Async Session, Current User)
       │
       ▼
[ PostgreSQL 16 Container ] (Persistent Volume)
```

### Clean Syntax & Routing Reference
| Component | Module / File | Primary Purpose | Key Syntax Example |
| :--- | :--- | :--- | :--- |
| **App Factory** | `app/main.py` | Initializes FastAPI & middleware | `app = FastAPI(lifespan=lifespan)` |
| **Settings** | `app/core/config.py` | Type-safe environment management | `class Settings(BaseSettings): ...` |
| **Database** | `app/db/session.py` | Async engine & session maker | `async_session = async_sessionmaker(...)` |
| **Security** | `app/core/security.py`| Password hashing & JWT generation | `pwd_context.hash(password)` |
| **Dependencies**| `app/api/deps.py` | Request-scoped DI (Auth & DB) | `async def get_db() -> AsyncGenerator` |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-enterprise-boilerplate/
├── alembic/                  # Database Migrations
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/    # Auth, Users, Health
│   │   │   └── router.py     # API Router Aggregator
│   │   └── deps.py           # FastAPI Dependencies (Auth, DB)
│   ├── core/
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async SQLAlchemy Engine
│   │   └── security.py       # JWT & Hashing utils
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic Data Validation Schemas
│   └── main.py               # Application Entrypoint
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### A. Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    # JWT Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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

### B. Asynchronous Database Engine (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
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

### C. JWT Security & Hashing (`app/core/security.py`)
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
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### D. Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenPayload(sub=username)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == token_data.sub))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### E. Docker Configuration (`Dockerfile`)
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

# Stage 2: Runtime Environment
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

---

### F. Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
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

  backend:
    build: .
    container_name: fastapi_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction123!
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous and Asynchronous ORM Calls**
   * *Anti-Pattern:* Calling blocking database drivers (`psycopg2`) or doing heavy CPU-bound operations inside async FastAPI route handlers, locking the event loop.
   * *Correction:* Always use `asyncpg` with `sqlalchemy.ext.asyncio` and offload CPU-intensive tasks using `run_in_threadpool`.

2. **Hardcoding Secrets or Storing Plaintext Passwords**
   * *Anti-Pattern:* Committing `.env` files or hardcoding `SECRET_KEY` variables directly in code repositories.
   * *Correction:* Use Pydantic's `BaseSettings` with strict environment variable injection and enforce password hashing via `passlib[bcrypt]`.

3. **Ignoring Session Lifecycle Management**
   * *Anti-Pattern:* Opening database connections inside route definitions without explicit context managers, leading to connection leaks and pool exhaustion.
   * *Correction:* Use FastAPI's dependency injection system (`Depends(get_db)`) to guarantee automatic session cleanup and transaction rollbacks on failure.

4. **N+1 Query Performance Traps**
   * *Anti-Pattern:* Accessing un-joined relational attributes inside loops (e.g., iterating through users and accessing `user.profile` one by one).
   * *Correction:* Use SQLAlchemy `.options(selectinload(User.profile))` to fetch related entities in bulk.

---

## 5. Performance & Optimization Tips

* **Connection Pooling:** Adjust `pool_size` and `max_overflow` in your SQLAlchemy engine based on your container resource limits and database tier.
* **Gunicorn + Uvicorn Workers:** For production bare-metal or high-throughput Kubernetes deployments, run Uvicorn managed via Gunicorn workers to maximize CPU core saturation:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Response Compression:** Implement `GZipMiddleware` in `app/main.py` for payloads exceeding 1KB to drastically reduce network bandwidth consumption:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure foreign keys and high-frequency filter columns (like `email`, `is_active`) have explicit database indexes defined in your SQLAlchemy models.

---

## 6. Commercial License & Attribution Summary

```text
================================================================================
MICROCORP AI COMMERCIAL DIGITAL PRODUCT LICENSE
================================================================================
Product: Full-Stack FastAPI Backend with JWT Auth and Docker Setup
Author: Backend Architect, Engineering Division @ The Agency / MicroCorp AI
Grant of Rights: 
  - Purchaser is granted a perpetual, non-exclusive, worldwide license to use,
    modify, adapt, and deploy this codebase for commercial client projects,
    internal enterprise systems, and SaaS startups.
Restrictions:
  - Reselling or redistributing this boilerplate as an isolated template or 
    competing digital product on marketplaces (Gumroad, GitHub, etc.) is strictly 
    prohibited.
Warranty:
  - Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI
    accepts no liability for downtime, security breaches, or data loss incurred 
    through improper deployment.
================================================================================
```