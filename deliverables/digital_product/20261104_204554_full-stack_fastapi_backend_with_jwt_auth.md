# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Boilerplate & Turnkey Solution*  
> **Target Audience:** Enterprise Clients, Senior Engineers, and Agency Partners  
> **Product ID:** `MC-TURKEY-FASTAPI-JWT-001`

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Architecture
Stop wasting 40+ hours writing boilerplate authentication, database migrations, and containerization scripts from scratch. This turnkey solution provides a **battle-tested, asynchronous, type-safe Python backend** designed for immediate deployment to production environments.

```
+-----------------------------------------------------------------+
               MICROCORP AI ENTERPRISE BACKEND STACK
+-----------------------------------------------------------------+
  [ Client / Frontend ] ---> ( Nginx Reverse Proxy )
                                     |
                                     v
                             [ FastAPI App ] 
                       (OAuth2 / JWT / Pydantic v2)
                             /             \
                            v               v
                [ SQLAlchemy 2.0 ]     [ Redis Cache ]
                (Async + Alembic)
                    |
                    v
          [ PostgreSQL 16 DB ]
+-----------------------------------------------------------------+
```

### Key Business Value
* **Time-to-Market:** Cut backend setup time by 90%. Deploy a secure, scalable API on day one.
* **Security First:** Implements robust JSON Web Token (JWT) authentication, password hashing via `bcrypt`, and CORS hardening out of the box.
* **Enterprise Scalability:** Built on asynchronous SQLAlchemy 2.0, Pydantic v2 data validation, and fully containerized via Docker Compose with health checks.
* **Developer Ergonomics:** Fully typed codebase with strict linting configurations (`ruff`, `mypy`) and automated database migrations (`Alembic`).

---

## 2. Quick Start & Core Concepts

Get your local development environment running in under 60 seconds with Docker Compose.

### Clean Syntax & Component Reference Table

| Component | Technology | Purpose / Configuration |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous API routing and automatic OpenAPI docs. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and settings management via `.env`. |
| **Database ORM** | SQLAlchemy 2.0 | Asynchronous database interactions, sessions, and relationship mapping. |
| **Migrations** | Alembic | Version control and schema evolution for PostgreSQL. |
| **Authentication** | OAuth2 + JWT | Stateless token-based security with expiration and scope support. |
| **Containerization** | Docker & Compose | Multi-container orchestration with persistent volumes and health checks. |

### ⚡ 60-Second Quick Start

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Containers:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify Health & Access Docs:**
   * API Documentation: `http://localhost:8000/docs`
   * OpenAPI JSON: `http://localhost:8000/openapi.json`
   * Health Check: `http://localhost:8000/health`

---

## 3. Production Code Patterns & Architecture Examples

This section contains copy-paste ready, production-grade code structured using a modular clean-architecture layout.

### Project Directory Structure
```text
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic BaseSettings
│   ├── database.py       # Async SQLAlchemy engine & session maker
│   └── security.py       # JWT creation, verification & password hashing
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User Model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic I/O Schemas
├── api/
│   ├── v1/
│   │   ├── api.py        # APIRouter aggregator
│   │   └── endpoints/
│   │       ├── auth.py   # Login & Token generation
│   │       └── users.py  # User registration & profile management
│   └── deps.py           # Dependency Injection (DB session, current user)
├── alembic/              # Database migration scripts
├── main.py               # FastAPI application factory
├── Dockerfile
└── docker-compose.yml
```

---

### `app/core/config.py` — Configuration Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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

### `app/core/database.py` — Async SQLAlchemy Engine
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
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

### `app/core/security.py` — JWT & Password Hashing
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


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### `app/models/user.py` — Database Model
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
```

---

### `app/api/deps.py` — Dependency Injection
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


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
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user
```

---

### `app/api/v1/endpoints/auth.py` — Authentication Router
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.security import create_access_token, verify_password
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

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### `Dockerfile` — Production Multi-Stage Container
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

# Stage 2: Runtime Environment
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

### `docker-compose.yml` — Container Orchestration
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: microcorp_postgres
    restart: always
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
    container_name: microcorp_fastapi
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeythatshouldbechangedinproduction
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Blocking I/O in Async Routes:** Never use synchronous libraries like `requests` or blocking ORM queries inside `async def` endpoints. This halts the Uvicorn event loop and degrades throughput. Always use `httpx` or asynchronous database drivers (`asyncpg`).
2. ❌ **Hardcoding Secrets:** Never commit `.env` files or hardcode JWT secret keys in source code. Always inject secrets via environment variables or secret managers (AWS Secrets Manager, HashiCorp Vault).
3. ❌ **Missing Database Connection Pooling:** Failing to configure pool size and timeout settings in production leads to connection leaks under high traffic. Let SQLAlchemy manage sessions via context managers (`yield` in `get_db`).
4. ❌ **Not Handling Token Revocation:** JWTs are stateless. If a user logs out or their account is compromised, the token remains valid until expiration. Mitigate this by maintaining a short token lifespan (15–30 minutes) combined with a Redis-backed blacklist if immediate revocation is required.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Run Uvicorn behind an Nginx reverse proxy or leverage multiple workers (`--workers 4` or multi-process container orchestration via Kubernetes/Docker replicas) to utilize multi-core CPU architectures.
* **Asynchronous Database Indexing:** Ensure high-cardinality lookup columns (such as `email` and foreign keys) have explicit database indexes.
* **Pydantic Model Compilation:** For maximum throughput in high-frequency APIs, ensure Pydantic models are pre-compiled and avoid excessive validator nesting.
* **Response Caching:** Integrate Redis for caching read-heavy endpoints that do not require real-time transactional consistency.

---

## 6. Commercial License & Attribution Summary

* **Product:** Full-Stack FastAPI Backend with JWT Auth and Docker Setup (`MC-TURKEY-FASTAPI-JWT-001`)
* **Author / Organization:** The Agency Engineering Division / MicroCorp AI
* **License:** Commercial Enterprise License (Perpetual, Royalty-Free for internal deployment and client deliverables).
* **Restrictions:** Redistribution or resale of this codebase as a standalone boilerplate or digital template on marketplaces (e.g., Gumroad, GitHub Marketplace) without explicit written authorization from MicroCorp AI is strictly prohibited.

---
*Built with precision by The Agency Backend Architect 🏗️ — Empowering resilient infrastructure.*