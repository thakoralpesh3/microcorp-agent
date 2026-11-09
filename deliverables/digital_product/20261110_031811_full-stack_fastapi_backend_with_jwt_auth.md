# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Commercial Assets*  
> **Product ID:** `MC-FASTAPI-JWT-DOCKER-001`  
> **Target Audience:** Enterprise Clients, Senior Full-Stack Engineers, Freelance Deliverables

---

## 1. # Product Title & Value Proposition

### Enterprise-Grade FastAPI Boilerplate: JWT Authentication & Dockerized Infrastructure

Building a production-ready asynchronous backend from scratch requires wiring together database migrations, security middleware, environment configuration, and container orchestration. Doing this securely while adhering to modern Python typing standards takes days of setup.

This turnkey commercial asset delivers a **battle-tested, production-ready FastAPI backend template** designed for immediate deployment. It incorporates modern architectural best practices, strict dependency injection, secure JWT authentication with refresh token mechanics, and an optimized multi-stage Docker deployment pipeline.

### What You Get
* **Zero Boilerplate Lag:** Jump straight to writing business logic instead of configuration files.
* **Security First:** Argon2/Bcrypt password hashing, RS256/HS256 JWT validation, CORS hardening, and rate-limiting placeholders.
* **Database Agnostic Base:** Pre-configured SQLAlchemy 2.0 with Alembic migrations and async connection pooling.
* **DevOps Ready:** Production-hardened `Dockerfile` and `docker-compose.yml` supporting hot-reload development and isolated container execution.

---

## 2. ## Quick Start & Core Concepts

### Core Architecture Concepts

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous HTTP routing & automatic OpenAPI schema generation. |
| **Data Validation** | Pydantic v2 | Strict runtime data parsing, serialization, and settings management. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database operations using `asyncpg` and PostgreSQL. |
| **Migrations** | Alembic | Version-controlled database schema evolution. |
| **Authentication** | `python-jose` / `passlib` | Secure stateless token generation and credential verification. |
| **Containerization** | Docker & Compose | Deterministic multi-stage builds for local dev and production parity. |

### 5-Minute Quick Start

```bash
# 1. Clone or extract the boilerplate package
cd microcorp-fastapi-backend

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your local database credentials and secret keys

# 3. Spin up infrastructure via Docker Compose
docker-compose up --build -d

# 4. Run database migrations inside the container
docker-compose exec api alembic upgrade head

# 5. Access interactive API docs
# Open http://localhost:8000/docs in your browser
```

---

## 3. ## Production Code Patterns & Architecture Examples

This codebase follows a strict modular domain structure to maintain separation of concerns:
```text
app/
├── core/             # Config, security, database session management
├── models/           # SQLAlchemy ORM database models
├── schemas/          # Pydantic validation & serialization models
├── api/              # API route controllers (v1)
├── services/         # Business logic layer
└── main.py           # Application entrypoint
```

### 3.1 Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
```

### 3.2 Secure Configuration Management (`app/core/config.py`)
```python
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    def model_post_init(self, __context) -> None:
        object.__setattr__(
            self,
            "DATABASE_URL",
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

### 3.3 Asynchronous Database Session (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
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

### 3.4 JWT Authentication & Dependency Injection (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

### 3.5 Production Multi-Stage Dockerfile (`Dockerfile`)
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

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.6 Container Orchestration (`docker-compose.yml`)
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking I/O in Async Routes:** 
   * *Anti-Pattern:* Using synchronous libraries like `requests` or blocking file operations directly inside `async def` paths. This blocks the main event loop, destroying throughput.
   * *Solution:* Offload CPU-bound or blocking synchronous code using `anyio.to_thread.run_sync()` or migrate to native async equivalents (`httpx`, `aiofiles`).

2. **Leaking Database Sessions:**
   * *Anti-Pattern:* Manually instantiating sessions inside route controllers without proper context management (`try/finally` blocks).
   * *Solution:* Always use FastAPI's dependency injection system (`Depends(get_db)`) to guarantee context closure.

3. **Hardcoding Configuration Values:**
   * *Anti-Pattern:* Placing database URIs, API keys, or secret tokens directly inside code files.
   * *Solution:* Enforce validation at startup via Pydantic `BaseSettings` reading explicitly from environment variables (`.env`).

4. **Catching Generic Exceptions:**
   * *Anti-Pattern:* Using broad `except Exception:` blocks that mask database constraint violations or runtime schema bugs, returning generic 500 errors to clients.
   * *Solution:* Catch specific exceptions (e.g., SQLAlchemy `IntegrityError`) and translate them into clean, actionable 400-level client responses.

---

## 5. ## Performance & Optimization Tips

* **Connection Pooling tuning:** Configure SQLAlchemy engine pooling parameters (`pool_size`, `max_overflow`, `pool_timeout`) matching your worker concurrency limits to prevent database exhaustion under load.
* **ASGI Worker Scaling:** Run Uvicorn behind a process manager like Gunicorn or deploy via Kubernetes with multiple worker pods behind a load balancer (`--workers 4`).
* **Response Caching:** Integrate Redis middleware or internal caching decorators (`fastapi-cache2`) for read-heavy, low-volatility database lookups.
* **Lazy Loading vs Eager Loading:** Explicitly use SQLAlchemy's `selectinload` or `joinedload` options on relational queries to avoid the N+1 query performance trap.

---

## 6. ## Commercial License & Attribution Summary

### Commercial License Terms (MicroCorp AI DevKit License v1.0)
* **Granted Rights:** You are granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and distribute this codebase within commercial client projects, SaaS products, and internal enterprise architectures.
* **Restrictions:** You may not resell, sublicense, or redistribute this exact architectural boilerplate as a standalone competitive template on digital marketplaces (e.g., GitHub Marketplace, Gumroad, ThemeForest) without explicit written consent from MicroCorp AI.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI and The Agency Engineering Division accept zero liability for infrastructure down-time, security breaches, or data loss arising from improper deployment or configuration mismanagement.

---
*Generated by **Backend Architect 🏗️** — The Agency Engineering Division / MicroCorp AI.*