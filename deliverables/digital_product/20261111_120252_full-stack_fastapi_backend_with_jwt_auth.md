# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
**MicroCorp AI Engineering Division — Product ID: MC-FAS-004**

## 1. Product Title & Value Proposition

### Title
**Enterprise-Grade FastAPI Backend Boilerplate with Async SQLAlchemy, JWT Authentication, and Production-Ready Docker Orchestration.**

### Value Proposition
Stop wasting 40+ hours writing boilerplate auth, database connection pooling, and container configurations for every new client project. This turnkey backend architecture is engineered for absolute performance, strict type-safety via Pydantic v2, and seamless horizontal scaling. Built for senior engineers and agencies delivering mission-critical microservices and SaaS backends.

### What's Included
* **Asynchronous Database Layer:** Powered by SQLAlchemy 2.0+ and asyncpg for non-blocking I/O.
* **Stateless JWT Security:** Access & Refresh token rotation with bcrypt password hashing.
* **Production-Ready Docker Setup:** Multi-stage builds, non-root user execution, and health checks.
* **Migrations Management:** Automated Alembic migration pipeline integrated into container startup.
* **Strict Type Safety:** End-to-end Python type hinting enforced by Pydantic v2 and MyPy.

---

## 2. Quick Start & Core Concepts

### System Architecture Diagram
```
[Client / Frontend] 
       │
       ▼ (HTTPS / JSON)
[Nginx / Reverse Proxy] (Optional)
       │
       ▼
[FastAPI App (Uvicorn Workers)]
       ├── /api/v1/auth (JWT Issuance & Verification)
       ├── /api/v1/users (User Management & RBAC)
       └── /api/v1/health (Container Health Probes)
       │
       ├──► [PostgreSQL 16 (AsyncPG Connection Pool)]
       └──► [Redis (Optional: Rate Limiting & Celery Broker)]
```

### Clean Syntax & Configuration Table

| Component | Technology | Version | Purpose / Constraint |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async routing and auto-docs. |
| **Data Validation** | Pydantic | `2.6+` | Runtime data parsing and serialization. |
| **ORM / Database** | SQLAlchemy | `2.0+` | Asynchronous ORM with strict typing. |
| **Database Driver** | asyncpg | `0.29+` | High-performance async PostgreSQL driver. |
| **Migrations** | Alembic | `1.13+` | Version-controlled schema migrations. |
| **Authentication** | PyJWT / Passlib | `2.8+` | Token encoding, decoding, and password hashing. |
| **Server Runtime** | Uvicorn | `0.27+` | ASGI worker management. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```
app/
├── alembic/              # Database migration scripts
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic Settings management
│   ├── database.py       # Async engine & sessionmaker
│   └── security.py       # JWT creation & verification
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User Model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic DTOs
├── api/
│   ├── v1/
│   │   ├── api.py        # Router aggregation
│   │   └── endpoints/
│   │       ├── auth.py   # Login & Token refresh
│   │       └── users.py  # User CRUD operations
│   └── deps.py           # FastAPI Dependencies (get_db, get_current_user)
├── main.py               # FastAPI Application factory
├── Dockerfile            # Multi-stage production container
├── docker-compose.yml    # Local multi-container orchestration
└── requirements.txt      # Pinned Python dependencies
```

---

### `app/core/config.py`
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
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
    POSTGRES_PORT: int = 5432

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

### `app/core/database.py`
```python
from typing import AsyncGenerator
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
    """Dependency function that yields database sessions per request."""
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

### `app/models/user.py`
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

---

### `app/core/security.py`
```python
from datetime import datetime, timedelta, timezone
from typing import Any, Union
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### `app/api/deps.py`
```python
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
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
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            raise credentials_exception
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (PyJWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

---

### `Dockerfile`
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

# Create non-root system user for security
RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### `docker-compose.yml`
```yaml
version: '3.8'

services:
  web:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=app_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=app_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d app_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes:**
   * *Anti-Pattern:* Using standard `requests`, `time.sleep()`, or synchronous database drivers (`psycopg2`) inside `async def` endpoints. This blocks the entire event loop.
   * *Correction:* Use `httpx` for async HTTP requests, `asyncio.sleep()`, and `asyncpg` via SQLAlchemy async extensions.
2. **Hardcoding Secrets & Configuration:**
   * *Anti-Pattern:* Writing database credentials, JWT secret keys, or API tokens directly into code or committing `.env` files to Git.
   * *Correction:* Use Pydantic's `BaseSettings` to enforce runtime environment variable validation.
3. **Ignoring Database Connection Pooling Limits:**
   * *Anti-Pattern:* Opening and closing new database engine instances per request.
   * *Correction:* Initialize a single global `async_engine` instance and yield session scopes via FastAPI dependency injection (`Depends(get_db)`).
4. **Running Containers as Root:**
   * *Anti-Pattern:* Leaving the default container user as root, making host systems vulnerable if container breakout occurs.
   * *Correction:* Implement multi-stage builds and execute applications under unprivileged system users (e.g., `USER appuser`).

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Always run Uvicorn with multiple worker processes behind a reverse proxy (Nginx or Traefik) based on CPU cores: `--workers $(nproc)`.
* **Database Indexing:** Ensure foreign keys, lookup columns (`email`), and frequently filtered attributes have explicit database indexes (`index=True`).
* **Connection Pool Tuning:** Adjust `pool_size` and `max_overflow` in your SQLAlchemy engine configuration based on expected concurrent load and database server resource limits.
* **Response Compression:** Enable `GZipMiddleware` in FastAPI (`app.add_middleware(GZipMiddleware, minimum_size=1000)`) to reduce JSON payload sizes over the network.

---

## 6. Commercial License & Attribution Summary

### License Type
**MicroCorp AI Commercial Client Delivery License (v1.0)**

### Terms of Use
* **Granted Rights:** You are authorized to deploy, modify, integrate, and distribute this codebase within commercial client projects, SaaS products, and freelance deliverables managed by your agency or engineering practice.
* **Restrictions:** Reselling, redistributing, or publishing this specific boilerplate as a standalone template, open-source framework, or digital product on marketplaces (e.g., Gumroad, GitHub Marketplace) is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI accepts no liability for system downtime, security compromises, or data loss arising from improper configuration or deployment.