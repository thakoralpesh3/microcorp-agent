# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Commercial Assets*  
> **Product ID:** `MC-FASTAPI-JWT-DOCKER-001`  
> **Target Audience:** Enterprise Clients, Senior Full-Stack Engineers, Freelance Deliverables

---

## 1. # Product Title & Value Proposition

### Enterprise-Grade FastAPI Boilerplate: JWT Authentication & Containerized Infrastructure
Stop wasting 40+ hours writing boilerplate user-management, database connection pools, security middleware, and Dockerfiles for every new client project. This commercial turnkey solution provides a production-ready, highly optimized asynchronous FastAPI backend integrated with SQLAlchemy 2.0 (async), Alembic migrations, secure JWT-based authentication (OAuth2 with Password Flow & Bearer tokens), and a multi-stage Docker containerization pipeline.

#### Key Business Benefits:
* **Time-to-Market Reduction:** Deploy secure APIs in minutes instead of weeks.
* **Security First:** Implements industry-standard Argon2/Bcrypt password hashing, short-lived Access Tokens, and secure Refresh Token rotation patterns.
* **Developer Ergonomics:** Fully typed with Python type hints, Pydantic v2 validation, and clean layered architecture (Router $\to$ Service $\to$ Repository $\to$ Model).
* **Production Hardened:** Pre-configured with CORS middleware, structured JSON logging, health-check endpoints, and container orchestration via Docker Compose.

---

## 2. ## Quick Start & Core Concepts

### Syntax & Architectural Reference

| Layer / Component | Technology Stack | Core Responsibility |
| :--- | :--- | :--- |
| **API Framework** | FastAPI (v0.110+) | Asynchronous request handling, automatic OpenAPI/Swagger docs, dependency injection. |
| **Data Validation** | Pydantic v2 | Strict payload validation, serialization, settings management (`BaseSettings`). |
| **ORM & Migrations**| SQLAlchemy 2.0 (Async) + Alembic | Type-safe asynchronous database operations and declarative schema migrations. |
| **Database** | PostgreSQL 16 | Relational persistence layer optimized for high concurrency. |
| **Authentication** | PyJWT / Passlib (Argon2) | Stateless JWT verification, role-based access control (RBAC), secure hashing. |
| **Containerization**| Docker & Docker Compose | Multi-stage builds, non-root execution, isolated networking. |

### 5-Minute Local Execution

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-starter.git
   cd fastapi-jwt-docker-starter
   cp .env.example .env
   ```

2. **Spin Up via Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

3. **Run Database Migrations:**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

4. **Access Interactive Documentation:**
   * Swagger UI: `http://localhost:8000/docs`
   * ReDoc: `http://localhost:8000/redoc`

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
app/
├── core/                  # Configuration, security, database session
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/                # SQLAlchemy ORM Models
│   └── user.py
├── schemas/               # Pydantic Schemas for Validation
│   └── user.py
├── repositories/          # Database Operations Layer
│   └── user.py
├── services/              # Business Logic Layer
│   └── auth.py
├── api/                   # FastAPI Routers (Endpoints)
│   ├── v1/
│   │   ├── api.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       └── users.py
│   └── deps.py            # FastAPI Dependencies (Get DB, Get Current User)
├── main.py                # Application Factory
└── Dockerfile             # Multi-stage production Dockerfile
```

---

### `app/core/config.py` (Environment & Settings)
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
    DATABASE_URL: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def assemble_db_connection(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
```

---

### `app/core/database.py` (Async SQLAlchemy Engine)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.assemble_db_connection(),
    future=True,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
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

### `app/core/security.py` (JWT & Hashing Utilities)
```python
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_refresh_token(
    subject: Union[str, Any], expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

---

### `app/models/user.py` (SQLAlchemy 2.0 Async Model)
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


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
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

---

### `app/schemas/user.py` (Pydantic v2 Validation Schemas)
```python
import uuid
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    id: uuid.UUID

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None
```

---

### `app/api/deps.py` (FastAPI Authentication Dependencies)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload
from sqlalchemy import select

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
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "access" or token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == token_data.sub)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user
```

---

### `app/api/v1/endpoints/auth.py` (Authentication Controller)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser,
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

---

### `Dockerfile` (Multi-Stage Production Container)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . /app

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `docker-compose.yml` (Local & Production Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
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

  backend:
    build: .
    container_name: fastapi_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=supersecretaccesskeychangeinproduction
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints:**
   * *Anti-Pattern:* Utilizing `time.sleep()`, synchronous database drivers (`psycopg2`), or blocking HTTP libraries (`requests`) inside `async def` routes. This blocks the main event loop and destroys concurrency.
   * *Correction:* Use `asyncio.sleep()`, `asyncpg` / SQLAlchemy async sessions, and `httpx` for outbound network requests.

2. **Hardcoding Secrets or Using Insecure Fallbacks:**
   * *Anti-Pattern:* Providing default fallback values for `JWT_SECRET_KEY` in production settings files.
   * *Correction:* Enforce required environment variables using Pydantic validation. The application should fail to start if core cryptographic secrets are missing.

3. **Session Leakage & Missing Context Managers:**
   * *Anti-Pattern:* Manually instantiating database sessions without ensuring they are closed in a `try/finally` block or async context manager.
   * *Correction:* Always use FastAPI's dependency injection system (`Depends(get_db)`) to manage session lifecycles automatically.

4. **Running Containers as Root:**
   * *Anti-Pattern:* Leaving the default container user as `root`, exposing the host system to container escape vulnerabilities.
   * *Correction:* Implement a non-privileged system user (e.g., `useradd -u 1000 appuser`) in your Dockerfile as shown above.

---

## 5. ## Performance & Optimization Tips

* **Connection Pooling:** Tune `pool_size` and `max_overflow` in `create_async_engine()` based on your PostgreSQL server limits and expected worker concurrency.
* **Uvicorn Worker Scaling:** In production environments behind reverse proxies (like Nginx or Traefik), run Uvicorn with Gunicorn process managers or multiple worker processes utilizing `--workers N` based on available CPU cores.
* **Response Serialization:** For high-throughput endpoints returning large lists, utilize Pydantic's `model_dump()` optimizations or yield streaming JSON responses to minimize memory spikes.
* **Database Indexing:** Ensure foreign keys (`user_id`) and lookup columns (`email`) are explicitly indexed in your SQLAlchemy models (`index=True`) to maintain sub-millisecond query execution times under load.

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp AI Commercial Enterprise License (MC-EULA-v1.0)

* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide, royalty-free license to use, modify, adapt, and deploy this codebase for internal use, commercial SaaS applications, and client deliverables (Fiverr/Upwork/Agency contracts).
* **Restrictions:** Redistribution of this codebase as a standalone boilerplate, open-source template, or competing digital product without prior written consent from MicroCorp AI is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI and The Agency Engineering Division assume zero liability for direct or indirect damages arising from the deployment of this software.

---
*Built with precision by The Agency Backend Architect • MicroCorp AI Engineering Division*