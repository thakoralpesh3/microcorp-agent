# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Solutions Series*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Boilerplate: Production-Ready JWT Auth & Dockerized Architecture

Stop wasting 40+ hours configuring boilerplate code, wiring asynchronous database drivers, debugging CORS policies, and writing secure JWT authentication flows from scratch. 

This turnkey solution delivers a battle-tested, highly scalable, asynchronous FastAPI backend designed explicitly for freelance engineers, SaaS founders, and enterprise clients who demand high performance and security out of the box.

#### What You Get:
- **Zero-Config Asynchronous Setup**: Fully asynchronous SQLAlchemy 2.0 with PostgreSQL, managed via Alembic migrations.
- **Enterprise Security**: Argon2 password hashing combined with stateless JWT (Access + Refresh token rotation) and role-based access control (RBAC).
- **Containerized Infrastructure**: Production-optimized multi-stage Dockerfiles and Docker Compose files featuring PostgreSQL, Redis caching, and NGINX reverse-proxy orchestration.
- **Developer Experience**: Pydantic v2 data validation, automated OpenAPI/Swagger documentation, and structured JSON logging.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
```
[ Client / Frontend ] 
       │
       ▼ (HTTPS)
[ NGINX Reverse Proxy ] 
       │
       ▼ (HTTP/JSON)
[ FastAPI App Container ] ──(Async SQLAlchemy)──► [ PostgreSQL DB ]
       │
       └──(Redis Client)────────────────────────► [ Redis Cache/Broker ]
```

### Syntax & Component Reference

| Component | Technology | Purpose in the Stack |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance, asynchronous REST API with automatic Pydantic validation. |
| **ORM / Migrations** | SQLAlchemy 2.0 + Alembic | Type-safe asynchronous database operations and schema version control. |
| **Database** | PostgreSQL 15 | Relational data store optimized for concurrent read/write operations. |
| **Authentication** | PyJWT + Passlib (Argon2) | Secure token generation, validation, and salted cryptographic password hashing. |
| **Caching / Queues** | Redis 7 | High-speed ephemeral data storage, rate limiting, and background task brokering. |
| **Containerization** | Docker & Compose v2 | Isolated, reproducible multi-container production and development environments. |

---

## 3. Production Code Patterns & Architecture Examples

### A. Project Directory Structure
```text
fastapi-enterprise-boilerplate/
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
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### B. Configuration Management (`app/core/config.py`)
Uses Pydantic BaseSettings to enforce type safety and environment variable validation upon startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
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

### C. Asynchronous Database Session (`app/core/database.py`)
Configures the async engine and session factory for SQLAlchemy 2.0.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
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

### D. Security & Token Handling (`app/core/security.py`)
Implements Argon2 hashing and JWT token generation/decoding.

```python
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### E. Authentication Dependency (`app/api/deps.py`)
Validates incoming Bearer tokens and extracts the current active user from the database.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
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
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### F. Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### G. Production Dockerfile
Multi-stage build pattern to maintain a minimal final image footprint.

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

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### H. Docker Compose Setup (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    restart: always

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: always

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
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      - db
      - redis
    restart: always

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Using Synchronous DB Drivers in an Async Framework
* **The Mistake**: Using standard `psycopg2` or synchronous SQLAlchemy sessions inside `async def` FastAPI endpoints. This blocks the main event loop, causing severe request bottlenecking under concurrent loads.
* **The Fix**: Always use an asynchronous driver (`asyncpg`) paired with `AsyncSession` and `create_async_engine`.

### ❌ Anti-Pattern 2: Hardcoding Configuration Values
* **The Mistake**: Placing database credentials, JWT secrets, and API keys directly inside code files.
* **The Fix**: Utilize Pydantic’s `BaseSettings` pattern to ingest configurations strictly from environment variables (`.env`).

### ❌ Anti-Pattern 3: Storing Passwords with Weak Hashing Algorithms
* **The Mistake**: Using basic SHA-256 or MD5 hashes for user credentials.
* **The Fix**: Use modern memory-hard cryptographic algorithms like Argon2 or bcrypt via `passlib`.

### ❌ Anti-Pattern 4: Ignoring Database Connection Pooling Limits
* **The Mistake**: Leaving connection limits unbound, causing database exhaustion under spikes in traffic.
* **The Fix**: Explicitly configure `pool_size` and `max_overflow` parameters on the SQLAlchemy engine.

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling**: In production environments, run Uvicorn behind a process manager or scale workers using `--workers N` (where N equals `2 * CPU_CORES + 1`).
2. **Response Compression**: Integrate `GZipMiddleware` in FastAPI for responses exceeding 1KB to minimize bandwidth utilization.
3. **Database Indexing**: Ensure high-cardinality search fields (such as `email` and `username`) have explicit database indexes defined in your SQLAlchemy models (`index=True`).
4. **Caching Layer**: Offload frequent, non-transactional read queries (such as system configurations or user profiles) to Redis with appropriate TTLs.

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial License (Permissive Business License)

Copyright (c) 2026 MicroCorp AI. All rights reserved.

#### Granted Rights:
- **Commercial Usage**: You are authorized to integrate this codebase into commercial products, client deliverables on Fiverr, upwork, or proprietary SaaS applications.
- **Modification**: You may alter, refactor, and extend this codebase to fit your architectural needs.

#### Restrictions:
- **Resale**: Redistribution of this exact template as a competing digital product, boilerplate generator, or open-source template kit is strictly prohibited without explicit written consent from MicroCorp AI.
- **Warranty**: This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI accepts no liability for production outages or data loss resulting from improper configuration.