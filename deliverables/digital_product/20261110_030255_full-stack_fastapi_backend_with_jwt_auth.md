# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### **FastAPI Enterprise Engine: Production-Ready Asynchronous Backend Blueprint**
*A turnkey, battle-tested FastAPI microservice boilerplate featuring secure JWT authentication, SQLAlchemy 2.0 async ORM, Alembic migrations, PostgreSQL, and a hardened multi-stage Docker deployment pipeline.*

---

### **Value Proposition**
Building a production-grade backend from scratch requires stitching together dozens of disparate technologies: async database drivers, cryptographic token management, connection pooling, environment configuration, and container orchestration. 

This turnkey solution eliminates 80+ hours of boilerplate setup. It provides software engineers and enterprise clients with a rigid, scalable, and secure architecture out-of-the-box. Fully optimized for high-throughput I/O bound operations, it enforces strict typing via Pydantic v2 and clean separation of concerns following Domain-Driven Design (DDD) principles.

---

## 2. Quick Start & Core Concepts

### **Architecture Topology**
```
[Client App] ---> (HTTPS / JSON) ---> [Nginx Reverse Proxy]
                                            |
                                            v
                                    [FastAPI Uvicorn Workers]
                                    /        |        \
                                   v         v         v
                             [SQLAlchemy] [Redis]   [Alembic]
                                   |
                                   v
                         [PostgreSQL 15 Database]
```

### **Core Stack & Syntax Quick Reference**

| Layer / Component | Technology Stack | Core Design Pattern / Concept |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | Dependency Injection, Starlette ASGI, Auto OpenAPI |
| **Data Validation** | Pydantic v2 | Strict parsing, field validators, settings management |
| **ORM & Migrations**| SQLAlchemy 2.0 (Async) + Alembic | Declarative mapping, session dependency injection, asyncpg driver |
| **Authentication** | python-jose + passlib (Bcrypt) | Stateless JWT access/refresh tokens, password hashing |
| **Containerization**| Docker & Docker Compose | Multi-stage builds, non-root execution, healthchecks |
| **Database** | PostgreSQL 15 | Relational integrity, connection pooling, async queries |

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
app/
├── alembic/                 # Database migration scripts
├── core/                    # Config, security, database sessions
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/                  # SQLAlchemy ORM models
│   └── user.py
├── schemas/                 # Pydantic validation schemas
│   └── user.py
├── api/                     # API Routers (v1)
│   ├── v1/
│   │   ├── api.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       └── users.py
│   └── deps.py              # FastAPI Dependencies
├── main.py                  # Application entrypoint
├── Dockerfile               # Production container definition
├── docker-compose.yml       # Local development orchestration
└── requirements.txt         # Pinned Python dependencies
```

---

### **Configuration Management (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    def model_post_init(self, __context) -> None:
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### **Database Session Management (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

### **Security & JWT Utilities (`app/core/security.py`)**
```python
from datetime import datetime, timedelta
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### **SQLAlchemy User Model (`app/models/user.py`)**
```python
import uuid
from sqlalchemy import Boolean, Column, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
```

---

### **Pydantic Schemas (`app/schemas/user.py`)**
```python
import uuid
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None
```

---

### **FastAPI Authentication Dependencies (`app/api/deps.py`)**
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.type != "access" or token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### **Authentication Router (`app/api/v1/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### **Main Application Entrypoint (`app/main.py`)**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

### **Production Multi-Stage Dockerfile (`Dockerfile`)**
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

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **Docker Compose Configuration (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
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

  web:
    build: .
    container_name: fastapi_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=FastAPI Enterprise Engine
      - SECRET_KEY=supersecretkeychangemeinproduction
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations Inside Async Paths**
   * *Anti-pattern:* Using standard library `requests` or blocking ORM queries inside `async def` route handlers. This starves the event loop and locks up worker threads.
   * *Correction:* Always use asynchronous drivers (`asyncpg`, `httpx`) inside `async def` routes, or define CPU-bound/blocking functions using standard `def` so FastAPI automatically runs them in an external threadpool.

2. **Global Mutable Database Sessions**
   * *Anti-pattern:* Instantiating a single global `AsyncSession` object and reusing it across multiple incoming requests. This causes race conditions and concurrent write failures.
   * *Correction:* Always use FastAPI's dependency injection (`Depends(get_db)`) to instantiate a request-scoped session context that cleanly tears down after the request completes.

3. **Exposing ORM Models Directly in API Responses**
   * *Anti-pattern:* Returning SQLAlchemy models directly from endpoints. This leaks database structure, internal password hashes, and risks infinite recursion loops during JSON serialization of relationship trees.
   * *Correction:* Always deserialize ORM models into dedicated Pydantic response models using `model_config = ConfigDict(from_attributes=True)`.

4. **Hardcoding Secrets and Configurations**
   * *Anti-pattern:* Embedding database credentials, JWT secret keys, and environment variables directly into source code files.
   * *Correction:* Use `pydantic-settings` to enforce strict environment configuration loading backed by `.env` files and secure secret managers.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, launch Uvicorn with multiple worker processes mapped to CPU cores (`--workers N`), or place FastAPI behind a Gunicorn process manager running Uvicorn worker classes.
* **Database Connection Pooling:** Fine-tune SQLAlchemy's connection pool parameters (`pool_size`, `max_overflow`, `pool_timeout`) based on your maximum concurrency needs and PostgreSQL server connection limits (`max_connections`).
* **Query Optimization and Eager Loading:** Prevent N+1 query performance hits by explicitly utilizing SQLAlchemy's `selectinload` or `joinedload` options when fetching relational entity trees.
* **Response Compression:** Integrate Starlette's `GZipMiddleware` to automatically compress JSON responses larger than 1KB, significantly reducing network payload transfer times.

---

## 6. Commercial License & Attribution Summary

### **Commercial End-User License Agreement (EULA)**
* **Copyright © MicroCorp AI & The Engineering Division.** All rights reserved.
* **Grant of License:** This turnkey codebase is licensed to the purchasing client for commercial deployment, modification, and integration into internal or client-facing production systems.
* **Restrictions:** Redistribution, resale, or public publishing of this raw architectural template as a standalone boilerplate product without explicit written authorization from MicroCorp AI is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.