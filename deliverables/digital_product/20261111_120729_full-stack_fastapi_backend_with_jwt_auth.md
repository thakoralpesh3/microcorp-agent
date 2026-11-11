# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Production Series*  
> **Product ID:** `MC-FASTAPI-JWT-DOCKER-001`  
> **Target Audience:** Enterprise Clients, Senior Full-Stack Engineers, Freelance Solution Architects

---

## 1. # Product Title & Value Proposition

### Product Title
**The Production-Grade FastAPI, JWT Authentication & Docker Microservice Boilerplate**

### Value Proposition
Stop wasting 40+ hours writing boilerplate, configuring async database sessions, debugging CORS middleware, and structuring secure JWT authentication flows from scratch. 

This turnkey solution delivers an enterprise-ready, battle-tested backend architecture designed for scale. Featuring **FastAPI (async)**, **SQLAlchemy 2.0 (async)**, **Pydantic v2**, **PostgreSQL**, **Redis**, and **Docker Compose**, this codebase provides everything you need to ship secure, high-performance REST APIs to production on day one. 

---

## 2. ## Quick Start & Core Concepts

### Core Architectural Stack
| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async REST API routing and automated OpenAPI docs. |
| **Data Validation** | Pydantic | `2.6+` | Strict payload validation, serialization, and settings management. |
| **ORM / Database** | SQLAlchemy | `2.0+` (Async) | Non-blocking database operations with PostgreSQL. |
| **Database Driver** | asyncpg | `0.29+` | Blazing-fast native PostgreSQL async driver. |
| **Authentication** | python-jose & passlib | Latest | Secure JWT creation, validation, and bcrypt password hashing. |
| **Caching / Queues** | Redis | `7.0+` | Token blacklisting, rate limiting, and background worker state. |
| **Containerization** | Docker & Compose | Latest | Zero-friction multi-container local and production deployment. |

### 3-Step Local Spin-Up

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Infrastructure & API via Docker:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify API Health:**
   Open your browser to [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic BaseSettings config
│   ├── database.py       # Async SQLAlchemy session factory
│   └── security.py       # JWT creation, verification & hashing
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic validation schemas
├── api/
│   ├── v1/
│   │   ├── api.py        # Router aggregation
│   │   └── endpoints/
│   │       ├── auth.py   # Login & Token generation
│   │       └── users.py  # User CRUD & /me routes
│   └── deps.py           # FastAPI Depends injections
├── main.py               # FastAPI application factory
Dockerfile
docker-compose.yml
requirements.txt
```

---

### Code Component 1: Application Factory (`app/main.py`)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables (Use Alembic in production!)
    await init_db()
    yield
    # Shutdown: Clean up connections if needed


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    application.include_router(api_router, prefix=settings.API_V1_STR)
    return application


app = get_application()
```

---

### Code Component 2: Async Database Session (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
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


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency function that yields db sessions per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        # Development helper: create tables. Use Alembic migrations for production.
        await conn.run_sync(Base.metadata.create_all)
```

---

### Code Component 3: Security & JWT Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

---

### Code Component 4: Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

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
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token type",
            )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = await db.get(User, int(token_data.sub))
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

### Code Component 5: Docker Configuration

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: microcorp_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - SERVER_HOST=0.0.0.0
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=microcorp_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - .:/app

  db:
    image: postgres:15-alpine
    container_name: microcorp_postgres
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=microcorp_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d microcorp_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: microcorp_redis
    restart: always
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

* **❌ Anti-Pattern 1: Using Synchronous DB Drivers in Async Routes**
  * *Gotcha:* Using standard `psycopg2` inside async `async def` route functions blocks the main event loop, destroying concurrent throughput.
  * *Fix:* Always use `asyncpg` with SQLAlchemy's `create_async_engine()`.
* **❌ Anti-Pattern 2: Hardcoding Configuration Values**
  * *Gotcha:* Hardcoding database credentials or JWT secrets inside code modules.
  * *Fix:* Always utilize `pydantic-settings` to load configuration strictly from environment variables and `.env` files.
* **❌ Anti-Pattern 3: Ignoring Database Session Lifecycles**
  * *Gotcha:* Manually opening sessions without proper context managers leading to connection leaks and pool exhaustion.
  * *Fix:* Utilize FastAPI's dependency injection system (`Depends(get_db)`) to guarantee correct allocation and teardown.
* **❌ Anti-Pattern 4: Missing Token Revocation Logic**
  * *Gotcha:* Relying solely on JWT expiration without a mechanism to invalidate tokens upon logout or password reset.
  * *Fix:* Implement Redis-backed token blacklisting for active sessions.

---

## 5. ## Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** In production, run Uvicorn behind a process manager or configure multiple workers matching your CPU core count:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
2. **Connection Pooling Optimization:** Tune your SQLAlchemy `pool_size` and `max_overflow` parameters based on database tier specifications and expected concurrent load peaks.
3. **Pydantic Model Compilation:** For high-throughput endpoints, leverage Pydantic v2's Rust-backed core (`pydantic-core`) which automatically accelerates validation speed up to 5x compared to v1.
4. **Response Caching:** Cache heavy, read-heavy query payloads in Redis using custom dependency decorators to bypass DB roundtrips entirely.

---

## 6. ## Commercial License & Attribution Summary

### Commercial License Agreement
* **Copyright © 2024 MicroCorp AI & The Agency Engineering Division.** All rights reserved.
* **Grant of Rights:** This turnkey solution is licensed under the **MicroCorp Commercial Developer License**. Purchasers and authorized Fiverr clients are granted a perpetual, non-exclusive, worldwide license to modify, deploy, and scale this codebase for commercial client projects or internal enterprise applications.
* **Restrictions:** Redistribution of this codebase as a competing template, boilerplates marketplace asset, or open-source framework without explicit written authorization from MicroCorp AI is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied.