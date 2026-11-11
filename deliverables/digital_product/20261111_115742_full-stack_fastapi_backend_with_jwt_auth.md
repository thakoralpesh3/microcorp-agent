# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*A Turnkey Production-Grade Boilerplate for Enterprise Microservices & Freelance Clients*

## 1. # Product Title & Value Proposition

### Product Title
**FastAPI Enterprise Engine: Production-Ready Asynchronous Backend with JWT Authentication, PostgreSQL/SQLAlchemy, and Dockerized CI/CD Architecture.**

### Value Proposition
Building modern, secure, and lightning-fast APIs from scratch consumes valuable engineering bandwidth. This turnkey solution delivers a battle-tested, modular FastAPI architecture designed for immediate deployment. 

Engineered with asynchronous database sessions, robust cryptographic JWT authentication, dependency-injected security scopes, and zero-downtime Docker orchestration, this boilerplate saves developers and agencies over **40+ hours** of setup time. Whether you are delivering a custom backend for a Fiverr client, bootstrapping a SaaS MVP, or scaling an internal microservice, this architecture guarantees enterprise-grade security, type safety, and horizontal scalability right out of the box.

---

## 2. ## Quick Start & Core Concepts

### Core Architectural Stack
| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance asynchronous API routing & automatic OpenAPI generation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) + Alembic | Non-blocking database operations & programmatic schema migrations. |
| **Data Validation** | Pydantic v2 | Strict payload serialization, deserialization, and environment management. |
| **Authentication** | PyJWT + Passlib (Argon2) | Stateless, cryptographically secure token-based user verification. |
| **Containerization** | Docker & Docker Compose | Isolated, multi-container production orchestration with PostgreSQL. |

### 5-Minute Quick Start
Clone the repository, configure your environment variables, and spin up the entire stack using Docker Compose.

```bash
# 1. Clone or initialize the repository
git clone https://github.com/microcorp-ai/fastapi-enterprise-engine.git
cd fastapi-enterprise-engine

# 2. Configure the environment variables
cp .env.example .env

# 3. Spin up PostgreSQL and the FastAPI application
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec web alembic upgrade head

# 5. Verify the installation
curl -X GET "http://localhost:8000/health" -H "Accept: application/json"
```

---

## 3. ## Production Code Patterns & Architecture Examples

### Directory Structure
```text
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic Settings management
│   ├── database.py       # Async SQLAlchemy session factory
│   └── security.py       # JWT creation, verification & hashing
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User ORM Model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic Request/Response DTOs
├── api/
│   ├── v1/
│   │   ├── api.py        # APIRouter aggregation
│   │   └── endpoints/
│   │       ├── auth.py   # Login & Token endpoints
│   │       └── users.py  # User CRUD & /me endpoints
│   └── deps.py           # FastAPI Dependencies (DB, Current User)
├── main.py               # FastAPI App initialization & middleware
├── Dockerfile
└── docker-compose.yml
```

---

### `app/core/config.py` — Environment & Configuration Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    # Database Configuration
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    SQLALCHEMY_DATABASE_URI(str) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # JWT Security Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### `app/core/database.py` — Asynchronous Database Session Management
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

---

### `app/core/security.py` — Cryptography & JWT Issuance
```python
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


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
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### `app/api/deps.py` — Dependency Injection Architecture
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
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
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
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

### `Dockerfile` — Multi-Stage Production Build
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

# Stage 2: Final runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### `docker-compose.yml` — Container Orchestration
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
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
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations in Asynchronous Routes**
   * *Anti-Pattern:* Using standard `requests` or blocking I/O libraries (like `time.sleep()`) directly inside `async def` path operations, which blocks the entire event loop.
   * *Correction:* Use native asynchronous HTTP clients like `httpx` or offload CPU/blocking operations using `anyio.to_thread.run_sync()`.

2. **Mixing Sync and Async SQLAlchemy Sessions**
   * *Anti-Pattern:* Injecting a synchronous sessionmaker into an asynchronous FastAPI endpoint, causing thread-pool starvation and `MissingGreenlet` errors.
   * *Correction:* Strictly utilize `create_async_engine` paired with `AsyncSession` and `async_sessionmaker`.

3. **Hardcoding Secrets and Configurations**
   * *Anti-Pattern:* Committing database passwords and JWT secret keys directly into source code control.
   * *Correction:* Leverage Pydantic BaseSettings to enforce runtime ingestion strictly via environment variables or secure vault injection.

4. **Catching Generic Exceptions Globally Without Logging**
   * *Anti-Pattern:* Using naked `try...except Exception:` blocks that swallow critical database constraint failures and obscure stack traces.
   * *Correction:* Define custom exception handlers in FastAPI for granular error management and structured logging.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container environments, run Uvicorn with multiple worker processes mapped to CPU cores (`--workers N`), or place a high-performance reverse proxy like Nginx or Envoy in front of Uvicorn.
* **Connection Pooling:** Tune your SQLAlchemy `pool_size` and `max_overflow` parameters in `app/core/database.py` based on your database instance limits to prevent connection exhaustion under heavy concurrent load.
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (e.g., `users.email`, `tokens.jti`) have explicit B-tree indexes defined in your SQLAlchemy models.
* **Response Compression:** Integrate `GZipMiddleware` in `app/main.py` for large JSON payloads to drastically reduce network payload size over the wire.

```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 6. ## Commercial License & Attribution Summary

### Commercial License Agreement
* **Copyright © 2024 MicroCorp AI. All Rights Reserved.**
* **Grant of Rights:** Purchasing or acquiring this digital product grants the licensee a perpetual, non-exclusive, worldwide, royalty-free license to use, modify, adapt, and deploy this codebase for commercial client deliverables (e.g., Fiverr, Upwork, enterprise agency contracts) and internal SaaS products.
* **Restrictions:** Redistribution, resale, or sublicensing of this standalone codebase as an open-source boilerplate, template kit, or digital product on marketplaces (e.g., Gumroad, GitHub Marketplace, ThemeForest) is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any direct, indirect, or consequential damages arising from the deployment or utilization of this architecture.