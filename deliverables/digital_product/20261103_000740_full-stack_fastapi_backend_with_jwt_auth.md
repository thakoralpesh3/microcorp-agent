# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Packet*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Enterprise Engine
**Turnkey Microservices-Grade Boilerplate with Asynchronous PostgreSQL, Secure JWT Authentication, Role-Based Access Control (RBAC), and Containerized Multi-Stage Docker Deployments.**

#### Executive Summary
Building production Python backends from scratch is fraught with recurring infrastructure bottlenecks: managing database connection pools safely across async boundaries, implementing robust refresh/access token rotation cycles, and writing secure Dockerfiles that don't bloat image size. 

This turnkey solution delivers an enterprise-grade, fully typed, and asynchronously optimized FastAPI backend template. Built specifically for high-throughput microservices and client-facing API products, it drops deployment timelines from weeks to hours.

#### Key Business & Technical Benefits
* **Zero-Tech-Debt Architecture:** Strictly adheres to separation of concerns using dependency injection, repository patterns, and Pydantic v2 data validation.
* **Security First:** Implements stateless JWT authentication with bcrypt password hashing, secure HTTP-only cookie rotation support, and fine-grained scopes.
* **Instant Containerization:** Production-ready multi-stage Dockerfile and Docker Compose setup incorporating health checks, non-root user execution, and persistent volumes.
* **Developer Velocity:** Integrated with Alembic for migrations, Pytest for async unit testing, and Ruff for lightning-fast linting and formatting.

---

## 2. Quick Start & Core Concepts

### System Requirements
* Python 3.11+
* Docker & Docker Compose v2.20+
* Make (optional, for automation shortcuts)

### 5-Minute Local Spin-up
```bash
# 1. Clone or extract the repository bundle
cd fastapi-enterprise-engine

# 2. Configure environment variables
cp .env.example .env
# Edit .env and supply your secure keys (DATABASE_URL, JWT_SECRET_KEY, etc.)

# 3. Spin up infrastructure via Docker Compose
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head

# 5. Verify API health
curl http://localhost:8000/health
```

### Architectural Component Matrix

| Layer | Technology | Responsibility | Best Practice / Rule |
| :--- | :--- | :--- | :--- |
| **API Transport** | FastAPI / Starlette | HTTP routing, request parsing, OpenAPI schema generation. | Keep business logic out of routers; use dependency injection. |
| **Data Validation** | Pydantic v2 | Serialization, deserialization, and strict schema enforcement. | Always define explicit response models (`response_model=UserOut`). |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Object-relational mapping and connection management. | Use `AsyncSession` context managers; never block the event loop. |
| **Migrations** | Alembic | Database schema evolution tracking. | Never edit migration history files once applied to production. |
| **Authentication** | PyJWT / Passlib | Token generation, validation, and secure password hashing. | Store short-lived access tokens (15m) and long-lived refresh tokens. |
| **Containerization** | Docker (Multi-stage) | Isolated runtime environments and dependency bundling. | Run containers as non-root users (`UID 10001`). |

---

## 3. Production Code Patterns & Architecture Examples

### A. Project Directory Structure
```text
fastapi-enterprise-engine/
├── alembic/                      # Database migration scripts
│   └── versions/
├── app/
│   ├── api/                      # API Routers (Endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py               # Shared FastAPI Dependencies
│   ├── core/                     # Configuration & Security
│   │   ├── config.py             # Pydantic BaseSettings
│   │   ├── database.py           # Async Engine & Sessionmaker
│   │   └── security.py           # JWT & Hashing utilities
│   ├── models/                   # SQLAlchemy ORM Models
│   │   └── user.py
│   ├── schemas/                  # Pydantic DTOs
│   │   └── user.py
│   ├── services/                 # Business Logic Layer
│   │   └── user_service.py
│   └── main.py                   # Application Entrypoint
├── tests/                        # Pytest asynchronous test suite
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### B. Configuration Engine (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    # Security
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

### C. Asynchronous Database Session Manager (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
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

### D. Security & JWT Encoder/Decoder (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
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
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, refresh: bool = False) -> dict:
    secret = settings.JWT_REFRESH_SECRET_KEY if refresh else settings.JWT_SECRET_KEY
    return jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
```

### E. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
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

### F. Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
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
        payload = decode_token(token, refresh=False)
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
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

### G. Auth Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, TokenOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=TokenOut)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

### H. Multi-Stage Production Dockerfile (`Dockerfile`)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# If using requirements.txt, substitute accordingly. For poetry/pip:
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

COPY . .
RUN poetry install --no-dev --no-interaction --no-ansi

# Stage 2: Runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . /app

RUN useradd -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### I. Production Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: fastapi_engine_api
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    container_name: fastapi_engine_db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Mixing Synchronous DB Calls in Async Endpoints
**The Anti-Pattern:** Using standard `psycopg2` or synchronous SQLAlchemy sessions inside `async def` route handlers. This blocks the entire Uvicorn event loop, destroying concurrent throughput.
**The Fix:** Always use `asyncpg` with SQLAlchemy's `AsyncSession` and `async/await` syntax.

### ❌ 2. Storing Sensitive Data in JWT Payloads
**The Anti-Pattern:** Embedding passwords, PII, or large authorization objects inside the JWT payload. JWTs are signed, not encrypted; anyone with the token can decode the payload using base64.
**The Fix:** Store only immutable identifiers (`sub: user_id`) and permission scopes. Fetch stateful user profiles from the database if required.

### ❌ 3. Running Containers as Root
**The Anti-Pattern:** Leaving the default root user active inside the Docker container runtime. If an attacker achieves Remote Code Execution (RCE), they immediately inherit container host privileges.
**The Fix:** Always implement a dedicated non-user creation step (`useradd`) inside your multi-stage Dockerfile.

### ❌ 4. Hardcoding Database Credentials in Configuration Files
**The Anti-Pattern:** Placing plaintext database strings or secret keys directly inside `config.py` or version control.
**The Fix:** Enforce strict validation via Pydantic `BaseSettings` reading from localized `.env` files or orchestration secret managers.

---

## 5. Performance & Optimization Tips

1. **Connection Pooling & Tuning:** Configure SQLAlchemy `pool_size` and `max_overflow` based on your Uvicorn worker count and database server limits to avoid exhaustion errors under high load.
2. **Gzip Middleware Compression:** Enable Starlette's `GZipMiddleware` on your FastAPI entrypoint (`main.py`) to drastically cut down payload transfer sizes for large JSON list responses.
3. **Database Indexing Strategy:** Ensure high-frequency query targets (like `email` and foreign keys) are explicitly indexed (`index=True`) to maintain $O(\log n)$ search performance.
4. **Uvicorn Worker Scaling:** In production clusters behind an Nginx or Traefik reverse proxy, run Uvicorn with multiple workers or process managers (e.g., `gunicorn -k uvicorn.workers.UvicornWorker`) mapped to CPU core counts (`2 * CPU + 1`).

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (Type C-Commercial)
* **Copyright (c) 2025 MicroCorp AI & The Agency Engineering Division.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this software codebase in commercial client projects, SaaS products, and internal enterprise architectures.
* **Restrictions:** Redistribution of this exact template as a competing standalone boilerplate, digital product, or open-source template package without prior written authorization from MicroCorp AI is strictly prohibited.
* **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.