# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Production Series*  
> **Product Type:** Full Turnkey Solution for Enterprise & High-End Fiverr Clients  
> **Target Audience:** Full-Stack Engineers, DevOps Specialists, Agency Founders  

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Enterprise Engine
Stop wasting 40+ hours writing boilerplate authentication, setting up asynchronous database connection pools, configuring Docker multi-stage builds, and structuring Alembic migrations. 

This turnkey solution provides a battle-tested, highly performant, type-safe FastAPI backend architecture. Designed from the ground up for strict enterprise constraints, it features secure JWT-based authentication with role-based access control (RBAC), SQLAlchemy 2.0 asynchronous ORM integration, Pydantic v2 validation, and a production-grade Docker compose setup with zero unhandled edge cases.

### What's Inside:
- **Zero Configuration Drift:** Fully containerized development and production environments using Docker and Docker Compose.
- **Enterprise Security:** Cryptographically secure JWT implementation with refresh token rotation patterns and secure cookie handling.
- **Modern Python Standards:** 100% Async support utilizing Python 3.11+, SQLAlchemy 2.0 AsyncSessions, and Pydantic v2.
- **Client-Ready Handover:** Structured cleanly so you can drop this repository into your client's workspace, change the environment variables, and bill for 2 weeks of development time instantly.

---

## 2. Quick Start & Core Concepts

Get your local containerized environment running in under 60 seconds.

### Prerequisites
- Docker Engine v24.0+ & Docker Compose v2.20+
- Python 3.11+ (if running bare-metal migrations)

### Quick Start Commands
```bash
# 1. Clone the repository and navigate to root
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-engine.git
cd fastapi-jwt-docker-engine

# 2. Configure environment variables
cp .env.example .env

# 3. Spin up the stack (PostgreSQL, Redis, and FastAPI)
docker compose up --build -d

# 4. Run database migrations via Alembic inside the container
docker compose exec api alembic upgrade head

# 5. Verify health check
curl http://localhost:8000/health
```

### Core Architecture Concepts
| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **API Framework** | FastAPI (v0.110+) | High-performance asynchronous routing, automatic OpenAPI/Swagger generation, dependency injection. |
| **Data Validation** | Pydantic v2 | Strict payload parsing, serialization, and runtime type enforcement. |
| **ORM & Database** | SQLAlchemy 2.0 (Async) + PostgreSQL | Non-blocking database queries, connection pooling, and explicit unit-of-work patterns. |
| **Migration Engine** | Alembic | Version-controlled schema evolutions synchronized with SQLAlchemy models. |
| **Authentication** | python-jose & passlib (Bcrypt) | Stateless JWT issuance, verification, and cryptographic password hashing. |
| **Containerization** | Docker (Multi-stage) | Minimal image footprint, separated build dependencies, secure non-root runtime user. |

---

## 3. Production Code Patterns & Architecture Examples

Here is the structural blueprint of the application. The codebase follows a strict modular domain layout to maximize maintainability at scale.

```text
app/
├── core/
│   ├── config.py         # Pydantic Settings management
│   ├── database.py       # Async engine & sessionmaker
│   ├── security.py       # JWT creation, verification, hashing
│   └── security_deps.py  # FastAPI Depends for Auth & RBAC
├── models/
│   └── user.py           # SQLAlchemy User ORM Model
├── schemas/
│   └── user.py           # Pydantic Request/Response models
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py   # Login, token refresh, registration
│   │   │   └── users.py  # Protected user routes
│   │   └── router.py     # API Router aggregation
└── main.py               # Application factory & middleware
```

### 3.1 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

### 3.2 Asynchronous Database Session (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
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

### 3.3 Security & JWT Engine (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

### 3.4 Authentication Dependencies (`app/core/security_deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


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

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
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

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.6 Docker Compose Infrastructure (`docker-compose.yml`)
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
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_api
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
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

1. **Blocking I/O in Async Routes (`def` vs `async def`)**
   - *Anti-Pattern:* Using synchronous database drivers (like `psycopg2`) or standard blocking libraries (like `requests` or time-heavy CPU tasks) inside `async def` endpoints, which starves the event loop.
   - *Solution:* Use `asyncpg` for database operations. If synchronous blocking libraries must be used, define the path operation with standard `def` so FastAPI executes it in an external threadpool.

2. **Ignoring Database Connection Pool Limits**
   - *Anti-Pattern:* Failing to set explicit `pool_size` and `max_overflow` parameters on the SQLAlchemy async engine, leading to unhandled connection spikes and database crash under load.
   - *Solution:* Explicitly bound your connection pools based on your Postgres worker limits (`pool_size=20`, `max_overflow=10`).

3. **Insecure Secret Management in Docker Containers**
   - *Anti-Pattern:* Hardcoding JWT `SECRET_KEY` directly inside `docker-compose.yml` or committing `.env` files containing production secrets to version control.
   - *Solution:* Always use external environment injection, Docker Secrets, or secret managers (AWS Secrets Manager, Vault) when deploying to production infrastructure.

4. **Catching Generic Exceptions Globally Without Logging**
   - *Anti-Pattern:* Using `except Exception:` blocks that silently fail or return empty 500 errors without tracing stack details.
   - *Solution:* Implement a custom global exception handler that logs exact stack traces while returning standardized JSON error envelopes to clients.

---

## 5. Performance & Optimization Tips

- **Uvicorn Worker Scaling:** In production, do not run single-process Uvicorn. Scale workers relative to your CPU cores using a process manager or command pattern:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
- **Response Compression:** Install `starlette.middleware.gzip.GZipMiddleware` to compress large JSON responses automatically and reduce downstream payload bandwidth.
- **Database Indexing:** Ensure foreign keys and frequently queried fields (such as `email` on the user model) feature explicit database indexes (`index=True` in SQLAlchemy model definitions).
- **ORM Lazy Loading Pitfalls:** SQLAlchemy 2.0 async engine does not support lazy loading by default (`MissingGreenlet` error). Always use explicit `selectinload` or `joinedload` options when querying relationships.

---

## 6. Commercial License & Attribution Summary

### 📄 Commercial Terms of Use
- **Single Client Commercial License:** Purchasing this product grants you a perpetual, non-exclusive license to use, modify, and rebrand this codebase for **one (1)** commercial client project (e.g., a Fiverr gig, Upwork contract, or custom client engagement).
- **Agency Unlimited License:** If purchased under an Agency tier, you may deploy this solution across an unlimited number of internal and external client systems.
- **Restrictions:** You are strictly prohibited from reselling, redistributing, or publishing this digital product as a standalone boilerplate, template pack, or open-source repository on platforms like GitHub, Gumroad, or Envato.

### 🛡️ Attribution & Warranty
*Developed by **The Agency Engineering Division** for MicroCorp AI.*  
This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI and The Agency assume no liability for damages resulting from the execution, deployment, or misuse of this code in production environments. Always perform rigorous penetration testing and independent security audits prior to live commercial deployment.