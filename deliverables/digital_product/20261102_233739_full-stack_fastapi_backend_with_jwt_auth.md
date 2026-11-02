# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Architectural Blueprint*  
> **Product ID:** `MC-FASTAPI-JWT-DOCKER-001`  
> **Target Audience:** Enterprise Clients, Senior Engineers, High-Performance Startups  

---

## 1. # Product Title & Value Proposition

### Title
**Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, PostgreSQL, SQLAlchemy 2.0 Async, and Multi-Stage Docker Setup**

### Value Proposition
Building modern, high-throughput APIs from scratch is time-consuming and fraught with security pitfalls—especially when configuring async database drivers, stateless JWT authentication, and secure containerization. 

This turnkey solution eliminates boilerplate friction, providing a battle-tested, production-ready architecture designed for horizontal scaling. It implements modern Python paradigms (Type Hints, Pydantic v2, SQLAlchemy 2.0 Async) and strict security standards (Argon2 password hashing, RS256/HS256 JWT validation, CORS isolation) out of the box.

### What You Get
*   **Zero-Config Dev Experience:** Spin up the complete stack (API, DB, Adminer) with a single `docker compose up` command.
*   **Production Security:** Secure HTTP-only cookie JWT flows, role-based access control (RBAC), and environment-driven configuration.
*   **Developer Velocity:** Pre-configured Alembic migrations, structured JSON logging, and comprehensive health check endpoints.

---

## 2. ## Quick Start & Core Concepts

### System Architecture Overview
```
[ Client / Frontend ] 
       │
       ▼ (HTTPS / JSON)
[ Nginx / Reverse Proxy ] (Optional Edge)
       │
       ▼ 
[ FastAPI Application Container ] ◄──► [ Redis Cache / Rate Limiter ]
       │
       ├──► SQLAlchemy 2.0 Async Engine
       │         │
       │         ▼
       └────► [ PostgreSQL 16 Primary DB ]
```

### Clean Syntax & Technology Matrix

| Layer | Technology | Purpose | Production Consideration |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous REST API | Run with Uvicorn workers behind a process manager. |
| **Data Validation** | Pydantic v2 | Strict payload validation & serialization | Utilize `model_validator` for cross-field rules. |
| **ORM & DB** | SQLAlchemy 2.0 (Async) | Non-blocking database interactions | Always use `AsyncSession` with context managers. |
| **Migrations** | Alembic | Database schema version control | Run migrations as an init container in production. |
| **Authentication** | python-jose / passlib | Stateless token generation & verification | Use asymmetric keys (RS256) for microservice architectures. |
| **Containerization** | Docker (Multi-stage) | Lightweight, secure runtime packaging | Run as a non-root user (`appuser`). |

### Quick Start Guide (Local Development)

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Infrastructure:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify API Health:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
   *Expected Response:* `{"status": "healthy", "database": "connected"}`

---

## 3. ## Production Code Patterns & Architecture Examples

### Directory Structure
```text
app/
├── core/
│   ├── config.py         # Pydantic Settings
│   ├── database.py       # Async SQLAlchemy sessionmaker
│   └── security.py       # JWT & Password hashing utils
├── models/
│   └── user.py           # SQLAlchemy declarative models
├── schemas/
│   └── user.py           # Pydantic request/response schemas
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py   # Login / Refresh routes
│   │   │   └── users.py  # User CRUD routes
│   │   └── router.py     # API router aggregation
│   └── deps.py           # FastAPI Dependencies (get_db, get_current_user)
└── main.py               # FastAPI app initialization
```

### 1. Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    SQLALCHEMY_DATABASE_URI: str | None = None
    
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def assemble_db_connection(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

settings = Settings()
if not settings.SQLALCHEMY_DATABASE_URI:
    settings.SQLALCHEMY_DATABASE_URI = settings.assemble_db_connection()
```

### 2. Database Engine & Session (`app/core/database.py`)
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

### 3. Security & JWT Handling (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
```

### 4. FastAPI Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

### 5. Authentication Router (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.user import TokenSchema

router = APIRouter()

@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

### 6. Production Multi-Stage Dockerfile (`Dockerfile`)
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 7. Production Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: secure_password_change_me
      POSTGRES_DB: enterprise_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres_user -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_api
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=secure_password_change_me
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=super_secret_jwt_key_change_in_production
      - JWT_REFRESH_SECRET_KEY=super_secret_refresh_key_change_in_production
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations inside Async Endpoints (`def` vs `async def`)**
   * *The Antipattern:* Using standard blocking libraries (e.g., `requests`, standard `psycopg2`) inside an `async def` FastAPI route, blocking the entire event loop.
   * *The Fix:* Use true async drivers (`asyncpg`, `httpx`) or wrap blocking code in `run_in_threadpool`.
2. **Missing Database Session Context Management**
   * *The Antipattern:* Manually instantiating sessions inside route controllers without proper `try/except/finally` teardowns, leading to connection leaks and pool exhaustion.
   * *The Fix:* Always use FastAPI's dependency injection system (`Depends(get_db)`) to yield and auto-close sessions.
3. **Hardcoding Secrets in Codebase or Dockerfile**
   * *The Antipattern:* Embedding JWT secret keys or DB credentials directly into configuration files or version-controlled environments.
   * *The Fix:* Force runtime injection strictly via `.env` files or secure parameter stores (AWS SSM, HashiCorp Vault).
4. **Ignoring SQLAlchemy Lazy-Loading Traps in Async Environments**
   * *The Antipattern:* Accessing uninitialized relationships (`user.posts`) on an expired async session instance, raising `MissingGreenlet`.
   * *The Fix:* Explicitly use `selectinload` or `joinedload` during your query execution phase.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Always scale your worker pool based on CPU cores. A common formula for production is `(2 * $CPU_CORES) + 1`. Execute via process managers like Gunicorn running Uvicorn workers.
* **Connection Pooling tuning:** Tune `pool_size` and `max_overflow` based on your DB tier and maximum concurrent load to prevent database thread starvation.
* **Response Compression:** Install `starlette.middleware.gzip.GZipMiddleware` to automatically compress large JSON payloads over the network.
* **Database Indexing:** Ensure all foreign keys, unique constraint columns, and high-frequency search fields have targeted B-tree indices configured in Alembic migration scripts.

---

## 6. ## Commercial License & Attribution Summary

### End-User Commercial License Agreement
* **Copyright © 2024 MicroCorp AI. All Rights Reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, and deploy this codebase for commercial and internal business applications, including delivery to end-client projects (e.g., Fiverr, Upwork, enterprise deployments).
* **Restrictions:** Redistribution, resale, or sub-licensing of this exact architectural boilerplate as an independent commercial product template is strictly prohibited.
* **Disclaimer:** Provided "AS IS" without warranty of any kind, express or implied. The author/agency shall not be held liable for any claims, damages, or liabilities arising from its deployment in production environments.