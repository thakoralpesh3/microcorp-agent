# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Delivery Specification*

---

## 1. # Product Title & Value Proposition

### Product Title
**FastAPI Production-Grade Microservice Boilerplate: JWT Auth, Async PostgreSQL, and Multi-Stage Docker Setup**

### Value Proposition
Stop wasting 40+ hours configuring boilerplate infrastructure, wiring up password hashing, debugging Pydantic v2 validation errors, or struggling with Docker multi-stage builds. This turnkey solution provides a fully asynchronous, highly scalable backend architecture ready for production deployment. Designed for enterprise clients and high-velocity freelance deliveries, this codebase implements industry best practices for dependency injection, secure JWT authentication with refresh token rotation, database migrations via Alembic, and an optimized, zero-vulnerability Docker container.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview
```
[Client] ---> (Nginx Reverse Proxy / SSL Termination)
                  │
                  ▼
       [Docker Container: Uvicorn]
                  │
                  ▼
       [FastAPI Async Application]
       ├── /api/v1/auth (JWT Handlers)
       ├── /api/v1/users (Protected CRUD)
       └── Database Session Dependency (SQLAlchemy 2.0 Async)
                  │
                  ▼
       [PostgreSQL Database (Docker Volume)]
```

### Clean Syntax & Configuration Table

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async API routing and auto-docs. |
| **Data Validation** | Pydantic | `2.6+` | Runtime data parsing and settings management. |
| **ORM** | SQLAlchemy | `2.0+` | Async database interaction and schema definition. |
| **Migrations** | Alembic | `1.13+` | Version control for database schema evolution. |
| **Authentication** | python-jose / passlib | Latest | Cryptographic JWT generation and bcrypt hashing. |
| **Containerization**| Docker / Compose | Latest | Multi-stage isolated runtime environments. |

---

## 3. ## Production Code Patterns & Architecture Examples

### Directory Structure
```
fastapi-production-boilerplate/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           └── users.py
│   └── core/
│       ├── __init__.py
│       ├── security.py
│       └── exceptions.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### `app/config.py` (Environment Configuration)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Production Microservice"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    SQLALCHEMY_DATABASE_URI: str | None = None
    
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
# Computed URI for AsyncPG
settings.SQLALCHEMY_DATABASE_URI = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)
```

---

### `app/database.py` (Async SQLAlchemy Setup)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


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

---

### `app/models/user.py` (SQLAlchemy 2.0 User Model)
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

---

### `app/core/security.py` (JWT & Hashing Utilities)
```python
from datetime import datetime, timedelta
from typing import Any
from jose import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### `app/api/deps.py` (Authentication & Session Dependencies)
```python
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
        parsed_uuid = uuid.UUID(user_id)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == parsed_uuid))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### `Dockerfile` (Optimized Multi-Stage Build)
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
FROM python:3.11-slim AS runner

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

### `docker-compose.yml` (Local Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=production_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super_secure_access_secret_key_change_in_production
      - JWT_REFRESH_SECRET_KEY=super_secure_refresh_secret_key_change_in_production
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O Inside Async Paths**
   * *Anti-Pattern:* Utilizing `time.sleep()`, standard `requests`, or synchronous DB drivers (`psycopg2`) inside `async def` endpoints. This freezes the entire event loop, destroying throughput.
   * *Correction:* Always use non-blocking counterparts (`asyncio.sleep`, `httpx`, `asyncpg`) or offload blocking CPU-heavy operations using `run_in_threadpool`.

2. **Ignoring Database Session Lifecycle Leaks**
   * *Anti-Pattern:* Manually creating `SessionLocal()` inside route functions without utilizing `try/finally` blocks or FastAPI dependency injection. This leads to leaked DB connections and connection pool exhaustion.
   * *Correction:* Leverage context-manager yields inside FastAPI dependencies as demonstrated in `app/database.py`.

3. **Hardcoding Environment Secrets**
   * *Anti-Pattern:* Keeping JWT secret keys or database credentials inside repository configuration files.
   * *Correction:* Use Pydantic's `BaseSettings` linked strictly to environment variables and container secrets management systems.

---

## 5. ## Performance & Optimization Tips

* **Connection Pool Tuning:** Adjust `pool_size` and `max_overflow` parameters in `create_async_engine()` to match your server's vCPU count and expected concurrent connection peaks.
* **Uvicorn Worker Scaling:** In production container environments, run Uvicorn with multiple workers behind a process manager or orchestrator (e.g., Kubernetes replicas or Gunicorn worker management patterns), matching worker counts to `(2 * vCPU) + 1`.
* **Response Compression:** Integrate `GZipMiddleware` into `app/main.py` for payloads exceeding 1000 bytes to drastically lower bandwidth overhead.
* **Database Indexing:** Ensure all foreign keys, lookup keys (`email`), and search criteria columns have explicit database indexes created via SQLAlchemy.

---

## 6. ## Commercial License & Attribution Summary

### End-User Commercial License Agreement
* **Copyright (c) 2026 MicroCorp AI. All rights reserved.**
* **Grant of License:** This turnkey solution is licensed to the purchasing client for commercial, internal, and client-delivery deployment. You are permitted to modify, rebrand, extend, and deploy this codebase as part of commercial client deliverables or SaaS products.
* **Restrictions:** Reselling, sub-licensing, or publicly redistributing this raw boilerplate code as an isolated standalone product template on open marketplaces is strictly prohibited without explicit written clearance from MicroCorp AI.
* **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.