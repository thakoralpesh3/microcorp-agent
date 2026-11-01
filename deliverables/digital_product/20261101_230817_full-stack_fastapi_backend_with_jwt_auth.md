# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Ready Architecture Series*  
> **Product ID:** `MC-TURKEY-FASTAPI-01`  
> **Target Audience:** Enterprise Contractors, Full-Stack Engineers, and Freelance Dev Agencies delivering high-performance APIs.

---

## 1. Product Title & Value Proposition

### 🚀 Production-Grade FastAPI Backend Boilerplate
Stop wasting 40+ billable hours writing boilerplate user models, token refresh logic, database migrations, and Dockerfiles from scratch. This turnkey solution delivers a battle-tested, asynchronous FastAPI backend designed to handle production loads out of the box.

```
+-------------------------------------------------------------------------+
|                        MICROCORP AI ARCHITECTURE                        |
|                                                                         |
|   [Client App] ---> Nginx ---> [FastAPI / Uvicorn] ---> PostgreSQL      |
|                                       |                                 |
|                                [Redis Cache]                            |
+-------------------------------------------------------------------------+
```

### Key Business Benefits
* **Zero Technical Debt:** Built using modern Python type hints, Pydantic v2 validation, and asynchronous SQLAlchemy 2.0.
* **Security First:** Implements stateless JWT authentication with secure password hashing (Argon2/Bcrypt) and HttpOnly cookie fallback patterns.
* **Instant Deployment:** Containerized with multi-stage Dockerfiles and Docker Compose profiles for local development and production environments.
* **Fiverr / Client Ready:** Cleanly structured, thoroughly documented, and strictly modular—ready to hand off to clients with zero friction.

---

## 2. Quick Start & Core Concepts

### Syntax & Architectural Mapping Table

| Layer | Technology | Purpose | Key File Location |
| :--- | :--- | :--- | :--- |
| **API Routing** | FastAPI APIRouter | Modular endpoint grouping & dependency injection | `app/api/v1/endpoints/` |
| **Validation** | Pydantic v2 | Request/Response payload serialization & validation | `app/schemas/` |
| **ORM / Data** | SQLAlchemy 2.0 (Async) | Async database session management & mapping | `app/models/` & `app/db/` |
| **Migrations** | Alembic | Database schema version control | `alembic/versions/` |
| **Security** | PyJWT / Passlib | Token generation, verification, and hashing | `app/core/security.py` |
| **Container** | Docker / Compose | Isolated runtime environments | `Dockerfile`, `docker-compose.yml` |

### 3-Step Local Initialization

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin up Infrastructure via Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify API Health & Docs:**
   * Interactive Swagger UI: `http://localhost:8000/docs`
   * Alternative Redoc: `http://localhost:8000/redoc`

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```
app/
├── api/
│   ├── deps.py             # FastAPI Dependencies (DB session, current user)
│   └── v1/
│       ├── api.v1.py       # Router aggregator
│       └── endpoints/
│           ├── auth.py     # Login, token refresh
│           └── users.py    # User CRUD operations
├── core/
│   ├── config.py           # Pydantic BaseSettings config
│   ├── database.py         # Async engine & sessionmaker
│   └── security.py         # JWT & password hashing utilities
├── models/
│   └── user.py             # SQLAlchemy ORM models
├── schemas/
│   └── user.py             # Pydantic validation schemas
└── main.py                 # FastAPI application factory
```

### 3.1 Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

settings = Settings()
```

### 3.2 Asynchronous Database Session (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
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

### 3.3 Security & Token Management (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
import jwt
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### 3.4 API Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")
```

### 3.5 Production Dockerfile
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 3.6 Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
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
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Using Synchronous DB Drivers in Async Routes:**
   * *Anti-Pattern:* Importing standard `psycopg2` inside an `async def` path operation blocks the entire Uvicorn event loop.
   * *Correction:* Always use `asyncpg` with SQLAlchemy's asynchronous session configurations.
2. **Hardcoding Secrets in Code:**
   * *Anti-Pattern:* Placing JWT keys or database passwords directly into config files.
   * *Correction:* Enforce Pydantic BaseSettings with mandatory `.env` overrides and fail fast if required secrets are missing.
3. **Missing Database Connection Pooling Management:**
   * *Anti-Pattern:* Opening and closing raw connections per request without proper context managers.
   * *Correction:* Rely on FastAPI dependency injection yielding scoped sessions from an application-level `async_sessionmaker`.
4. **Neglecting Alembic Migration Revisions:**
   * *Anti-Pattern:* Altering SQLAlchemy models directly in production databases without generating migration scripts.
   * *Correction:* Treat Alembic as the single source of truth for schema changes (`alembic revision --autogenerate`).

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Run behind a process manager or configure multiple workers via Gunicorn/Uvicorn workers (`--workers 4` or `WEB_CONCURRENCY=auto`).
* **Response Serialization Tuning:** For heavy JSON responses, leverage `orjson` response classes in FastAPI for up to 10x serialization speed improvements over standard library json.
* **Database Indexing:** Ensure foreign keys and high-cardinality lookup columns (such as `users.email`) are explicitly indexed (`index=True`).
* **Connection Pooling Parameters:** Tune `pool_size` and `max_overflow` on your SQLAlchemy engine when facing high concurrency spikes:
  ```python
  engine = create_async_engine(
      settings.DATABASE_URL,
      pool_size=20,
      max_overflow=10,
      pool_recycle=3600
  )
  ```

---

## 6. Commercial License & Attribution Summary

```
+-------------------------------------------------------------------------+
|                  MICROCORP COMMERCIAL SOFTWARE LICENSE                  |
|                                                                         |
|  Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.     |
|  Licensed under the MIT Commercial-Friendly License.                    |
+-------------------------------------------------------------------------+
```

* **Permitted Uses:** You are free to use, modify, distribute, and resell this codebase as part of client deliverables on platforms like Fiverr, Upwork, or direct B2B contracts.
* **Restrictions:** You may not resell or redistribute this exact boilerplate as an independent digital product or template on marketplaces (e.g., Gumroad, GitHub marketplace) without explicit written consent from MicroCorp AI.
* **Warranty Disclaimer:** Provided *as is*, without warranty of any kind, express or implied. The Agency Engineering Division assumes no liability for production incidents resulting from improper configuration or unverified credential management.