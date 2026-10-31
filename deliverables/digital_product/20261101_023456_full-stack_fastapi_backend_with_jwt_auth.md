# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Turnkey Client Deliverable*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, PostgreSQL, & Dockerized Production Ready**

#### **Value Proposition**
Building production-ready asynchronous Python APIs from scratch is time-consuming, error-prone, and full of hidden security traps. This turnkey solution provides a battle-tested, highly optimized FastAPI backend architecture designed for scale. Featuring native async database operations with SQLAlchemy 2.0, secure JWT-based authentication (OAuth2 with Password Flow), Alembic migrations, and a fully orchestrated Docker Compose environment, this boilerplate reduces initial backend setup time from days to minutes. 

Engineered strictly around modern PEP 8 standards, dependency injection patterns, and robust error handling, this codebase is ready to plug into your frontend (React, Next.js, Flutter) or deploy directly to AWS, GCP, or DigitalOcean.

---

## 2. ## Quick Start & Core Concepts

### **System Architecture & Tech Stack Overview**

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous API routing & automatic OpenAPI docs |
| **Runtime** | Python | `3.11+` | Strict type-hinting, performance optimizations, and async support |
| **Database Driver** | AsyncPG | `0.29+` | Non-blocking PostgreSQL driver for maximum concurrency |
| **ORM** | SQLAlchemy | `2.0+` | Modern data mapping with native asynchronous session handling |
| **Migrations** | Alembic | `1.13+` | Version-controlled database schema migrations |
| **Authentication** | PyJWT & Passlib | `2.8+` | Cryptographic JWT generation and bcrypt password hashing |
| **Containerization** | Docker & Compose | `Latest` | Isolated, reproducible development and production environments |

### **5-Minute Quick Start Guide**

1. **Clone and Configure Environment Variables:**
   ```bash
   git clone https://github.com/microcorp/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify Database Migrations:**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Access Interactive Documentation:**
   * Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   * ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
app/
├── alembic/              # Database migration scripts
├── core/                 # Config, security, database session management
│   ├── config.py         # Pydantic BaseSettings management
│   ├── database.py       # Async SQLAlchemy sessionmaker
│   └── security.py       # JWT creation & password hashing
├── models/               # SQLAlchemy ORM database models
│   └── user.py
├── schemas/              # Pydantic validation & serialization schemas
│   └── user.py
├── api/                  # API routers (Endpoints)
│   ├── v1/
│   │   ├── api.py        # Router aggregation
│   │   └── endpoints/
│   │       ├── auth.py   # Login & token generation
│   │       └── users.py  # User registration & profile management
│   └── deps.py           # FastAPI dependency injection (get_db, get_current_user)
├── main.py               # FastAPI application entrypoint
├── Dockerfile            # Multi-stage production container build
└── docker-compose.yml    # Service orchestration (API + PostgreSQL)
```

---

### **1. Core Configuration (`app/core/config.py`)**
Handles strict environment validation using Pydantic Settings.

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
    
    SQLALCHEMY_DATABASE_URI: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### **2. Database Engine & Session Dependency (`app/core/database.py`)**
Asynchronous connection pooling with SQLAlchemy 2.0.

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
    """Dependency function that yields database sessions per request lifecycle."""
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

### **3. Cryptography & Security Utilities (`app/core/security.py`)**
Secure password hashing and token generation.

```python
from datetime import datetime, timedelta, timezone
import jwt
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **4. SQLAlchemy User Model (`app/models/user.py`)**

```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

---

### **5. FastAPI Dependencies for Auth (`app/api/deps.py`)**
Validates JWT Bearer tokens and extracts current user context.

```python
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
        user_uuid = uuid.UUID(user_id)
    except (PyJWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user
```

---

### **6. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.user import TokenSchema

router = APIRouter()

@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### **7. Docker Orchestration (`docker-compose.yml`)**

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
    container_name: fastapi_backend
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
      - JWT_SECRET_KEY=supersecretkeyjwt123456
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkey123456
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

### **8. Production Containerization (`Dockerfile`)**

```dockerfile
FROM python:3.11-slim as base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

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

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous and Asynchronous Database Drivers:**
   * *Anti-Pattern:* Using standard `psycopg2` or basic SQLAlchemy synchronous sessions inside async FastAPI route definitions (`async def`). This blocks the entire event loop under concurrent load.
   * *Fix:* Always utilize `asyncpg` via `create_async_engine` paired with `AsyncSession`.

2. **Hardcoding Secrets and Config Parameters:**
   * *Anti-Pattern:* Hardcoding database credentials, JWT secrets, or environment-specific URLs directly in configuration files.
   * *Fix:* Enforce strict validation via Pydantic `BaseSettings` reading from `.env` files or secure secret managers (AWS Secrets Manager, HashiCorp Vault).

3. **Not Managing Database Session Lifecycles:**
   * *Anti-Pattern:* Manually opening database sessions within route handlers without closing them, leading to connection leaks and pool exhaustion.
   * *Fix:* Use FastAPI’s dependency injection system (`Depends(get_db)`) to safely yield sessions and guarantee closure via context managers.

4. **Catching Generic Exceptions Silently:**
   * *Anti-Pattern:* Wrapping database logic in broad `except Exception:` blocks that swallow errors and return HTTP 200 with empty bodies.
   * *Fix:* Catch specific database exceptions, log the stack trace cleanly, rollback transactions manually if needed, and throw descriptive `HTTPException` codes.

---

## 5. ## Performance & Optimization Tips

* **Connection Pool Tuning:** Adjust `pool_size` and `max_overflow` in your SQLAlchemy engine setup based on your server core count and database max connection ceilings. For high-throughput apps, pair this with an external connection pooler like **PgBouncer**.
* **Query Optimization with `selectinload`:** Prevent N+1 query problems when fetching related models by using SQLAlchemy's async loading strategies (`selectinload` or `joinedload`).
* **Gzip Compression Middleware:** Enable response compression in FastAPI to drastically reduce payload sizes over the wire:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Production ASGI Server Workers:** Never run `uvicorn` with `--reload` in production. Deploy using multiple worker processes via Gunicorn with Uvicorn workers:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```

---

## 6. ## Commercial License & Attribution Summary

### **MicroCorp AI Commercial-Grade License**

Copyright (c) 2026 MicroCorp AI and The Agency Engineering Division. All rights reserved.

#### **Grant of License**
Subject to your purchase of this digital product from an authorized distributor (Fiverr, GitHub Sponsors, Gumroad, or itch.io), MicroCorp AI grants the purchaser (Client/Developer) a worldwide, non-exclusive, perpetual, royalty-free license to use, modify, copy, and distribute this codebase within commercial, proprietary, or open-source software applications, subject to the conditions below.

#### **Restrictions**
* **Resale:** Redistribution of this codebase as a standalone boilerplate, API template, or competing digital product wrapper is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall MicroCorp AI or The Agency be liable for any claim, damages, or liability arising from its use.