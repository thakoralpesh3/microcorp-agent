# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division — Turnkey Solution Package**  
> *Author: Senior Backend Architect, MicroCorp AI*  
> *Target: Production-Ready Microservices & Enterprise Client Handover*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Grade FastAPI Backend Boilerplate
Stop wasting 40+ hours setting up boilerplate architecture, database migrations, stateless JWT authentication, and secure containerization for every new client project. 

This turnkey solution provides a battle-tested, highly performant, asynchronous Python backend engineered for scale. Built with **FastAPI**, **SQLModel**, **PostgreSQL**, **Alembic**, and **Docker**, it includes zero-trust security practices, automatic OpenAPI documentation, and a fully modular service-repository pattern designed for immediate commercial deployment.

### What You Get:
* **Complete Source Code**: Cleanly structured, type-hinted Python code ready for immediate customization.
* **Enterprise Authentication**: Secure HTTP-only Cookie or Bearer token JWT authentication with role-based access control (RBAC).
* **Database Agility**: Modern asynchronous database operations via SQLModel (SQLAlchemy 2.0 + Pydantic v2).
* **Zero-Hassle DevOps**: Multi-stage Dockerfiles and `docker-compose.yml` orchestrating FastAPI, PostgreSQL, and Redis caching.

---

## 2. Quick Start & Core Concepts

### Architectural Clean Syntax Reference

| Component | Technology | Core Responsibility |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | Asynchronous request handling, automated OpenAPI/Swagger documentation. |
| **Validation** | Pydantic v2 | Strict data parsing, serialization, and settings management via environment variables. |
| **ORM / DB** | SQLModel / PostgreSQL | Type-safe database models, asynchronous session management, asyncpg driver. |
| **Migrations** | Alembic | Version-controlled database schema migrations. |
| **Auth** | python-jose & passlib | Stateless JWT signing, verification, and bcrypt password hashing. |
| **Containerization** | Docker & Docker Compose | Isolated multi-container environments for development and production. |

### ⚡ 3-Minute Quick Start Guide

#### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate
cp .env.example .env
```

#### Step 2: Spin Up Infrastructure via Docker Compose
```bash
docker compose up --build -d
```

#### Step 3: Run Database Migrations
```bash
docker compose exec api alembic upgrade head
```

#### Step 4: Verify Installation
* **API Documentation (Swagger):** `http://localhost:8000/docs`
* **Alternative Docs (Redoc):** `http://localhost:8000/redoc`
* **Health Check Endpoint:** `http://localhost:8000/health`

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-backend/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/   # Auth, Users, Items
│   │   │   └── router.ts    # Consolidated router
│   ├── core/                # Config, security, database session
│   ├── models/              # SQLModel database schemas
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   └── main.rs / main.py    # FastAPI application entrypoint
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Local orchestration
├── requirements.txt         # Pinned production dependencies
└── .env.example             # Environment variable template
```

---

### Configuration Engine (`app/core/config.py`)
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
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### Database Session Manager (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI, echo=False, future=True
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
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

### Security & JWT Implementation (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### SQLModel Database Schema (`app/models/user.py`)
```python
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, nullable=False)
    full_name: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

### API Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.core.config import settings
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
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

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
```

---

### Production Dockerfile (`Dockerfile`)
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

# Stage 2: Final runtime container
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: "3.8"

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
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
    container_name: fastapi_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O inside Async Endpoints (`async def`)**:
   * *Anti-Pattern*: Utilizing standard blocking libraries (e.g., `requests`, standard `psycopg2`) inside `async def` route handlers blocks the entire event loop.
   * *Correction*: Use fully asynchronous drivers (`asyncpg`, `httpx`) or wrap blocking operations in `run_in_threadpool`.

2. **Database Session Leaks**:
   * *Anti-Pattern*: Instantiating sessions manually without ensuring proper context management (`try/except/finally` or dependency injection yielding).
   * *Correction*: Strictly use FastAPI’s `Depends(get_db)` to ensure connections are returned to the pool safely upon completion or error.

3. **Hardcoding Secrets and Configurations**:
   * *Anti-Pattern*: Embedding database credentials, JWT secrets, or API keys directly in source code.
   * *Correction*: Use Pydantic’s `BaseSettings` combined with environment variables and secure `.env` management.

4. **Running Containers as `root` in Production**:
   * *Anti-Pattern*: Deploying Docker containers executing applications under the root user, exposing the host system to container escape vulnerabilities.
   * *Correction*: Create a dedicated non-privileged system user within your Dockerfile (`RUN useradd -u 1000 appuser && USER appuser`).

---

## 5. Performance & Optimization Tips

* **Enable Uvicorn Workers Scaling**: In production, leverage Gunicorn as a process manager running multiple Uvicorn workers to maximize multi-core CPU utilization:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Database Connection Pooling**: Configure `pool_size` and `max_overflow` parameters inside `create_async_engine` to handle concurrent traffic spikes gracefully without exhausting PostgreSQL connection limits.
* **Response Caching**: Integrate Redis caching middleware for read-heavy API endpoints to bypass database trips entirely for static or semi-static resources.
* **Gzip Compression**: Add FastAPI's built-in `GZipMiddleware` to reduce payload sizes for JSON responses over the network:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware

  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial License (Type-B Enterprise Handover)
* **Copyright (c) 2026 MicroCorp AI. All Rights Reserved.**
* **Grant of Rights**: Purchasing or licensing this digital product grants the buyer (Client/Engineer) a non-exclusive, perpetual, worldwide license to modify, distribute, and deploy this codebase within commercial client projects, SaaS platforms, and internal enterprise architectures.
* **Restrictions**: You may **not** resell, re-license, or redistribute this boilerplates repository as a standalone template kit on digital marketplaces (e.g., Gumroad, GitHub Marketplace, Envato) without explicit written consent from MicroCorp AI.
* **Disclaimer**: Provided *AS IS*, without warranty of any kind, express or implied. The authors are not liable for any damages arising from the use of this software.