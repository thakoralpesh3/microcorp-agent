# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*  
> *Production-Grade Turnkey Boilerplate for Enterprise Microservices*

---

## 1. Product Title & Value Proposition

### Title
**FastAPI Production-Grade Boilerplate: Enterprise JWT Auth, SQLAlchemy 2.0 Async, Alembic Migrations, and Multi-Stage Docker Architecture**

### Value Proposition
Stop wasting 40+ hours scaffolding boilerplate authentication, database connection pooling, containerization, and configuration management for every new client project. 

This turnkey solution delivers a battle-tested, asynchronous FastAPI backend architecture designed for scale, security, and immediate deployment. Built specifically for freelance engineers, agency developers, and enterprises who need to deliver secure, production-ready REST APIs on day one without technical debt.

### What You Get
* **Asynchronous Core**: Native async/await support utilizing SQLAlchemy 2.0 and Pydantic v2 for maximum throughput.
* **Secure JWT Authentication**: Access and Refresh token rotation, password hashing via Argon2/Bcrypt, and Role-Based Access Control (RBAC).
* **Zero-Downtime Containerization**: Production-hardened multi-stage Dockerfiles and Docker Compose profiles for local development and production deployment.
* **Database Migrations**: Integrated Alembic setup for tracking schema changes safely.
* **Structured Logging & Error Handling**: Global exception handlers and JSON logging formatted for APM ingestion (Datadog, ELK).

---

## 2. Quick Start & Core Concepts

### Architectural Component Matrix

| Component | Technology Choice | Architectural Rationale |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance async routing, automatic OpenAPI/Swagger documentation, native Pydantic validation. |
| **Database Driver** | asyncpg + SQLAlchemy 2.0 | Asynchronous PostgreSQL driver providing high concurrent connection handling without thread-blocking. |
| **Migration Engine** | Alembic | Version-controlled schema migrations natively integrated with SQLAlchemy declarative models. |
| **Authentication** | python-jose / passlib | Stateless JSON Web Tokens with cryptographic signing (HS256/RS256) and secure password hashing. |
| **Containerization** | Docker (Multi-stage) | Minimized image footprint, non-root execution security, isolated runtime environments. |

### 3-Step Local Initialization

```bash
# 1. Clone or extract the boilerplate repository
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your local database credentials and secret keys

# 3. Spin up the stack via Docker Compose
docker compose up --build -d
```

Verify the API is running by navigating to `http://localhost:8000/docs` for the interactive Swagger documentation.

---

## 3. Production Code Patterns & Architecture Examples

### Directory Structure
```text
app/
├── core/
│   ├── config.py        # Pydantic BaseSettings environment parsing
│   ├── database.py      # Async engine and sessionmaker setup
│   └── security.py      # JWT token creation and password hashing
├── models/
│   └── user.py          # SQLAlchemy ORM User model
├── schemas/
│   └── auth.py          # Pydantic schemas for request/response validation
├── api/
│   ├── v1/
│   │   ├── api.py       # API router aggregator
│   │   └── endpoints/
│   │       ├── auth.py  # Login, register, token refresh routes
│   │       └── users.py # Protected user routes
│   └── deps.py          # FastAPI Depends injectables (current_user, get_db)
├── main.py              # Application entrypoint and middleware wiring
Dockerfile
docker-compose.yml
alembic.ini
requirements.txt
```

### 1. Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def assemble_db_connection(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


settings = Settings()
if not settings.SQLALCHEMY_DATABASE_URI:
    settings.SQLALCHEMY_DATABASE_URI = settings.assemble_db_connection()
```

### 2. Async Database Session (`app/core/database.py`)
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
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
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

### 3. Security & JWT Utility (`app/core/security.py`)
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


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

### 4. FastAPI Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


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
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user
```

### 5. Multi-Stage Production Dockerfile (`Dockerfile`)
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
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

# Create non-privileged user for security compliance
RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 6. Production Docker Compose (`docker-compose.yml`)
```yaml
version: "3.8"

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fastapi_backend
    restart: always
    depends_on:
      db:
        condition: service_healthy
    env_file:
      - .env
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* **Anti-Pattern 1: Using Synchronous DB Drivers with Async FastAPI Routes**
  * *Gotcha*: Using standard `psycopg2` or standard SQLAlchemy sessions inside `async def` endpoints blocks the entire event loop, causing severe latency degradation under concurrency.
  * *Correction*: Always use `asyncpg` combined with `AsyncSession` and `create_async_engine`.
* **Anti-Pattern 2: Storing Plaintext or Weakly Hashed Passwords**
  * *Gotcha*: Relying on MD5, SHA256, or native database hashing without salt.
  * *Correction*: Use `passlib` with `bcrypt` or `argon2` configured with dynamic work factors.
* **Anti-Pattern 3: Hardcoding Secrets in Codebase or Dockerfile**
  * *Gotcha*: Baking API keys, database credentials, or JWT secrets directly into images during build time.
  * *Correction*: Inject runtime variables via secure environment variables (`.env` files locally, AWS Secrets Manager / Kubernetes Secrets in production).
* **Anti-Pattern 4: Catching Generic Exceptions Without Rollback**
  * *Gotcha*: Failing to catch and roll back failed database transactions inside endpoints, resulting in aborted transaction states (`InFailedSqlTransaction`) for subsequent requests in the connection pool.
  * *Correction*: Use context managers that explicitly execute `await session.rollback()` upon exception.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling**: In production container environments, run Uvicorn with multiple worker processes behind a reverse proxy (like Nginx or Traefik) matching your CPU core count (`--workers 4` or via `WEB_CONCURRENCY` environment variable).
* **Connection Pooling Optimization**: Adjust `pool_size` and `max_overflow` parameters in `create_async_engine` to match the maximum concurrent query profile of your PostgreSQL instance.
* **Response Compression**: Integrate `GZipMiddleware` in `app/main.py` for payloads larger than 1000 bytes to minimize network bandwidth consumption.
* **Lazy Loading vs. Eager Loading**: Prevent N+1 query performance bottlenecks by explicitly utilizing SQLAlchemy's `selectinload` or `joinedload` options when querying relationships.

---

## 6. Commercial License & Attribution Summary

### Commercial License Agreement
* **Copyright © MicroCorp AI. All rights reserved.**
* **Grant of License**: Purchasing or licensing this digital product grants the buyer (Individual Developer, Agency, or Enterprise) a perpetual, non-exclusive, worldwide license to use, modify, adapt, and compile this code base for commercial client projects or internal proprietary products.
* **Restrictions**: Redistribution, resale, sub-licensing, or public publishing of this complete source code package as a standalone boilerplate, template, or competing digital product on marketplaces (such as Gumroad, GitHub, or ThemeForest) is strictly prohibited.
* **Warranty Disclaimer**: This software is provided "as is", without warranty of any kind, express or implied. The Agency and MicroCorp AI shall not be held liable for any direct, indirect, or incidental damages arising from the deployment of this architecture.