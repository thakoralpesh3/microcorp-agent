# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Client Delivery Specification*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend: Enterprise JWT Architecture & Dockerized Boilerplate
Engineered for scale, security, and immediate client handoff. This turnkey solution eliminates 80+ hours of boilerplate setup by providing a battle-tested, asynchronous FastAPI backend featuring enterprise-grade JSON Web Token (JWT) authentication, PostgreSQL integration via SQLAlchemy 2.0 (async), Alembic database migrations, and a fully optimized multi-stage Docker deployment pipeline.

```
+--------------------------------------------------------------------------+
                 MICROCORP AI ENTERPRISE BACKEND ARCHITECTURE               
+--------------------------------------------------------------------------+
  [ Client / SPA ] ---> ( HTTPS / REST ) ---> [ Nginx Reverse Proxy ]
                                                      |
                                             [ FastAPI (Async Uvicorn) ]
                                             ├── JWT Security Middleware
                                             ├── Pydantic v2 Validation
                                             └── SQLAlchemy 2.0 Async ORM
                                                      |
                                             [ PostgreSQL Database ]
+--------------------------------------------------------------------------+
```

### Key Business Metrics & Technical Highlights
* **Zero Technical Debt:** Built strictly on modern Python async primitives (`async/await`) and Pydantic v2 for maximum I/O throughput.
* **Security First:** Implements stateless JWT authentication with dual token strategy (Access + Refresh tokens), password hashing via `bcrypt`, and CORS hardening.
* **Developer Experience:** Complete hot-reload local development setup via Docker Compose, coupled with automated testing via `pytest`.
* **Client Handover Ready:** Fully documented OpenAPI (Swagger/Redoc) generation out of the box with zero additional configuration required.

---

## 2. Quick Start & Core Concepts

### Core Technical Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous REST API framework |
| **Validation** | Pydantic | `2.6+` | Data parsing, validation, and settings management |
| **Database Driver** | asyncpg | `0.29+` | Blazing-fast asynchronous PostgreSQL driver |
| **ORM** | SQLAlchemy | `2.0+` | Enterprise Python ORM with native async support |
| **Migrations** | Alembic | `1.13+` | Database schema migration version control |
| **Auth** | python-jose / passlib | `Latest` | JWT encoding/decoding and secure password hashing |
| **Containerization**| Docker & Compose | `Latest` | Multi-stage isolated deployment environments |

### 5-Minute Local Deployment

Clone the repository and run the automated container stack:

```bash
# 1. Clone and enter directory
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boiler.git
cd fastapi-jwt-docker-boiler

# 2. Configure environment variables
cp .env.example .env
# Edit .env and set secure production keys if desired

# 3. Spin up infrastructure (PostgreSQL + FastAPI)
docker compose up --build -d

# 4. Run database migrations inside container
docker compose exec api alembic upgrade head

# 5. Verify health check
curl http://localhost:8000/health
```

* **API Documentation:** `http://localhost:8000/docs`
* **Alternative Docs (Redoc):** `http://localhost:8000/redoc`

---

## 3. Production Code Patterns & Architecture Examples

### Directory Structure
```text
app/
├── alembic/              # Database migration scripts
├── core/
│   ├── config.py         # Pydantic BaseSettings environment parsing
│   ├── database.py       # Async SQLAlchemy sessionmaker & base model
│   └── security.py       # JWT creation, verification & password hashing
├── models/
│   └── user.py           # SQLAlchemy User ORM Model
├── schemas/
│   └── user.py           # Pydantic Request/Response validation schemas
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py   # Login, Token Refresh & Registration
│   │   │   └── users.py  # Protected User Endpoints
│   │   └── router.py     # API Router aggregation
│   └── deps.py           # FastAPI Dependency Injection (Current User)
├── main.py               # FastAPI application entrypoint
Dockerfile                # Production multi-stage build file
docker-compose.yml        # Local orchestration manifest
requirements.txt          # Pinned dependency manifest
```

---

### `app/core/config.py` — Enterprise Settings Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp AI Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
```

---

### `app/core/database.py` — Async SQLAlchemy Engine & Session Setup
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
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
    """Dependency for obtaining an async database session per request."""
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

### `app/core/security.py` — Cryptography, Hashing & JWT Handling
```python
from datetime import datetime, timedelta, timezone
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
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

### `app/api/deps.py` — Authentication Dependency Injection
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

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise credentials_exception
            
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### `Dockerfile` — Production Multi-Stage Build
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
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### `docker-compose.yml` — Local Orchestration Configuration
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
    container_name: fastapi_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - SECRET_KEY=super-secret-production-key-change-me-immediately
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Blocking I/O inside Asynchronous Endpoints
* **Anti-Pattern:** Using synchronous database drivers (`psycopg2`), blocking HTTP clients (`requests`), or CPU-heavy sync libraries (`time.sleep`) directly inside `async def` routes. This completely blocks the Uvicorn event loop and tanks concurrent throughput.
* **Production Fix:** Always use async-native drivers (`asyncpg`, `httpx`), or offload CPU-bound blocking tasks to a threadpool via `starlette.concurrency.run_in_threadpool`.

### ❌ 2. Catching Generic Exceptions (`except Exception:`)
* **Anti-Pattern:** Swallowing database or runtime errors indiscriminately, masking bugs, and returning ambiguous `500 Internal Server Error` responses to clients.
* **Production Fix:** Catch specific SQLAlchemy or Pydantic exceptions, log the stack trace with contextual telemetry, and return structured, standardized RFC 7807 error payloads.

### ❌ 3. Storing Plaintext or Weakly Hashed Passwords
* **Anti-Pattern:** Using MD5, SHA-256, or unsalted hashing for user credential storage.
* **Production Fix:** Always use `passlib` with the `bcrypt` hashing algorithm, which automatically handles cryptographic salting and work-factor calibration.

### ❌ 4. Hardcoding Sensitive Credentials in Code
* **Anti-Pattern:** Committing database connection strings, JWT secret keys, and third-party API tokens directly into version control.
* **Production Fix:** Enforce strict adherence to environmental separation via Pydantic `BaseSettings` reading from environment variables or secure secret managers (AWS Secrets Manager, HashiCorp Vault).

---

## 5. Performance & Optimization Tips

* **Uvicorn Multi-Worker Scaling:** Never run a single Uvicorn instance in production. Use `--workers N` (where `N = (2 * CPU cores) + 1`) or orchestrate behind an Nginx reverse proxy / Kubernetes deployment cluster.
* **Connection Pooling Tuning:** Fine-tune SQLAlchemy pool parameters (`pool_size`, `max_overflow`, `pool_timeout`) to prevent connection starvation under heavy concurrent traffic spikes.
* **Database Indexing:** Ensure all foreign keys, unique constraints, and high-cardinality search columns in PostgreSQL have appropriate `B-tree` or `GIN` indexes applied via Alembic migrations.
* **Response Serialization Streaming:** For endpoints returning large datasets, utilize Pydantic model serialization generators or stream JSON responses to minimize memory footprints.

---

## 6. Commercial License & Attribution Summary

```text
+--------------------------------------------------------------------------+
                    COMMERCIAL CLIENT DISTRIBUTION LICENSE                 
+--------------------------------------------------------------------------+
  Copyright (c) 2026 MicroCorp AI. All Rights Reserved.                    
                                                                           
  Licensed under the MicroCorp Commercial Engineer License (MCEL-v1.2).    
  You are granted a perpetual, non-exclusive, worldwide license to use,    
  modify, and distribute this codebase in commercial client deliverables   
  (e.g., Fiverr, Upwork, Enterprise Contracting).                          
                                                                           
  RESTRICTION: Reselling this exact source code package as a standalone    
  commercial digital product on marketplaces is strictly prohibited.       
+--------------------------------------------------------------------------+
```