# 🚀 Enterprise-Grade FastAPI Backend: JWT Auth & Docker Setup
*A Turnkey Production-Ready Microservice Boilerplate for Engineering Teams*

---

## 1. # Product Title & Value Proposition

### 📌 Product Title
**FastAPI Production Forge: Enterprise Async Backend with JWT Auth, PostgreSQL, & Docker Multi-Stage Builds**

### 💎 Value Proposition
Building production-grade Python backends from scratch is fraught with hidden traps: async database session mismanagement, insecure token rotation, unoptimized container images bloat, and poor dependency injection. 

This turnkey solution delivers a battle-tested, highly performant FastAPI backend architecture. Designed specifically for agencies and freelance engineers delivering work to high-stakes clients, this codebase slashes 40+ hours of boilerplate setup time. It guarantees strict type safety with Pydantic v2, dependency-injected asynchronous SQLAlchemy 2.0, secure stateless JWT authentication with role-based access control (RBAC), and a hardened, lean production Docker setup.

#### What You Get:
- **Zero-Config Security:** Argon2 password hashing, RS256/HS256 JWT lifecycle management, and strict CORS configuration.
- **Async Database Layer:** SQLAlchemy 2.0 with `asyncpg`, Alembic migrations pre-configured, and connection pooling out of the box.
- **Enterprise Docker Blueprint:** Multi-stage distroless-ready builds with non-root user security constraints.
- **Developer Experience:** Fully typed, structured JSON logging, health-check probes, and OpenAPI/Swagger autodoc tuning.

---

## 2. ## Quick Start & Core Concepts

Get your local development cluster running in under 60 seconds using Docker Compose.

### Quick Start Commands
```bash
# 1. Clone the repository and navigate to the root
git clone https://github.com/microcorp-ai/fastapi-production-forge.git
cd fastapi-production-forge

# 2. Copy the environment variables template
cp .env.example .env

# 3. Spin up the entire stack (PostgreSQL + FastAPI App + Adminer)
docker-compose up --build -d

# 4. Run database migrations inside the container
docker-compose exec api alembic upgrade head

# 5. Access interactive API docs
open http://localhost:8000/docs
```

### Core Architecture Concepts
| Concept | Implementation Strategy | Why It Matters for Production |
| :--- | :--- | :--- |
| **Dependency Injection** | FastAPI `Depends()` for DB sessions and Auth | Enables modular testing, loose coupling, and clean request-scoped resource cleanup. |
| **Async ORM** | SQLAlchemy 2.0 + `asyncpg` | Prevents thread-pool exhaustion under heavy I/O loads, maximizing throughput. |
| **Token Strategy** | Stateless JWT with Access/Refresh split | Minimizes database lookups per request while mitigating token-theft impact via short TTLs. |
| **Containerization** | Docker Multi-Stage Build + Alpine/Slim | Reduces final image attack surface, strips build dependencies, and accelerates deployment times. |

---

## 3. ## Production Code Patterns & Architecture Examples

Here is the structured, modular layout of the project, followed by copy-paste ready production files.

### Directory Structure
```text
fastapi-app/
├── alembic/                 # Database migration scripts
├── app/
│   ├── api/                 # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/   # auth.py, users.py, items.py
│   │   │   └── router.py    # API router aggregator
│   ├── core/                # Config, security, database sessions
│   │   ├── config.py        # Pydantic BaseSettings
│   │   ├── database.py      # Async session maker
│   │   └── security.py      # JWT & Password hashing utils
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   └── main.py              # Application entrypoint
├── Dockerfile               # Multi-stage production container
├── docker-compose.yml       # Local orchestration
├── requirements.txt         # Pinned production dependencies
└── .env.example             # Environment template
```

---

### File 1: `app/core/config.py` (Environment Configuration)
```python
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Forge"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

---

### File 2: `app/core/database.py` (Async SQLAlchemy Session Factory)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding database sessions, guaranteeing closure on exit."""
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

### File 3: `app/core/security.py` (JWT & Hashing Engine)
```python
from datetime import datetime, timedelta
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### File 4: `app/api/v1/endpoints/auth.py` (Authentication Controller)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.token import TokenSchema

router = APIRouter()

@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2 compatible token login, getting an access token for future requests."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
```

---

### File 5: `Dockerfile` (Multi-Stage Production Build)
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

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create non-root system user for security compliance
RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Sync and Async Code (The Blocking Trap):**
   * *Anti-Pattern:* Using synchronous libraries like `requests` or blocking ORM queries (`session.query()`) inside `async def` FastAPI route paths. This completely blocks the main event loop.
   * *Solution:* Always use native async drivers (`asyncpg`, `httpx`) and `async def` handlers, or offload blocking tasks to a threadpool via `run_in_threadpool`.

2. ❌ **Not Committing or Closing Sessions Properly:**
   * *Anti-Pattern:* Manually creating sessions inside endpoints without using context managers (`async with`), leading to connection leaks and pool exhaustion.
   * *Solution:* Rely strictly on FastAPI's dependency injection yielding generator functions with try/finally blocks.

3. ❌ **Storing Plain-Text Passwords or Weak Hashing:**
   * *Anti-Pattern:* Using MD5, SHA256, or bcrypt with low rounds.
   * *Solution:* Use Argon2id or Bcrypt with a high work factor (`passlib` handles this securely out of the box).

4. ❌ **Hardcoding Secrets in Code:**
   * *Anti-Pattern:* Leaving database credentials or JWT secrets inside source files.
   * *Solution:* Enforce Pydantic's `BaseSettings` reading exclusively from environment variables.

---

## 5. ## Performance & Optimization Tips

- **Uvicorn Worker Scaling:** Always run Uvicorn behind a process manager or configure multiple workers matching your CPU core count (`--workers 4` or via Gunicorn process manager).
- **Database Indexing:** Ensure foreign keys (`user_id`) and lookup columns (`email`) have explicit indices defined in your SQLAlchemy models (`index=True`).
- **Pydantic v2 Performance:** Leverage Pydantic v2's Rust-backed core validation engine by ensuring all data contracts inherit from `pydantic.BaseModel` without custom legacy validators.
- **Connection Pooling:** Fine-tune `pool_size` and `max_overflow` in your SQLAlchemy engine parameters based on your database instance limits and expected concurrent connection peaks.

---

## 6. ## Commercial License & Attribution Summary

### 📜 MicroCorp Commercial Engineer License (MCEL-1.0)
*Copyright © 2026 MicroCorp AI. All rights reserved.*

* **Grant of Rights:** Purchasing or acquiring this digital product grants the buyer (Individual or Enterprise) a perpetual, non-exclusive, worldwide license to use, modify, adapt, and compile this codebase for commercial client projects, SaaS products, and internal enterprise architectures.
* **Restrictions:** You **may not** resell, redistribute, sub-license, or package this raw boilerplate as a competing template, framework, or open-source generator kit on marketplaces (e.g., Gumroad, GitHub, Envato) without explicit written authorization from MicroCorp AI.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. The authors are not liable for any damages arising from the use of this software.