# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*
> *Turnkey Enterprise Solution for High-Performance Microservices*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Asynchronous Starter Kit with JWT Authentication & Dockerized Production Pipeline**

#### **Executive Value Proposition**
Stop wasting 40+ hours bootstrapping boilerplates, configuring secure token rotations, wiring SQLAlchemy asynchronous drivers, and debugging Docker multi-stage builds. 

This production-ready turnkey solution provides a battle-tested, highly scalable backend architecture designed for enterprise microservices and high-ticket client handoffs. Engineered with asynchronous paradigms from the database layer to the web server, it delivers sub-millisecond routing overhead, type-safe data validation via Pydantic v2, and secure, stateless authentication out of the box.

#### **Key Deliverables**
- **Asynchronous Core:** Built on FastAPI, Uvicorn, and SQLAlchemy 2.0+ async sessions.
- **Robust Security Architecture:** Access/Refresh JWT token rotation, bcrypt password hashing, and dependency-injected RBAC (Role-Based Access Control).
- **Zero-Configuration Containerization:** Optimized multi-stage Dockerfiles with non-root security contexts and Docker Compose orchestration (PostgreSQL + Redis + App).
- **Developer Experience:** Fully typed codebase, automatic OpenAPI/Swagger documentation, and automated testing hooks via Pytest.

---

## 2. ## Quick Start & Core Concepts

To deploy this backend instantly, verify your environment meets the prerequisites and follow the operational matrix below.

### Prerequisites
- Docker Engine 24.0+ & Docker Compose v2+
- Python 3.11+ (for local development without containers)

### Quick Start Commands
```bash
# 1. Clone or extract the repository
cd fastapi-enterprise-starter

# 2. Configure environment variables
cp .env.example .env

# 3. Launch the full stack (App, PostgreSQL, Redis) via Docker Compose
docker compose up --build -d

# 4. Access interactive API docs
open http://localhost:8000/docs
```

### Core Architecture Concepts & Syntax Reference

| Concept | Implementation Layer | Primary Python / Docker Syntax | Purpose / Advantage |
| :--- | :--- | :--- | :--- |
| **Async ORM** | Database Access | `AsyncSession`, `select()`, `await db.execute()` | Non-blocking database I/O preventing thread pool exhaustion under heavy load. |
| **Dependency Injection** | Routing & Security | `Depends(get_db)`, `Security(verify_token)` | Modularizes cross-cutting concerns (DB sessions, auth) with automatic cleanup. |
| **Data Validation** | Request/Response | `BaseModel`, `Field(frozen=True)` | Runtime input sanitization and automatic OpenAPI schema generation. |
| **Token Handling** | Authentication | `python-jose`, `cryptography` | Cryptographically signed JSON Web Tokens for stateless session management. |
| **Multi-Stage Build** | Containerization | `FROM python:3.11-slim AS builder` | Strips build dependencies from final production image to minimize attack surface and size. |

---

## 3. ## Production Code Patterns & Architecture Examples

This architecture follows a strict Separation of Concerns (SoC) layout:
```text
app/
├── core/             # Configuration, security, database sessions
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic data transfer objects (DTOs)
├── api/              # API route controllers (v1)
├── services/         # Business logic layer
└── main.go / main.py # Application entry point
```

### 3.1 Environment & Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

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

settings = Settings()
```

### 3.2 Asynchronous Database Engine (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
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
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    """Dependency injection generator for database sessions."""
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

### 3.3 JWT Security & Authentication Service (`app/core/security.py`)
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
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
```

### 3.4 Authentication Router & Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from app.schemas.token import TokenSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
    
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
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

# Stage 2: Runtime Environment
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

# Create non-privileged system user for security
RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3.6 Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: redis_cache
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build: .
    container_name: fastapi_app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async Drivers (The Thread-Starvation Trap):**
   * *Anti-Pattern:* Using `psycopg2` (synchronous) inside an async FastAPI route without wrapping it in `run_in_threadpool`. This blocks the main event loop.
   * *Fix:* Strictly utilize asynchronous drivers like `asyncpg` (`postgresql+asyncpg://...`) for full non-blocking performance.
2. **Hardcoding Secret Keys:**
   * *Anti-Pattern:* Storing JWT secrets or database connection URIs directly in code files or committing `.env` files to Git.
   * *Fix:* Enforce Pydantic validation via `BaseSettings` reading exclusively from environment variables injected securely via Docker secrets or orchestrator configuration.
3. **Not Managing Database Connection Pools:**
   * *Anti-Pattern:* Opening a new database engine instance on every incoming request cycle.
   * *Fix:* Instantiate a single global engine reference (`create_async_engine`) at startup and yield session instances via dependency injection.
4. **Ignoring Database Session Leakage:**
   * *Anti-Pattern:* Forgetting to explicitly close or commit/rollback sessions during uncaught exceptions.
   * *Fix:* Always utilize context managers (`async with AsyncSessionLocal() as session:`) or generator-based dependencies with automatic `try/except/finally` teardown.

---

## 5. ## Performance & Optimization Tips

- **Uvicorn Worker Scaling:** Always run Uvicorn behind a process manager or configure worker counts based on CPU cores (`--workers $(nproc)`) in production Dockerfiles.
- **Pydantic v2 Model Serialization:** Utilize `.model_dump(mode='json')` instead of older v1 `.dict()` calls to leverage lightning-fast Rust-backed serialization optimizations.
- **Database Query Indexing:** Ensure foreign keys and high-frequency lookup columns (e.g., `users.email`, `tokens.jti`) have explicit database indexes (`index=True`).
- **Response Caching Layer:** Integrate Redis caching decorators (`fastapi-cache2`) for heavy, read-heavy query endpoints that change infrequently to bypass database overhead entirely.

---

## 6. ## Commercial License & Attribution Summary

### **The Agency Enterprise License (AEL-v1.0)**

* **Authorized Usage:** This digital product is licensed for deployment within commercial client deliverables, internal engineering boilerplates, and SaaS production environments developed by the purchasing entity or designated Fiverr client.
* **Restrictions:** Redistribution, resale, or public publishing of this specific source code as a standalone competing boilerplate kit is strictly prohibited.
* **Warranty Disclaimer:** Provided *as-is* without warranty of any kind, express or implied. The Agency Engineering Division disclaims all liability for infrastructure misconfigurations or security vulnerabilities arising from improper environment management.

> *Engineered with precision by The Agency — Backend Architecture Division.*