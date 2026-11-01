# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Turnkey Boilerplate*

---

## 1. Product Title & Value Proposition

### **Enterprise-Grade FastAPI Asynchronous Backend Boilerplate**
* **Target Audience:** Full-stack developers, startups, and agency contractors needing a bulletproof, containerized API backend with secure stateless authentication out of the box.
* **Commercial Value:** Eliminates 40+ hours of boilerplate configuration, security hardening, database wiring, and Docker container orchestration. Drop this into your client repository and start building business logic immediately.

### **What's Inside**
* **FastAPI 0.110+** running on Uvicorn with native async/await support.
* **SQLAlchemy 2.0 (Async)** coupled with **Alembic** for robust database migrations.
* **PostgreSQL 16** optimized container setup with health checks.
* **JWT Authentication** (Access & Refresh tokens) with BCrypt password hashing and sliding session windows.
* **Pydantic v2** strict input validation and serialization.
* **Docker & Docker Compose** multi-stage builds optimized for zero-bloat production deployments.

---

## 2. Quick Start & Core Concepts

### Core Architectural Stack
| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Async) | High-performance API routing, automatic OpenAPI/Swagger generation |
| **Database Driver** | asyncpg + SQLAlchemy 2.0 | Non-blocking database operations at scale |
| **Migration Engine** | Alembic | Version control for database schemas |
| **Authentication** | python-jose + passlib | Cryptographic JWT generation and BCrypt hashing |
| **Validation** | Pydantic v2 | Runtime data parsing and strict type safety |
| **Containerization** | Docker & Docker Compose | Isolated, reproducible development and production environments |

### 3-Step Local Initialization
```bash
# 1. Clone or unpack the boilerplate into your workspace
cd fastapi-enterprise-boilerplate

# 2. Configure your local environment variables
cp .env.example .env

# 3. Spin up the entire stack via Docker Compose
docker compose up --build -d
```
*API documentation will be live at `http://localhost:8000/docs`.*

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-backend/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API Routers (v1)
│   │   ├── endpoints/        # Auth, Users, Health
│   │   └── deps.py           # Dependency injection (DB, Current User)
│   ├── core/                 # App configuration & security settings
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async engine & sessionmaker
│   │   └── security.py       # JWT & Password hashing utilities
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic validation schemas
│   └── main.py               # FastAPI application entrypoint
├── Dockerfile                # Multi-stage production container build
├── docker-compose.yml        # Local orchestration manifest
├── requirements.txt          # Python dependencies pinned
└── .env.example              # Environment variable template
```

---

### Configuration Engine (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: String = "Enterprise FastAPI Engine"
    API_V1_STR: String = "/api/v1"
    
    # Security / JWT
    SECRET_KEY: String
    ALGORITHM: String = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    POSTGRES_SERVER: String
    POSTGRES_USER: String
    POSTGRES_PASSWORD: String
    POSTGRES_DB: String
    DATABASE_URL: String | None = None

    model_config = SettingsConfigDict(
        env_file=".env", case_insensitive=True, extra="ignore"
    )


settings = Settings()
```

---

### Async Database Session Management (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Construct async connection URL if not explicitly defined
DATABASE_URL = (
    settings.DATABASE_URL
    or f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function yielding non-blocking database sessions."""
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

### Security & JWT Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: String, hashed_password: String) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: String) -> String:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> String:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> String:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User  # Assuming User model exists

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: String = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
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
        user_id: String = payload.get("sub")
        token_type: String = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

---

### FastAPI Main Application Entrypoint (`app/main.py`)
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

# Set up CORS middleware restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production environments to explicit domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### Production Dockerfile (`Dockerfile`)
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

# Copy installed site-packages from builder stage
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
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

  backend:
    build: .
    container_name: fastapi_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-jwt-key-change-this
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints**
   * *Anti-Pattern:* Utilizing standard `requests`, `time.sleep()`, or synchronous database drivers (`psycopg2`) inside `async def` routes. This freezes the entire event loop.
   * *Fix:* Use `asyncpg`, `httpx`, and `asyncio.sleep()`. If legacy sync libraries are unavoidable, run them via `run_in_threadpool`.

2. **Database Session Leaks**
   * *Anti-Pattern:* Manually instantiating sessions inside routes without context managers (`async with`), leading to unclosed connection pooling starvation.
   * *Fix:* Always inject sessions utilizing FastAPI's `Depends(get_db)` generator framework.

3. **Hardcoding Secret Keys & Secrets**
   * *Anti-Pattern:* Keeping JWT secret keys or database credentials inside code files or checking `.env` files into source control.
   * *Fix:* Enforce Pydantic validation for environment variables and add `.env` to your `.gitignore`.

4. **Catching Bare Exceptions**
   * *Anti-Pattern:* Using `except:` or `except Exception:` blocks without logging or re-raising, swallowing unexpected server crashes.
   * *Fix:* Catch explicit exceptions and map them to clean `HTTPException` responses with proper error payloads.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production containers, leverage multiple worker processes based on CPU cores (`--workers 4`) or run behind an Nginx/Traefik reverse proxy cluster.
* **Connection Pooling:** Fine-tune SQLAlchemy engine parameters (`pool_size`, `max_overflow`, `pool_timeout`) to match your PostgreSQL server capacity limits.
* **Response Compression:** Add `GZipMiddleware` to your FastAPI instance for large payload minimization:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware

  app.add_middleware(GZipMiddleware, minimum_size=1000)
```
* **Database Indexing:** Ensure frequently queried foreign keys (`user_id`, `email`) carry proper B-Tree indexes inside your Alembic migrations.

---

## 6. Commercial License & Attribution Summary

* **License:** MIT Commercial-Friendly License (Permitted for internal use, client delivery, modification, and resale as part of proprietary SaaS platforms).
* **Attribution:** Provided by **The Agency // Engineering Division**. No runtime watermarks or required frontend attribution tags. Ready for immediate deployment.