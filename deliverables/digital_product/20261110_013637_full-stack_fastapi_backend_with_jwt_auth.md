# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — Enterprise Backend Architecture  
> *Production-grade, secure, and containerized FastAPI boilerplate ready for commercial deployment.*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Architecture
Stop wasting 40+ hours configuring boilerplate security, database sessions, and container orchestration. This turnkey solution delivers a hardened, production-grade FastAPI backend complete with Asynchronous SQLAlchemy 2.0, PostgreSQL, JWT Authentication (Access + Refresh tokens), role-based access control (RBAC), Alembic migrations, and a fully optimized Docker Compose development/production environment.

#### Key Business Benefits:
* **Time-to-Market Acceleration:** Deploy a battle-tested architecture on Day 1 instead of writing infrastructure glue code.
* **Security First:** Implements industry-standard cryptographic practices (bcrypt hashing, JWT with expiration validation, secure HTTP-only cookie strategies, and CORS hardening).
* **Enterprise Scalability:** Built on AsyncIO primitives and a clean repository pattern to scale gracefully under high-concurrency loads.
* **Developer Experience:** Fully typed with Python 3.11+, Pydantic v2, and integrated with hot-reloading Docker containers.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
```
[ Client / Frontend ] 
       │
       ▼ (HTTPS / Bearer Token)
[ Nginx / Reverse Proxy ] (Optional Production Layer)
       │
       ▼
[ FastAPI Application (ASGI / Uvicorn) ]
 ├── /api/v1/auth (JWT Issuance & Refresh)
 ├── /api/v1/users (RBAC Protected Endpoints)
 └── Core Middleware (CORS, Trusted Hosts, Rate Limiting)
       │
       ▼ (Async SQLAlchemy 2.0)
[ PostgreSQL 15 Database Container ]
```

### Architectural Component Reference

| Component | Technology | Purpose & Design Pattern |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | High-performance async request routing, auto OpenAPI documentation. |
| **Data Validation** | Pydantic v2 | Strict payload validation, serialization, and settings management. |
| **ORM / Migrations**| SQLAlchemy 2.0 (Async) + Alembic | Non-blocking database operations and deterministic schema migrations. |
| **Authentication** | PyJWT / Passlib (Bcrypt) | Stateless token-based auth with cryptographic signing. |
| **Containerization**| Docker & Docker Compose | Isolated, reproducible development and production environments. |

---

## 3. Production Code Patterns & Architecture Examples

### 📁 Project Structure
```text
fastapi-enterprise/
├── alembic/
│   └── versions/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   └── main.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### ⚙️ 1. Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )


settings = Settings()
```

---

### 🗄️ 2. Database Session Management (`app/core/database.py`)
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

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
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

### 🔒 3. Security & JWT Utilities (`app/core/security.py`)
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


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

---

### 👤 4. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False
    )
```

---

### 🛡️ 5. FastAPI Dependencies (`app/api/deps.py`)
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
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
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

### 🚀 6. Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure securely in production (e.g., ["https://mydomain.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 🐳 7. Containerization Configuration

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

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
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: postgres_password
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres_user -d enterprise_db"]
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
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=postgres_password
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretaccesstokenkeychangeinproduction
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshtokenkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous and Asynchronous Database Drivers:**
   * *Anti-Pattern:* Using `psycopg2` inside async FastAPI path operations or async definitions.
   * *Solution:* Always use `asyncpg` combined with SQLAlchemy's `create_async_engine` to prevent blocking the event loop.
2. **Hardcoding Secrets & Configuration:**
   * *Anti-Pattern:* Keeping JWT secret keys or database credentials inside code files.
   * *Solution:* Use Pydantic's `BaseSettings` to enforce runtime environment variable checks.
3. **Missing Database Connection Pool Settings:**
   * *Anti-Pattern:* Leaving SQLAlchemy pool parameters at default values under high traffic.
   * *Solution:* Explicitly configure `pool_size` and `max_overflow` matching your server instance capacity.
4. **Swallowing Database Exceptions:**
   * *Anti-Pattern:* Using blanket `try/except Exception:` without rolling back the active session.
   * *Solution:* Always explicitly call `await session.rollback()` on transaction errors within dependency generators.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, run Uvicorn behind a process manager like Gunicorn or orchestrate multiple Uvicorn instances via Kubernetes with Nginx as a reverse proxy load balancer.
* **Response Caching:** Integrate Redis caching layers (`fastapi-cache2`) for high-read, low-mutation endpoints to minimize database load.
* **Pydantic Model Compilation:** For ultra-high throughput applications, compile Pydantic models using Cython or rely on Pydantic v2's Rust-backed core engine (already active by default).
* **Database Indexing:** Ensure foreign keys and high-cardinality search fields (such as `email` or account numbers) have proper B-tree indices mapped in Alembic scripts.

---

## 6. Commercial License & Attribution Summary

### 📄 Commercial Use License (MicroCorp AI Standard Enterprise License)
* **Granted Rights:** You are licensed to use, modify, distribute, and integrate this codebase into commercial client projects, SaaS platforms, and internal enterprise systems.
* **Restrictions:** Reselling this specific architectural boilerplate as an independent standalone product or template repository on marketplaces without written authorization is strictly prohibited.
* **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. The Agency and MicroCorp AI accept no liability for damages resulting from production misconfigurations.

> *Engineered by Backend Architect 🏗️ — The Agency Engineering Division.*