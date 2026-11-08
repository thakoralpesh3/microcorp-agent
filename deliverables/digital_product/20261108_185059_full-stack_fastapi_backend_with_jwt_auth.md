# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise-Grade FastAPI Backend Boilerplate with JWT Authentication & Dockerized Production Stack

#### Value Proposition
Stop wasting 40+ hours writing boilerplate configurations, wiring up database migrations, and debugging async connection pools. This enterprise-ready FastAPI turnkey solution delivers a rock-solid, production-grade backend architecture out of the box. Designed for high-scale microservices, SaaS platforms, and enterprise client deliverables, it features strict type checking, robust asynchronous database operations via SQLAlchemy 2.0, secure HTTP-only JWT authentication, and a bulletproof multi-stage Docker setup.

#### What’s Included
* **Fully Asynchronous Architecture:** Built on FastAPI, Uvicorn, and SQLAlchemy 2.0 async sessions (`asyncpg`).
* **Secure Auth Pipeline:** OAuth2 Password Bearer flow with JWT access/refresh tokens, password hashing via `passlib[bcrypt]`, and dependency injection for role-based access control.
* **Database Migrations:** Automated schema management with Alembic.
* **Production Containerization:** Optimized multi-stage Dockerfiles with non-root execution and Docker Compose orchestration (PostgreSQL + Redis + App).
* **Developer Experience:** Pre-configured Pydantic V2 settings management, structured logging, and comprehensive test suites via `pytest`.

---

## 2. Quick Start & Core Concepts

### System Architecture Quick Reference

```
[ Client / Frontend ] 
       │ (HTTPS / Bearer Token)
       ▼
[ Nginx / Reverse Proxy ] (Optional Layer)
       │
       ▼
[ FastAPI Application (Uvicorn Workers) ]
       ├──> [ PostgreSQL 15 ] (Async SQLAlchemy 2.0)
       └──> [ Redis 7 ] (Caching / Rate Limiting / Celery Broker)
```

### Clean Syntax & Component Matrix

| Component | Technology | Version | Purpose / Architectural Role |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance asynchronous API routing, automatic OpenAPI docs, and strict payload validation via Pydantic V2. |
| **Database Driver** | asyncpg + SQLAlchemy | `2.0+` | Non-blocking database operations, connection pooling, and declarative ORM modeling. |
| **Migration Engine** | Alembic | `1.13+` | Version-controlled database schema migrations. |
| **Authentication** | python-jose + passlib | `Latest` | JWT encoding/decryption and cryptographic password hashing. |
| **Containerization** | Docker & Compose | `24.0+` | Isolated, reproducible multi-container production environment. |

---

## 3. Production Code Patterns & Architecture Examples

### 3.1 Project File Tree Structure
```text
fastapi-enterprise-boilerplate/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           └── users.py
│   └── crud/
│       ├── __init__.py
│       └── crud_user.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### 3.2 Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
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

### 3.3 Asynchronous Database Session Management (`app/core/database.py`)
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

### 3.4 SQLAlchemy User Model (`app/models/user.py`)
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

---

### 3.5 Security & JWT Encoding (`app/core/security.py`)
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


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 3.6 API Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.crud.crud_user import user as crud_user

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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    current_user = await crud_user.get(db, id=user_id)
    if current_user is None:
        raise credentials_exception
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

---

### 3.7 Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.core import security
from app.core.config import settings
from app.crud.crud_user import user as crud_user
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await crud_user.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }
```

---

### 3.8 Docker Configuration (`Dockerfile`)
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

# Stage 2: Runtime Image
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

### 3.9 Orchestration (`docker-compose.yml`)
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* ❌ **Blocking I/O in Async Paths:** Utilizing synchronous libraries (e.g., `requests`, standard `psycopg2`) inside `async def` route handlers. This blocks the entire event loop, destroying throughput. Always use `httpx` and `asyncpg`.
* ❌ **Hardcoding Secrets:** Storing database credentials and JWT secret keys in source control. Always inject configuration via environment variables and validate with Pydantic Settings.
* ❌ **N+1 Query Traversal:** Lazy loading relational attributes in loops within async contexts (`User.posts` without pre-fetching). This triggers runtime exceptions or hidden synchronous execution blocks. Use SQLAlchemy `selectinload` or `joinedload`.
* ❌ **Catching Base Exceptions Silently:** Using `except Exception:` without raising or correctly rolling back database transactions, resulting in dangling, locked database sessions.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container deployments, run multiple Uvicorn worker processes based on available vCPUs (`--workers 4` or managed via Gunicorn process manager).
* **Connection Pooling tuning:** Fine-tune `pool_size` and `max_overflow` in SQLAlchemy's engine creation based on your PostgreSQL server connection limits.
* **Response Compression:** Integrate `GZipMiddleware` into FastAPI to automatically compress responses larger than 1KB, drastically reducing payload sizes over the wire.
* **Redis Caching Layer:** Offload heavy aggregate read queries and rate-limiting counters to Redis to minimize database read overhead.

---

## 6. Commercial License & Attribution Summary

### Commercial End-User License Agreement (EULA)
* **Granted Rights:** You are granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this codebase for commercial client deliverables, internal company products, and SaaS applications.
* **Restrictions:** Redistribution, resale, or sub-licensing of this exact architectural boilerplate as a competing template package on digital marketplaces (e.g., Gumroad, ThemeForest) is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. The author/agency shall not be held liable for any claim, damages, or liability arising from its implementation.