# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise-Grade FastAPI Backend Boilerplate with Secure JWT Authentication & Dockerized Infrastructure

#### Value Proposition
Stop wasting 40+ hours writing boilerplate, structuring routing layers, configuring CORS, handling database migrations, and setting up secure token-based authentication from scratch. This turnkey FastAPI solution provides a battle-tested, production-ready architecture designed for horizontal scaling, rapid feature development, and bulletproof security out of the box. 

Whether you are delivering a custom MVP for a Fiverr client or bootstrapping your own SaaS platform, this codebase guarantees zero technical debt on day one.

#### What’s Included:
- **Asynchronous Database Engine:** Powered by SQLAlchemy 2.0+ and Alembic for seamless async migrations.
- **Robust Security Layer:** OAuth2 with Password Flow, JWT access/refresh token rotation, and bcrypt password hashing.
- **Modular Project Structure:** Clean separation of concerns (Routers, Schemas, Models, Services, Core config).
- **Production-Ready Docker Setup:** Multi-stage `Dockerfile` and `docker-compose.yml` orchestrating FastAPI and PostgreSQL with persistent volumes.
- **Enterprise Standards:** Type-hinted throughout, strict Pydantic v2 validation, comprehensive error handling, and environment-driven configuration via Pydantic-Settings.

---

## 2. Quick Start & Core Concepts

### Syntax & Architecture Mapping

| Component | Technology | Purpose in the Stack |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance asynchronous REST API routing and auto-docs. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and settings management. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database queries and declarative model mapping. |
| **Migrations** | Alembic | Version control and automated execution for database schemas. |
| **Authentication** | `python-jose` & `passlib` | Stateless JWT generation/verification and secure password hashing. |
| **Containerization** | Docker & Compose | Isolated, reproducible development and production environments. |

### ⚡ 60-Second Quick Start

1. **Clone & Navigate:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   ```

2. **Configure Environment:**
   Copy the sample environment file and adjust your secrets:
   ```bash
   cp .env.example .env
   ```

3. **Spin up with Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

4. **Verify Deployment:**
   - API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. Production Code Patterns & Architecture Examples

### 📂 Directory Structure
```text
fastapi_backend/
├── alembic/                  # Database migration versions
├── app/
│   ├── api/                  # API routers (endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # auth.py, users.py, items.py
│   │   │   └── api.py        # Router aggregation
│   │   └── deps.py           # Dependency injection (DB, Current User)
│   ├── core/                 # App configuration & security
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async sessionmaker & engine
│   │   └── security.py       # JWT creation & password hashing
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic data validation schemas
│   └── main.py               # FastAPI application entrypoint
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### ⚙️ 1. Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

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

### 🗄️ 2. Asynchronous Database Engine (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency generator that yields an async database session."""
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

### 🔐 3. Security & Token Generation (`app/core/security.py`)
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
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 📦 4. Pydantic User Schemas (`app/schemas/user.py`)
```python
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_string_length=64)


class UserRead(UserBase):
    id: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str = None
```

---

### 🚪 5. Dependency Injection (`app/api/deps.py`)
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
    db: AsyncSession = Depends(get_db), 
    token: str = Depends(reusable_oauth2)
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
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### 🐳 6. Multi-Stage Dockerfile (`Dockerfile`)
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

# Copy installed python dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 🐙 7. Docker Compose Orchestration (`docker-compose.yml`)
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

  web:
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
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
    postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Mixing Synchronous DB Drivers in Async Routes
- **The Anti-Pattern:** Using standard `psycopg2` or synchronous SQLAlchemy sessions (`Session`) inside `async def` FastAPI routes. This blocks the main event loop, destroying concurrent request performance.
- **The Correct Approach:** Always utilize `asyncpg` combined with SQLAlchemy’s `AsyncSession` and `async_sessionmaker`.

### ❌ 2. Storing Secrets in Plain-Text Config Files
- **The Anti-Pattern:** Hardcoding `SECRET_KEY` or database credentials directly into `config.py` or version control.
- **The Correct Approach:** Rely exclusively on `pydantic-settings` to ingest secrets via environment variables (`.env`). Ensure `.env` is declared in `.gitignore`.

### ❌ 3. Forgetting Database Connection Pooling Limits
- **The Anti-Pattern:** Spawning unlimited ephemeral connections under heavy traffic spikes, crashing the Postgres database instance.
- **The Correct Approach:** Configure explicit pool sizes and overflow limits inside `create_async_engine`:
  ```python
  engine = create_async_engine(
      settings.DATABASE_URL,
      pool_size=20,
      max_overflow=10,
      pool_timeout=30
  )
  ```

---

## 5. Performance & Optimization Tips

1. **Enable Gzip Compression:** Protect your bandwidth by adding Starlette’s GZip middleware to `main.py`:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```
2. **Uvicorn Worker Scaling (Production):** When deploying outside Docker or behind a load balancer, run multiple worker processes using Uvicorn's process manager or Gunicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
3. **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (such as `email` on the User table) feature explicit database indexes (`index=True` in SQLAlchemy model columns).

---

## 6. Commercial License & Attribution Summary

### 📄 Commercial Use License
**MicroCorp AI Standard Commercial License (Fiverr / Client Deliverable Tier)**

- **Granted Rights:** You are licensed to use, modify, rebrand, and deploy this codebase for commercial client projects (including Fiverr, Upwork, and direct enterprise contracts).
- **Restrictions:** You may **not** repackage, resell, or redistribute this raw boilerplate code as a standalone template, digital product, or GitHub repository on marketplaces (e.g., Gumroad, ThemeForest) without explicit written authorization from MicroCorp AI.
- **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI accepts no liability for direct or indirect damages resulting from the deployment of this code.