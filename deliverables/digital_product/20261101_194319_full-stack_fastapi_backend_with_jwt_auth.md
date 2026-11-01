# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*  
> *Turnkey Client Deliverable #842 — Production-Ready Code & Infrastructure Blueprint*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Engine: Production-Grade Async Backend with JWT Authentication, PostgreSQL, Alembic, and Dockerized Architecture**

Stop wasting weeks architecting boilerplate code, setting up async database drivers, configuring secure OAuth2/JWT password flows, and writing complex multi-stage Dockerfiles. 

This enterprise-grade turnkey solution provides a battle-tested, highly performant FastAPI backend engineered for immediate commercial deployment. Designed by Senior Backend Architects, this repository template handles high-concurrency workloads out of the box with zero configuration drift.

### **Key Business & Technical Benefits**
* **Time-to-Market Acceleration:** Deploy a fully functional, secure REST API in under 5 minutes.
* **Security First:** Implements industry-standard cryptographic practices (Argon2/Bcrypt password hashing, RS256/HS256 JWT access and refresh token rotation).
* **Enterprise Scalability:** Built entirely on asynchronous paradigms (`async`/`await`), leveraging SQLAlchemy 2.0 and asyncpg for non-blocking database queries.
* **Zero-Hassle Infrastructure:** Fully containerized with Docker Compose, including health checks, persistent volumes, and automatic database migrations via Alembic.
* **Strict Type Safety:** Fully typed Python codebase leveraging Pydantic v2 for lightning-fast payload validation and serialization.

---

## 2. ## Quick Start & Core Concepts

### **Directory Structure**
```text
fastapi-enterprise-engine/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API routers (v1 endpoints)
│   ├── core/                 # Config, security, database sessions
│   ├── models/               # SQLAlchemy ORM database models
│   ├── schemas/              # Pydantic data validation schemas
│   ├── services/             # Business logic layer
│   └── main.py               # FastAPI application entrypoint
├── tests/                    # Pytest integration & unit tests
├── .env.example              # Environment variable template
├── Dockerfile                # Multi-stage production container build
├── docker-compose.yml        # Local orchestration configuration
└── requirements.txt          # Pinned dependency manifest
```

### **Core Stack Syntax & Architectural Mapping**

| Component | Technology Choice | Architectural Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance asynchronous routing and automatic OpenAPI documentation. |
| **Data Validation** | Pydantic v2 | High-speed data parsing and serialization written in Rust core. |
| **ORM & Driver** | SQLAlchemy 2.0 + `asyncpg` | Non-blocking database interactions with modern Python type hints. |
| **Migrations** | Alembic | Version-controlled database schema evolution. |
| **Authentication** | OAuth2 with JWT | Stateless token-based security with access/refresh lifecycle. |
| **Containerization**| Docker & Compose | Isolated, reproducible runtime environments for dev and production. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **Environment Configuration (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

### **Database Session Management (`app/core/database.py`)**
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

### **JWT Security & Authentication Dependency (`app/core/security.py`)**
```python
from datetime import datetime, timedelta
from typing import Any
from jose import jwt, JWTError
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


def create_access_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
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
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user
```

### **Multi-Stage Production Dockerfile (`Dockerfile`)**
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
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Docker Compose Infrastructure (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
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

  api:
    build: .
    container_name: fastapi_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction
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

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous and Asynchronous DB Drivers:**
   * *Anti-Pattern:* Using standard `psycopg2` or `sqlite3` inside `async def` path operations. This blocks the entire event loop.
   * *Correction:* Always use `asyncpg` with SQLAlchemy's `create_async_engine()` and `AsyncSession`.
2. **Hardcoding Secret Keys & Configuration:**
   * *Anti-Pattern:* Placing JWT secrets and database credentials directly inside Python modules.
   * *Correction:* Implement `pydantic-settings` to enforce environment variable ingestion at runtime.
3. **Improper Exception Handling in DB Context Managers:**
   * *Anti-Pattern:* Failing to roll back transactions on exception, leaving the database session in an unrecoverable state.
   * *Correction:* Ensure your session dependency explicitly calls `await session.rollback()` inside a `try/except` block.
4. **Ignoring Connection Pooling Limits:**
   * *Anti-Pattern:* Instantiating unconstrained database connections per request, causing connection pool exhaustion under high traffic.
   * *Correction:* Set explicit `pool_size` and `max_overflow` parameters on the SQLAlchemy async engine.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a reverse proxy (Nginx/Traefik), scale Uvicorn workers using `gunicorn` with Uvicorn worker class:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Pydantic v2 Performance:** Utilize compiled models and avoid unnecessary custom validators when built-in field constraints (`Field(ge=0, max_length=50)`) suffice.
* **Database Indexing:** Ensure foreign keys and high-cardinality query columns (e.g., `email`, `username`) possess explicit database indexes in your Alembic migration scripts.
* **Response Compression:** Integrate Starlette's `GZipMiddleware` to minimize payload sizes for high-volume JSON responses:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware

  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```

---

## 6. ## Commercial License & Attribution Summary

* **Product License:** Commercial Developer License (Single-Entity & Client Projects).
* **Usage Rights:** You are authorized to use, modify, adapt, and deploy this codebase for internal use, SaaS applications, and direct delivery to paid consulting/Fiverr clients.
* **Restrictions:** Redistribution, resale, or publishing of this code as a standalone competing boilerplate template, open-source template repository, or digital course material is strictly prohibited.
* **Warranty Disclaimer:** Provided *as is*, without warranty of any kind, express or implied. The Agency Engineering Division assumes no liability for production downtime or misconfigured cloud deployments.