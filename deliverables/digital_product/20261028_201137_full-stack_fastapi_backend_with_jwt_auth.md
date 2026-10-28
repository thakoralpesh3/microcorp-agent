# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*  
> **Product Code:** MC-TURKEY-FASTAPI-042  
> **Target Audience:** Enterprise Clients, Senior Engineers, and Freelance Deliverables

---

## 1. # Product Title & Value Proposition

### Product Title
**Production-Grade FastAPI Backend Boilerplate with Async PostgreSQL, JWT Authentication, Alembic Migrations, and Docker Multi-Stage Builds.**

### Value Proposition
Building a modern, secure, and performant backend from scratch takes weeks of boilerplate configuration. This turnkey solution provides an enterprise-ready, battle-tested FastAPI architecture designed for horizontal scale, strict typing, and zero-downtime containerized deployments. 

Instead of spending 40+ hours stitching together Pydantic v2, SQLAlchemy 2.0 Async, python-jose, and Docker, you can deploy a secure API with integrated auth, automated migrations, and health checks in under 5 minutes.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview
This system uses a decoupled, domain-driven structure optimized for async I/O. 

```
[ Client / Frontend ] 
       │ (HTTPS / Bearer Token)
       ▼
[ Nginx / Reverse Proxy ] (Optional Edge)
       │
       ▼
[ FastAPI Application (Uvicorn Workers) ] ──(Async SQLAlchemy 2.0)──► [ PostgreSQL 16 ]
       │
       └──(Redis Client)──► [ Redis Cache / Rate Limiter ]
```

### Clean Syntax & Configuration Reference

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async routing & automatic OpenAPI docs |
| **Data Validation** | Pydantic | `2.6+` | Runtime data parsing and settings management via environment variables |
| **ORM** | SQLAlchemy | `2.0+` | Enterprise async ORM with type-safe query execution |
| **Migrations** | Alembic | `1.13+` | Version-controlled database schema evolution |
| **Auth** | python-jose & passlib | Latest | Cryptographic JWT generation and bcrypt password hashing |
| **Containerization** | Docker / Compose | `20.10+` | Multi-stage production builds and local orchestration |

---

## 3. ## Production Code Patterns & Architecture Examples

### 3.1 Project File Tree
```
fastapi-production-boilerplate/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   └── main.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### 3.2 Configuration Management (`app/core/config.py`)
Utilizes Pydantic BaseSettings to enforce environment variable validation at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### 3.3 Asynchronous Database Engine (`app/core/database.py`)
Sets up the async SQLAlchemy session maker with connection pooling.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
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

---

### 3.4 Security & JWT Utilities (`app/core/security.py`)
Handles password hashing via Passlib and token creation via Python-Jose.

```python
from datetime import datetime, timedelta, timezone
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 3.5 API Dependencies (`app/api/deps.py`)
Extracts and validates JWT Bearer tokens, injecting the current user into endpoints.

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
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### 3.6 Docker Setup (`Dockerfile`)
Multi-stage build pattern for minimizing container image size and eliminating build-time dependencies.

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

### 3.7 Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app_db"]
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
      - PROJECT_NAME=FastAPI Enterprise
      - SECRET_KEY=supersecretjwtkeychangeinproduction123
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=app_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Using Synchronous DB Drivers (`psycopg2`) inside Async FastAPI Endpoints**
   * *Anti-Pattern:* Mixing synchronous database calls blocks the main event loop, destroying concurrent request handling.
   * *Correction:* Always use `asyncpg` with SQLAlchemy's `create_async_engine`.
2. **Hardcoding Secrets or Storing Plaintext Passwords**
   * *Anti-Pattern:* Committing `.env` files or using fallback strings like `secret123` in production code.
   * *Correction:* Enforce strict Pydantic settings validation and inject secrets via Docker Swarm, Kubernetes Secrets, or AWS Parameter Store.
3. **Omitting `expire_on_commit=False` in SQLAlchemy Session Makers**
   * *Anti-Pattern:* Accessing ORM model attributes after committing an async session throws an `DetachedInstanceError`.
   * *Correction:* Always configure `expire_on_commit=False` on your `async_sessionmaker`.
4. **Not Using Connection Pooling Bounds**
   * *Anti-Pattern:* Spawning infinite database connections under load, resulting in Postgres `FATAL: sorry, too many clients already`.
   * *Correction:* Explicitly set `pool_size` and `max_overflow` on the async engine.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, run Uvicorn behind a process manager or scale workers relative to CPU cores (`--workers $(nproc)`). For high-throughput I/O, utilize Uvicorn paired with `uvloop`.
* **Database Indexing:** Ensure foreign keys and high-cardinality lookup columns (like user `email`) have explicit B-tree indexes defined via Alembic migrations.
* **Response Serialization:** For large datasets, utilize Pydantic's `.model_dump()` sparingly or return native dictionaries if serialization bottlenecks occur.
* **Caching Layers:** Implement Redis caching for read-heavy, low-mutation endpoints (e.g., configuration tables, user profile lookups) using FastAPI's dependency injection caching or custom middleware.

---

## 6. ## Commercial License & Attribution Summary

* **License:** MIT Commercial-Grade License
* **Usage Rights:** Permitted for commercial client delivery, internal enterprise deployment, and SaaS product foundations.
* **Attribution:** Provided by **The Agency Engineering Division** / MicroCorp AI. No warranty or liability is assumed by the authors; users are responsible for security audits prior to live production releases.