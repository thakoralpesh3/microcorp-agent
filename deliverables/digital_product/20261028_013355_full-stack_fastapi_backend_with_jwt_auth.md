# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture & Infrastructure Kit*  
> **Product ID:** `MC-API-FASTAPI-JWT-004`  
> **Target Audience:** Enterprise Clients, Scale-up Engineering Teams, and High-End Freelance Delivery

---

## 1. Product Title & Value Proposition

### Title
**Enterprise-Grade FastAPI Production Boilerplate: Async Architecture, Secure JWT Authentication, and Multi-Stage Docker Deployment**

### Value Proposition
Building modern, high-throughput microservices requires getting dozens of infrastructure and architectural decisions right on day one. This turnkey backend solution eliminates weeks of boilerplate setup by providing a battle-tested, highly performant FastAPI template. 

Engineered with asynchronous database sessions (SQLAlchemy 2.0), robust stateless JWT authentication with refresh token rotation, strict Pydantic v2 validation, and an optimized production-ready Docker containerization setup, this codebase is designed to scale effortlessly from MVP to millions of requests.

### What's Included
- **Modular Directory Structure:** Scalable feature-based architecture separating domain logic, persistence, and routing.
- **Asynchronous Data Layer:** Fully async PostgreSQL integration using `asyncpg` and SQLAlchemy 2.0.
- **Enterprise Security:** Cryptographically secure JWT authentication, password hashing via `passlib[bcrypt]`, and role-based access control (RBAC).
- **Zero-Downtime Infrastructure:** Multi-stage Dockerfile and production-ready `docker-compose.yml` with health checks and persistent volumes.
- **Developer Experience:** Integrated Alembic migrations, environment validation, and automated testing hooks.

---

## 2. Quick Start & Core Concepts

### System Architecture Quick Reference

| Component | Technology | Role / Responsibility |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous HTTP routing and automatic OpenAPI documentation. |
| **Data Validation** | Pydantic v2 | Strict schema serialization, deserialization, and runtime type checking. |
| **ORM / Database** | SQLAlchemy 2.0 + Asyncpg | Async database connection pooling and declarative object-relational mapping. |
| **Migrations** | Alembic | Version-controlled database schema evolution. |
| **Authentication** | PyJWT / Passlib | Stateless token generation, verification, and secure password hashing. |
| **Containerization** | Docker & Compose | Isolated multi-container execution environment for development and production. |

### 5-Minute Quick Start

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify Health and Access Documentation:**
   - Interactive API Docs (Swagger): `http://localhost:8000/docs`
   - Alternative Docs (Redoc): `http://localhost:8000/redoc`
   - Health Check Endpoint: `http://localhost:8000/api/v1/health`

---

## 3. Production Code Patterns & Architecture Examples

### 3.1 Directory Structure
```text
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic BaseSettings environment management
│   ├── database.py       # Async SQLAlchemy engine & session factory
│   └── security.py       # JWT creation, validation, & password hashing
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy declarative models
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic request/response validation schemas
├── api/
│   ├── __init__.py
│   ├── deps.py           # Dependency injection (Current user, DB session)
│   └── v1/
│       ├── api.py        # APIRouter aggregator
│       └── endpoints/
│           ├── auth.py   # Login, token refresh, registration
│           └── users.py  # User profile management
├── alembic/              # Database migrations
├── main.py               # FastAPI application entrypoint
├── Dockerfile            # Multi-stage production container build
└── docker-compose.yml    # Multi-container orchestration
```

---

### 3.2 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    # Security
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

### 3.3 Asynchronous Database Setup (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

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
    autocommit=False,
    autoflush=False,
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

### 3.4 Security & JWT Utility (`app/core/security.py`)
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
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

### 3.5 Dependency Injection (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

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
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).filter(User.id == int(token_data.sub)))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

---

### 3.6 Multi-Stage Dockerfile (`Dockerfile`)
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

### 3.7 Production Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: secure_password_here
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres_user -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=MicroCorp Enterprise API
      - SECRET_KEY=super_secret_jwt_key_change_in_production_12345
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=secure_password_here
      - POSTGRES_DB=production_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Patterns to Avoid | ❌ The Wrong Way | ✅ The Production-Grade Solution |
| :--- | :--- | :--- |
| **Sync Database Calls** | Using standard `psycopg2` or blocking SQLAlchemy queries inside async endpoints. | Always utilize `asyncpg` combined with SQLAlchemy's `AsyncSession` to prevent threadpool starvation. |
| **Blocking Password Hashing** | Running `passlib` hashing directly in the request loop. | Offload CPU-bound hashing using `starlette.concurrency.run_in_threadpool` or async wrappers. |
| **Hardcoded Secrets** | Storing JWT secrets and DB credentials in source control. | Enforce strict validation via Pydantic `BaseSettings` reading exclusively from environment variables. |
| **Catching Base Exceptions** | `except Exception:` hiding actual runtime bugs and database deadlocks. | Catch specific database errors (`IntegrityError`) and let unexpected exceptions bubble to global exception handlers. |
| **Unbounded Connection Pools** | Leaving default connection limits unchecked under high horizontal scaling. | Explicitly configure `pool_size` and `max_overflow` matching your database server capacity. |

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** Always run Uvicorn behind a process manager or scale workers relative to CPU cores (`--workers $(nproc)`) in production environments.
2. **Database Indexing:** Ensure foreign keys and high-cardinality lookup columns (e.g., `email`, `username`) have explicit b-tree indexes defined in your SQLAlchemy models.
3. **Pydantic Model Compilation:** For extreme JSON serialization performance, leverage Pydantic v2's Rust-backed core validation engine by avoiding custom validator methods where standard types suffice.
4. **Response Caching:** Implement Redis-backed caching layers for read-heavy, low-volatility endpoints using decorators or FastAPI middleware.

---

## 6. Commercial License & Attribution Summary

### End-User Commercial License
Copyright © **MicroCorp AI** & **The Agency Engineering Division**. All rights reserved.

- **Grant of License:** Subject to the purchase agreement, the purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, evaluate, and deploy this codebase for commercial and non-commercial internal projects, client deliverables, and SaaS products.
- **Restrictions:** Redistribution of this codebase as a standalone template, boilerplate generator, or competing commercial product kit is strictly prohibited without explicit written consent from MicroCorp AI.
- **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The Agency and MicroCorp AI accept zero liability for infrastructure downtime, data loss, or security breaches resulting from improper deployment or unverified configuration modifications.