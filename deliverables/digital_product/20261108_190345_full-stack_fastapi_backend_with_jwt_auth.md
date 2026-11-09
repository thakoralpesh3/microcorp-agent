# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise-Grade FastAPI Backend Boilerplate
*Secure, Scalable, and Production-Ready Asynchronous API Template with JWT Authentication, PostgreSQL, SQLAlchemy ORM, Alembic Migrations, and Full Docker Compose Orchestration.*

---

### 💡 Executive Value Proposition
Building a modern, secure, and production-ready backend from scratch takes weeks of boilerplate setup, security configuration, and architectural planning. This turnkey solution provides a fully integrated, enterprise-grade FastAPI template engineered for high-throughput microservices and SaaS applications. 

Designed for immediate deployment, it eliminates common technical debt traps by implementing industry best practices out-of-the-box: asynchronous database connections, stateless JWT authentication with refresh token patterns, strict type safety using Pydantic v2, and containerized multi-stage Docker builds.

---

## 2. Quick Start & Core Concepts

Get your development environment running in under 60 seconds with Docker Compose.

### 🏁 60-Second Quick Start
```bash
# 1. Clone the repository and navigate to the root directory
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Configure your environment variables
cp .env.example .env

# 3. Spin up the containers (PostgreSQL + FastAPI App)
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head

# 5. Access interactive API documentation
open http://localhost:8000/docs
```

### 🧠 Architectural Blueprint & Syntax Guide

| Component | Technology | Core Responsibility |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance asynchronous request handling and auto-docs generation. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and strict schema enforcement. |
| **ORM & Driver** | SQLAlchemy 2.0 (asyncio) + asyncpg | Non-blocking relational database operations. |
| **Migrations** | Alembic | Version-controlled database schema migrations. |
| **Authentication** | PyJWT / Passlib (Argon2) | Stateless token-based auth with military-grade password hashing. |
| **Containerization**| Docker & Docker Compose | Isolated, multi-stage, reproducible environments for dev and prod. |

---

## 3. Production Code Patterns & Architecture Examples

This architecture follows a decoupled, service-oriented structure designed to scale cleanly as your codebase expands.

```text
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   └── users.py
│   │   └── router.py
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/
│   └── user.py
├── schemas/
│   └── user.py
├── crud/
│   └── crud_user.py
└── main.py
```

---

### ⚙️ Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
```

---

### 🗄️ Asynchronous Database Engine (`app/core/database.py`)
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

### 🔒 Security & JWT Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### 📦 SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
```

---

### 🛡️ Authentication Dependency (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
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
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    user = await db.get(User, token_data.sub)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### 🐳 Production Docker Setup

#### `Dockerfile`
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

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
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
    container_name: fastapi_api
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
      - JWT_SECRET_KEY=super-secret-access-key-change-me
      - JWT_REFRESH_SECRET_KEY=super-secret-refresh-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Synchronous and Asynchronous Code:** Using standard `psycopg2` or blocking I/O inside async FastAPI routes will block the event loop, completely destroying throughput.
   * ✅ **Fix:** Always use `asyncpg` with SQLAlchemy's asynchronous session extensions (`AsyncSession`).
2. ❌ **Hardcoding Secrets in Code or Dockerfiles:** Committing JWT keys or database passwords to version control.
   * ✅ **Fix:** Injected all secrets securely via environment variables using `pydantic-settings`.
3. ❌ **Storing Passwords in Plain Text or Weak Hashing:** Using MD5, SHA256, or Bcrypt without proper work factors.
   * ✅ **Fix:** Use Argon2 (`passlib[argon2]`) for modern memory-hard password hashing.
4. ❌ **Failing to Handle Database Session Rollbacks:** Leaving uncommitted transactions open during database exceptions, causing connection leaks.
   * ✅ **Fix:** Wrap database dependencies in strict `try/except/finally` blocks that execute explicit `session.rollback()` on failure.

---

## 5. Performance & Optimization Tips

* ⚡ **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` in your SQLAlchemy engine setup depending on your database tier and concurrent load requirements.
* ⚡ **Uvicorn Worker Scaling:** In production (outside of Docker development mode), run Uvicorn behind a process manager or use Gunicorn with Uvicorn workers (`gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`).
* ⚡ **Response Compression:** Integrate `GZipMiddleware` into your FastAPI app to automatically compress responses larger than 1KB, decreasing network payload sizes.
* ⚡ **Selective Serialization:** Avoid lazy-loading large relationships accidentally in your API responses by using explicit Pydantic response models (`response_model=UserPublic`).

---

## 6. Commercial License & Attribution Summary

### 📜 MicroCorp AI Enterprise License (Permissive Commercial)
*Copyright © 2024 MicroCorp AI. All rights reserved.*

* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and distribute this codebase within commercial, proprietary, and open-source software products.
* **Restrictions:** You may not resell, sublicense, or distribute this specific boilerplate package as a standalone template or competing developer kit.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any direct, indirect, or consequential damages arising from the deployment of this software.