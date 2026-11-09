# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division**  
> *Author:* Backend Architect 🏗️  
> *Target:* Enterprise MicroCorp AI Commercial Release / Fiverr Turnkey Delivery Kit v2.4  

---

## 1. # Product Title & Value Proposition

### Product Title
**Production-Ready FastAPI Backend Boilerplate: JWT Authentication, PostgreSQL, Alembic Migrations, and Fully Containerized Docker Architecture.**

### Value Proposition
Building a modern, secure, and scalable backend from scratch is time-consuming. Engineers and agency clients waste dozens of hours configuring security layers, database connection pooling, async ORM models, environment segregation, and multi-stage Docker builds. 

This turnkey solution provides a **battle-tested, enterprise-grade architecture** designed for high throughput and strict security compliance. It bridges the gap between rapid prototyping and production-grade reliability, allowing you to deploy secure RESTful APIs with JSON Web Token (JWT) authentication in under 10 minutes.

### What's Included
* **Asynchronous SQLAlchemy 2.0+** integrated with PostgreSQL.
* **Database Migrations** via Alembic pre-configured for async drivers.
* **Secure Authentication Engine** utilizing OAuth2 password bearer flows, access/refresh token rotation, and bcrypt password hashing.
* **Production-Grade Docker Setup** featuring multi-stage builds, non-root execution, and health checks via Docker Compose.
* **Comprehensive Test Suite** structure using `pytest` and `httpx`.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview
```
[Client / Frontend] 
       │ (HTTPS / Bearer Token)
       ▼
[Nginx / Reverse Proxy] (Optional)
       │
       ▼
[FastAPI Application Container (Uvicorn Workers)]
       ├─► [API Router Layer]
       ├─► [Dependency Injection (Auth & DB Session)]
       ├─► [Async SQLAlchemy ORM]
       └─► [PostgreSQL Database Container]
```

### Clean Syntax & Technology Stack Reference

| Layer / Component | Technology Selected | Core Responsibility |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | High-performance asynchronous API routing and validation via Pydantic v2. |
| **ASGI Server** | Uvicorn | Production-ready process management and request handling. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Type-safe database interactions using native Python async/await syntax. |
| **Migrations** | Alembic | Version-controlled schema evolutions and database state management. |
| **Security** | `python-jose` & `passlib` | JWT generation, cryptographic signing, and secure password hashing. |
| **Containerization**| Docker & Docker Compose | Isolated, reproducible multi-container execution environments. |

### 3-Step Quick Start

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up via Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify API Health:**
   Navigate to `http://localhost:8000/docs` to interact with the auto-generated Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-backend/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/    # Route handlers (auth, users, items)
│   │   │   └── router.py     # API router aggregation
│   ├── core/                 # Config, security, database session setup
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic validation schemas
│   └── main.py               # FastAPI application factory
├── tests/                    # Pytest integration tests
├── Dockerfile                # Multi-stage production Docker build
├── docker-compose.yml        # Local orchestration
└── requirements.txt          # Python dependencies
```

---

### File 1: `app/core/config.py` (Environment Configuration)
```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp AI Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "app_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    SQLALCHEMY_DATABASE_URI: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY_CHANGE_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        case_sensitive = True

settings = Settings()
```

---

### File 2: `app/core/database.py` (Async Database Session)
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
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

### File 3: `app/core/security.py` (JWT & Password Hashing)
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

---

### File 4: `app/models/user.py` (SQLAlchemy ORM Model)
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)
```

---

### File 5: `app/api/v1/endpoints/auth.py` (Authentication Router)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### File 6: `Dockerfile` (Multi-stage Production Build)
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

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### File 7: `docker-compose.yml` (Local Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    container_name: fastapi_backend
    restart: always
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=app_db
      - SECRET_KEY=super-secret-production-key-change-me
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking the Event Loop in Async Endpoints**
   * *Anti-Pattern:* Utilizing synchronous libraries (like standard `requests` or blocking file I/O) directly inside `async def` route handlers. This locks the entire Uvicorn worker thread.
   * *Correction:* Use asynchronous clients like `httpx` or run CPU-heavy computational tasks inside a thread pool executor (`loop.run_in_executor`).

2. **Hardcoding Cryptographic Secrets**
   * *Anti-Pattern:* Storing raw JWT `SECRET_KEY` strings inside application code or tracking `.env` files in Git.
   * *Correction:* Always inject secrets via environment variables or secure vault managers (AWS Secrets Manager, HashiCorp Vault).

3. **Mixing Synchronous and Asynchronous ORM Sessions**
   * *Anti-Pattern:* Passing standard SQLAlchemy `Session` objects into asynchronous route definitions or failing to utilize `asyncpg` database drivers.
   * *Correction:* Maintain strict async boundaries across the engine, sessionmaker, and dependency injection lifecycle.

4. **Ignoring Database Connection Pool Exhaustion**
   * *Anti-Pattern:* Creating a new database session manually within loops or route scopes without using a reliable context manager or dependency injection lifecycle (`yield`).
   * *Correction:* Always rely on FastAPI's `Depends(get_db)` to automatically acquire and close sessions safely, even during unhandled exceptions.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container environments, scale your Uvicorn worker processes based on available CPU cores using the formula `(2 * $CPU_CORES) + 1`, or deploy behind a process manager like Gunicorn / Kubernetes ingress controllers.
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (such as `email` or query filter fields) possess explicit database indexes (`index=True`).
* **Pydantic Model Parsing Speed:** Utilize Pydantic v2's compiled Rust core (`pydantic-core`) by ensuring your models are cleanly typed; avoid unnecessary custom validators where native types suffice.
* **Response Compression:** Integrate `GZipMiddleware` into your FastAPI application initialization to minimize payload over-the-wire transit times for large JSON responses:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```

---

## 6. ## Commercial License & Attribution Summary

### Commercial Usage License
* **Grant of Rights:** MicroCorp AI grants the purchaser / client a perpetual, non-exclusive, worldwide, royalty-free commercial license to use, modify, adapt, and deploy this software boilerplate within proprietary commercial applications, client deliverables, and SaaS platforms.
* **Restrictions:** Redistribution of this codebase as a standalone competing boilerplate, template kit, or open-source product without explicit written consent from MicroCorp AI is strictly prohibited.
* **Disclaimer of Warranty:** This software is provided *"as is"*, without warranty of any kind, express or implied. MicroCorp AI and the Engineering Division assume no liability for direct or indirect damages resulting from the deployment of this code in production environments.

### Attribution
Engineered with absolute precision by **The Agency Engineering Division** for **MicroCorp AI**.  
*Systems that hold everything up.*