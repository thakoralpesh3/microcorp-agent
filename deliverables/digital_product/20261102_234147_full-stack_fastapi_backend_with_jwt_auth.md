# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Solution Specification*

---

## 1. # Product Title & Value Proposition

### Product Title
**FastAPI Production-Grade Microservice Boilerplate: JWT Auth, Async PostgreSQL, & Multi-Stage Docker Setup**

### Value Proposition
Stop wasting 40+ hours configuring boilerplate infrastructure, wiring up password hashing, debugging Pydantic v2 migration issues, and writing custom Dockerfiles for production. This turnkey solution provides an enterprise-ready, asynchronous Python backend architecture designed for scale, security, and developer velocity. 

Whether you are delivering a custom solution to a high-ticket Fiverr client or spinning up your next SaaS MVP, this battle-tested stack gives you a secure REST API, strict typing, automated database migrations, and a containerized deployment pipeline out of the box.

### Target Audience
* **Freelance Engineers & Agencies:** Deliver enterprise-grade FastAPI backends to clients in hours instead of weeks.
* **Startup Founders:** Launch secure, scalable MVPs with production-ready security baselines from day one.
* **Backend Developers:** Master modern asynchronous Python patterns, dependency injection, and secure JWT handling.

---

## 2. ## Quick Start & Core Concepts

### System Architecture Overview
```
[Client / Frontend] 
       │
       ▼ (HTTPS / Bearer Token)
[Nginx Reverse Proxy] (Optional SSL Termination)
       │
       ▼
[FastAPI Application Container (Uvicorn Workers)]
       ├── /api/v1/auth (OAuth2 Password Bearer / JWT Issuance)
       ├── /api/v1/users (User Lifecycle & RBAC)
       └── /api/v1/items (Protected Business Logic)
       │
       ├──► [SQLAlchemy 2.0 Async Session] ──► [PostgreSQL 15 Container]
       └──► [Redis Container] (Optional Crate/Rate Limiting)
```

### Clean Syntax & Component Reference

| Layer / Component | Technology Stack | Primary Purpose in the Stack |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | High-performance asynchronous API routing, automatic OpenAPI (Swagger) generation. |
| **Data Validation** | Pydantic v2 | Strict payload validation, serialization, and environment configuration management. |
| **ORM & DB Driver** | SQLAlchemy 2.0 + `asyncpg` | Non-blocking database operations, type-safe models, and migration management. |
| **Database Migrations** | Alembic | Version-controlled schema evolutions and rollback management. |
| **Authentication** | `python-jose` + `passlib` (bcrypt) | Stateless JSON Web Tokens (JWT) and secure password hashing. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds, rootless execution, and local orchestration. |

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
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
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### 1. Configuration Management (`app/core/config.py`)
Uses Pydantic v2 `BaseSettings` to ingest environment variables safely with strict type validation.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Production Service"
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
    SQLALCHEMY_DATABASE_URI: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### 2. Async Database Engine & Session (`app/core/database.py`)
Configures SQLAlchemy 2.0 with an asynchronous engine and session maker factory.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
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

### 3. Security Utilities (`app/core/security.py`)
Handles cryptographic password hashing and JSON Web Token (JWT) encoding/decoding.

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


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### 4. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

---

### 5. Authentication Dependencies (`app/api/deps.py`)
Extracts and validates JWT bearer tokens, fetching the active user context safely.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
    return user
```

---

### 6. Authentication Router (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()


@router.post("/login", response_model=Token)
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 7. FastAPI Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 8. Production Dockerfile (Multi-Stage Build)
```dockerfile
# Stage 1: Build Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production Runtime
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### 9. Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fastapi_app
    restart: always
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=FastAPI Service
      - SECRET_KEY=supersecretjwtkeychangeinproduction
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=production_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async Code in Database Operations**
   * *Anti-Pattern:* Using synchronous SQLAlchemy session classes (`Session`) inside an `async def` FastAPI path operation without wrapping them in `run_in_threadpool`.
   * *The Fix:* Always use `AsyncSession` alongside an async engine driver (`asyncpg`) and fully asynchronous query declarations.
2. **Hardcoding Secrets and Configurations**
   * *Anti-Pattern:* Placing database credentials, JWT secret keys, and API keys directly inside application code files.
   * *The Fix:* Always utilize Pydantic `BaseSettings` reading exclusively from an isolated `.env` file or environment container variables.
3. **Failing to Handle Database Connection Pool Exhaustion**
   * *Anti-Pattern:* Opening manual database connections within loops or failing to close session scopes properly.
   * *The Fix:* Use FastAPI's dependency injection generator (`yield`) pattern with `get_db` to guarantee automatic session closure upon request completion.
4. **Ignoring Container Security Contexts**
   * *Anti-Pattern:* Running the FastAPI application container as the root user in production environments.
   * *The Fix:* Create a dedicated non-privileged system user within your Dockerfile to restrict potential container escalation vulnerabilities.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Always configure multiple worker processes via Uvicorn (`--workers N`) based on available CPU cores (`CPU count * 2 + 1`) to maximize asynchronous concurrency throughput behind a reverse proxy like Nginx or Traefik.
* **Connection Pooling:** Tune SQLAlchemy pool size (`pool_size`, `max_overflow`, `pool_pre_ping`) matching your PostgreSQL instance maximum connection limit to avoid starvation under high concurrent traffic loads.
* **Pydantic Model Serialization:** For high-throughput endpoints returning large lists of database entities, utilize Pydantic's `model_validate(obj, from_attributes=True)` combined with `.scalars().all()` to avoid unnecessary object serialization bottlenecks.
* **Database Indexing:** Ensure all foreign keys (`user_id`), search parameters, and unique constraints (`email`) feature proper B-tree indices at the database schema level.

---

## 6. ## Commercial License & Attribution Summary

### Commercial License Agreement
* **Grant of Rights:** MicroCorp AI grants the purchaser a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this codebase for commercial client deliverables, internal company MVPs, and proprietary SaaS platforms.
* **Restrictions:** Reselling, sublicensing, or distributing this boilerplate codebase as a standalone template, starter kit, or competing digital product is strictly prohibited.
* **Disclaimer:** Provided "AS IS" without warranty of any kind, express or implied. The author and MicroCorp AI accept zero liability for direct or indirect damages resulting from the deployment of this software.

---
*Architected with precision by Backend Architect 🏗️ — The Agency Engineering Division for MicroCorp AI.*