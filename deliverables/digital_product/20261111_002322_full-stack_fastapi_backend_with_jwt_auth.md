# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Client Delivery Specification*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, PostgreSQL, & Docker Setup**

#### **Product Overview**
This turnkey backend architecture package is engineered for senior developers, technical founders, and agency contractors looking to bypass the boilerplate phase of production web development. It delivers an asynchronous, high-performance, secure, and fully containerized API foundation built with **FastAPI**, **SQLModel/SQLAlchemy**, **PostgreSQL**, and **JSON Web Token (JWT) Authentication**.

```
+-----------------------------------------------------------------------+
                    CLIENT DELIVERY MANIFEST
+-----------------------------------------------------------------------+
| Stack: FastAPI (Async) | Python 3.11+ | PostgreSQL 15 | Docker Compose |
| Auth: OAuth2 Password Flow with JWT (Access + Refresh Tokens)         |
| Architecture: Clean Layered Architecture (Routers, CRUD, Services)      |
| Quality: Type-Hinted, Pytest-Ready, Pydantic v2 Validated             |
+-----------------------------------------------------------------------+
```

#### **Value Proposition**
* **Time-to-Market Acceleration:** Cuts initial backend setup time by 40+ hours, eliminating redundant configuration of database sessions, environment validation, CORS policies, and security headers.
* **Production-Ready Security:** Implements industry-standard cryptographic signing (`HS256`/`RS256`), secure password hashing via `passlib[bcrypt]`, HttpOnly cookie strategies, and role-based access control (RBAC).
* **Zero-Friction Infrastructure:** Fully orchestrated via Docker and Docker Compose with hot-reloading development loops and production-optimized multi-stage builds.

---

## 2. ## Quick Start & Core Concepts

### **Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/                  # Database migrations
├── app/
│   ├── api/                  # API Routers (v1)
│   │   ├── endpoints/        # Auth, Users, Health
│   │   └── deps.py           # Dependency injection (DB, Current User)
│   ├── core/                 # App configuration & security
│   │   ├── config.py         # Pydantic Settings
│   │   └── security.py       # JWT & password hashing utils
│   ├── crud/                 # Database abstraction layer
│   ├── models/               # SQLModel database tables
│   ├── schemas/              # Pydantic validation schemas
│   └── main.er.py            # FastAPI application factory
├── tests/                    # Pytest suite
├── .env.example              # Environment variables template
├── Dockerfile                # Production container spec
├── docker-compose.yml        # Local orchestration
└── requirements.txt          # Dependency manifest
```

### **Core Concepts Syntax Table**

| Component | Library / Pattern | Purpose & Implementation Rule |
| :--- | :--- | :--- |
| **Validation** | Pydantic v2 | Runtime data parsing, serialization, and settings management via environment variables. |
| **ORM & DB** | SQLModel / Asyncpg | Combines SQLAlchemy 2.0 type safety with Pydantic models for async database operations. |
| **Auth Flow** | OAuth2PasswordBearer | Issues JWT tokens upon credential validation; protects routes via FastAPI `Depends`. |
| **Migrations** | Alembic | Tracks schema changes deterministically across development, staging, and production. |
| **Containerization**| Docker Multi-Stage | Separates build dependencies from runtime environments to minimize image footprint. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **A. Environment & Configuration (`app/core/config.py`)**
Using Pydantic v2 `BaseSettings` to guarantee strict type validation for runtime configuration.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    VERSION: str = "1.0.0"
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
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
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

### **B. Security & JWT Token Generation (`app/core/security.py`)**
Cryptographic routines for password hashing and JWT payload encoding.

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


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### **C. Database Engine & Session Dependency (`app/api/deps.py`)**
Async session management adhering to the Unit of Work lifecycle pattern.

```python
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from app.core.config import settings
from app.models.user import User

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user
```

---

### **D. Application Factory (`app/main.py`)**
Clean bootstrap script setting up middleware, CORS, and API routing.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/health", tags=["System"])
    async def health_check():
        return {"status": "healthy", "version": settings.VERSION}

    return application


app = get_application()
```

---

### **E. Containerization (`Dockerfile`)**
Production-hardened, multi-stage Docker build utilizing non-root execution.

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

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **F. Local Orchestration (`docker-compose.yml`)**

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

  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretdevkeychangeinproduction
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations in Async Endpoints**
   * *Anti-Pattern:* Utilizing standard `requests` or blocking ORM queries inside `async def` routes, blocking the event loop thread.
   * *Fix:* Use `asyncpg` / `SQLModel` async sessions, or offload heavy CPU/blocking I/O routines using `run_in_threadpool`.

2. **Hardcoding Secrets and Configurations**
   * *Anti-Pattern:* Embedding JWT secrets or database passwords directly within code files or checking `.env` files into source control.
   * *Fix:* Enforce validation schemas with Pydantic `BaseSettings` and ensure `.env` is listed inside `.gitignore`.

3. **Ignoring Database Connection Pool Exhaustion**
   * *Anti-Pattern:* Creating a new database engine or unmanaged session per request without proper context managers.
   * *Fix:* Use FastAPI dependency injection (`Depends(get_db)`) to guarantee automatic session closing and connection return to the pool.

4. **Catching Generic Exceptions Globally**
   * *Anti-Pattern:* Using `except Exception:` without logging or re-raising, masking underlying errors and returning opaque 500 server errors.
   * *Fix:* Register explicit exception handlers for custom domain errors and structure validation errors cleanly.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production Kubernetes or container environments, run Uvicorn behind a process manager or configure multiple worker processes (`uvicorn app.main:app --workers 4`) matched to available CPU cores.
* **Connection Pooling Parameters:** Fine-tune database connection pool limits inside production deployment variables to match database capacity:
  ```python
  create_async_engine(
      settings.DATABASE_URL, pool_size=20, max_overflow=10, pool_timeout=30
  )
```
* **Response Model Optimization:** Always utilize `response_model` declarations on FastAPI decorators to filter out unassigned database attributes and accelerate JSON serialization rendering via Pydantic.
* **Database Indexing:** Ensure foreign key relations and high-cardinality query fields (e.g., `email`, `username`) carry explicit database indexes via Alembic migrations.

---

## 6. ## Commercial License & Attribution Summary

### **End-User Commercial License**
* **Granted Rights:** You are licensed to use, modify, adapt, and distribute this codebase within commercial client applications, proprietary SaaS platforms, and internal enterprise architectures.
* **Restrictions:** Reselling, redistributing, or publishing this exact architectural boilerplate as a competing template, digital product, or open-source generator without explicit authorization is strictly prohibited.
* **Warranty Disclaimer:** Provided *as-is* without warranty of any kind, express or implied. The author and MicroCorp AI disclaim all liability for direct or indirect damages resulting from the deployment of this software.

---
*Built with precision by The Engineering Division @ The Agency for MicroCorp AI.*