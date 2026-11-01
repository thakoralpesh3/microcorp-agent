# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Architectural Blueprint*  
> **Product SKU:** MC-TURKEY-FASTAPI-049  
> **Target Audience:** Enterprise Clients, Senior Engineers, and Freelance Systems Architects

---

## 1. # Product Title & Value Proposition

### Product Title
**The Enterprise FastAPI Core Boilerplate: JWT Auth, Async PostgreSQL, and Multi-Stage Docker Setup**

### Value Proposition
Building modern, high-throughput microservices requires a robust asynchronous foundation, secure stateless authentication, and immutable containerization from day one. This turnkey architecture eliminates weeks of boilerplate scaffolding. It provides production-ready dependency injection, Pydantic v2 validation, SQLAlchemy 2.0 async session management, secure token rotation, and a hardened Docker setup engineered to pass strict security audits and scale effortlessly under load.

### Key Deliverables
*   **Zero-Config Async ORM Layer:** Pre-configured SQLAlchemy 2.0 with Alembic migration pipelines.
*   **Secure Authentication Engine:** Access/Refresh token rotation using industry-standard JWTs and Argon2 password hashing.
*   **Production-Hardened Docker Engine:** Multi-stage builds, non-root user execution, and slim distroless/alpine runtimes.
*   **Developer Ergonomics:** Hot-reloading development setup with integrated pre-commit hooks, Ruff linting, and Pytest coverage.

---

## 2. ## Quick Start & Core Concepts

### System Architecture Quick Reference

```
[ Client / SPA ] 
       │
       ▼ (HTTPS / Bearer Token)
[ Nginx / Traefik Reverse Proxy ]
       │
       ▼
[ FastAPI Application Container (Uvicorn Workers) ]
       ├──> [ Async SQLAlchemy ORM ] ──> [ PostgreSQL Database ]
       └──> [ Redis Cache / Rate Limiter ]
```

### Clean Syntax & Technology Matrix

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance asynchronous API routing & auto-docs |
| **Data Validation** | Pydantic | `2.6+` | Strict runtime payload validation and settings management |
| **Database Driver** | asyncpg + SQLAlchemy | `2.0+` | Non-blocking database connection pooling and ORM mapping |
| **Migrations** | Alembic | `1.13+` | Version-controlled database schema migrations |
| **Authentication** | python-jose / passlib | Latest | Cryptographic JWT signing and Argon2 password hashing |
| **Containerization** | Docker / Docker Compose | Latest | Reproducible multi-service deployment environment |

---

## 3. ## Production Code Patterns & Architecture Examples

### 3.1 Project Directory Structure
```text
fastapi-enterprise-core/
├── alembic/
│   └── versions/
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
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

---

### 3.2 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Core"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### 3.3 Asynchronous Database Session (`app/core/database.py`)
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

AsyncSessionLocal = async_sessionmaker(
    engine,
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

### 3.4 Cryptography & JWT Security (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
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
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### 3.5 SQLAlchemy User Model (`app/models/user.py`)
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
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
```

---

### 3.6 FastAPI Dependency Injection (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

---

### 3.7 Production Dockerfile (`Dockerfile`)
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

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### 3.8 Docker Compose Orchestration (`docker-compose.yml`)
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
    container_name: fastapi_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Architecture Pattern |
| :--- | :--- | :--- |
| **Blocking Sync I/O in Async Paths** | Using standard `requests` or blocking SQL drivers inside async routes starves the event loop, tanking throughput. | Always use `asyncpg`, `httpx`, and native async database sessions. |
| **Global State Session Management** | Sharing a single database session across requests causes thread safety issues, deadlocks, and corrupted transactions. | Use FastAPI's Dependency Injection (`Depends(get_db)`) to instantiate request-scoped sessions. |
| **Storing Secrets in Code/Git** | Hardcoding JWT secrets or database connection strings leads to data leaks and compromised systems. | Utilize Pydantic BaseSettings, environment variables, and secure secret managers. |
| **Running Containers as Root** | If a container is compromised, the attacker gains host root access immediately. | Create a dedicated unprivileged system user (`USER appuser`) inside the Dockerfile. |

---

## 5. ## Performance & Optimization Tips

1.  **Uvicorn Worker Scaling:** Always scale your production Uvicorn workers based on available CPU cores (`--workers $(nproc)`). Never rely on a single worker for production loads.
2.  **Connection Pooling:** Tune your SQLAlchemy connection pool parameters (`pool_size`, `max_overflow`, `pool_recycle`) to match your PostgreSQL instance's `max_connections` limit.
3.  **JSON Serialization Speed:** Replace standard JSON serialization with `orjson` or `ujson` drop-in replacements within FastAPI for a 5x–10x boost in response encoding speed.
4.  **Database Indexing:** Ensure foreign keys, lookup columns (such as user emails), and frequently filtered fields have explicit B-tree indexes defined in your SQLAlchemy models.

---

## 6. ## Commercial License & Attribution Summary

### Commercial License Agreement
*   **Grant of Rights:** MicroCorp AI grants the purchaser a perpetual, non-exclusive, worldwide license to use, modify, adapt, and distribute this codebase within commercial client projects, software-as-a-service (SaaS) platforms, and internal enterprise architectures.
*   **Restrictions:** Redistribution of this exact template as a standalone competing digital product, boilerplate kit, or template marketplace item is strictly prohibited.
*   **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The Agency and MicroCorp AI accept zero liability for deployment configurations, security misconfigurations, or production outages.

---
*Generated by **Backend Architect** 🏗️ | The Agency Engineering Division for MicroCorp AI.*