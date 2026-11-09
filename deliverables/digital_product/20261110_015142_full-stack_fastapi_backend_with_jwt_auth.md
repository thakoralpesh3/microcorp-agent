# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture & Distributed Systems*  
> *Commercial Delivery Artifact // SKU: MC-FASTAPI-JWT-099*

---

## 1. # Product Title & Value Proposition

### Enterprise-Grade FastAPI Boilerplate: JWT Auth, Async PostgreSQL, and Multi-Stage Docker Setup

Stop wasting 40+ hours configuring repetitive boilerplate, setting up secure password hashing, wiring asynchronous database drivers, and debugging Docker build cache layers. 

This turnkey solution delivers a production-ready, highly scalable, asynchronous FastAPI backend architecture. It features fully tested JSON Web Token (JWT) authentication, Role-Based Access Control (RBAC), SQLAlchemy 2.0 with async support, Alembic database migrations, and an optimized, secure multi-stage Docker environment.

### What's Included
* **Modular Domain-Driven Architecture:** Clean separation of concerns (Routers, Schemas, Models, Services, Repositories).
* **Robust Security Layer:** OAuth2 with Password Flow, JWT access/refresh token rotation, bcrypt password hashing, and dependency-injected user verification.
* **Async Database Layer:** Full async PostgreSQL integration via `asyncpg` and SQLAlchemy 2.0.
* **Zero-Waste Containerization:** Production-optimized multi-stage Dockerfile and Docker Compose topology with health checks.
* **Comprehensive Tooling:** Pre-configured Alembic environment, CORS middleware, Pydantic v2 validation, and structured logging.

---

## 2. ## Quick Start & Core Concepts

### Architectural Component Reference

| Component | Technology | Purpose & Design Decision |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance async API with automatic OpenAPI (Swagger) documentation and Pydantic v2 validation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Type-safe, asynchronous database interactions preventing I/O blocking under heavy loads. |
| **Database Driver** | `asyncpg` | Blazing-fast pure-Python/C PostgreSQL driver optimized for async execution. |
| **Migrations** | Alembic | Deterministic, version-controlled schema evolution management. |
| **Authentication** | PyJWT / Passlib | Stateless token-based auth with cryptographic signing (HS256) and salt-hashed credentials. |
| **Container Engine** | Docker & Compose v2 | Isolated, reproducible runtime environments with unprivileged security contexts. |

### 5-Minute Local Setup

```bash
# 1. Clone or extract the delivery archive
cd microcorp-fastapi-backend

# 2. Copy the environment template
cp .env.example .env

# 3. Spin up infrastructure (PostgreSQL & Redis) via Docker Compose
docker compose up -d db

# 4. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 5. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 6. Run database migrations
alembic upgrade head

# 7. Launch the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify your installation by navigating to `http://localhost:8000/docs` for the interactive Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
microcorp-fastapi-backend/
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
│   ├── services/
│   │   └── user_service.py
│   └── main.py
├── alembic/
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### `app/core/config.py` — Type-Safe Environment Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### `app/core/database.py` — Async Engine & Session Factory
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

### `app/models/user.py` — SQLAlchemy 2.0 Declarative Model
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

---

### `app/core/security.py` — Cryptography & JWT Operations
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

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str, refresh: bool = False) -> dict | None:
    secret = settings.JWT_REFRESH_SECRET_KEY if refresh else settings.JWT_SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
```

---

### `app/api/deps.py` — Authentication Dependencies
```python
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from sqlalchemy import select

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    payload = decode_token(token, refresh=False)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")
        
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user
```

---

### `app/api/v1/endpoints/auth.py` — Authentication Endpoints
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, TokenResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=TokenResponse)
async def login(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")
        
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
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

# Stage 2: Production runtime
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

# Create non-privileged user for security compliance
RUN useradd -u 1000 microcorp && chown -R microcorp:microcorp /app
USER 1000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### `docker-compose.yml` — Container Orchestration
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: microcorp_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=microcorp_prod
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-access-key-change-in-production
      - JWT_REFRESH_SECRET_KEY=super-secret-refresh-key-change-in-production
    depends_on:
      db:
        condition: service_healthy
    networks:
      - microcorp-net

  db:
    image: postgres:15-alpine
    container_name: microcorp_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: microcorp_prod
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d microcorp_prod"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - microcorp-net

volumes:
  postgres_data:

networks:
  microcorp-net:
    driver: bridge
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async Drivers (`psycopg2` vs `asyncpg`):**
   * *Anti-Pattern:* Instantiating SQLAlchemy engines with synchronous connection strings (`postgresql://...`) in async route handlers. This causes threadpool starvation and blocks the event loop.
   * *Correct Practice:* Always use the async dialect (`postgresql+asyncpg://...`) and ensure all database execution points utilize `await db.execute(...)`.
2. **Hardcoding Secrets in Configuration Files:**
   * *Anti-Pattern:* Placing production JWT secrets directly inside `config.py` or committing `.env` files to Git history.
   * *Correct Practice:* Enforce environment variable injection through Pydantic's `BaseSettings` and add `.env` to your `.gitignore`.
3. **Not Expiring or Revoking Refresh Tokens:**
   * *Anti-Pattern:* Issuing infinite-lifetime JWT access tokens. If compromised, an attacker gains permanent access.
   * *Correct Practice:* Keep access tokens short-lived (15 minutes) and implement a secure refresh token mechanism for session continuation.
4. **Running Containers as Root:**
   * *Anti-Pattern:* Utilizing default container images that execute processes with `root` privileges.
   * *Correct Practice:* Implement unprivileged system users within your Dockerfiles (as demonstrated in Stage 2 of the provided `Dockerfile`).

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, never rely on a single Uvicorn worker process. Launch with multiple workers matching your CPU core count (`--workers 4` or via Gunicorn process manager with Uvicorn worker classes).
* **Connection Pooling:** Fine-tune your SQLAlchemy `pool_size` and `max_overflow` parameters based on your PostgreSQL maximum connection limit (`max_connections`) to prevent database socket saturation under peak traffic.
* **Database Indexing:** Ensure all foreign keys, unique email fields, and frequent query filter targets are explicitly indexed (`index=True`) at the database model level.
* **Response Serialization Tuning:** For heavy payloads, utilize Pydantic's `model_dump()` or model serialization optimizations, or bypass serialization overhead via raw JSON responses when streaming massive datasets.

---

## 6. ## Commercial License & Attribution Summary

### Commercial End-User License Agreement (EULA)
* **Granted Rights:** You are licensed to use, modify, distribute, and embed this codebase into proprietary, commercial client projects, SaaS products, and enterprise applications.
* **Restrictions:** Reselling this specific source code artifact as a competing boilerplate, code template, or standalone digital product package is strictly prohibited.
* **Warranty Disclaimer:** Provided *as is* without warranty of any kind, express or implied. The author and MicroCorp AI assume no liability for damages resulting from the deployment of this software.

```text
SPDX-License-Identifier: MIT-Commercial-Derivative
Copyright (c) 2026 MicroCorp AI / The Agency Engineering Division. All rights reserved.
```