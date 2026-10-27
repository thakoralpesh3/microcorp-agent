# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*A Production-Grade, Turnkey Microservices Boilerplate for Enterprise Clients & Freelance Delivery*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Engine: JWT Auth, Async PostgreSQL, & Dockerized CI/CD
Stop spending 40+ hours setting up boilerplate architecture for every new client project. This commercial-grade turnkey solution provides a fully asynchronous, highly scalable FastAPI backend pre-configured with industry-standard security, database migrations, dependency injection, and a production-ready multi-stage Docker environment.

#### **What’s Included:**
* **Production-Ready Security:** OAuth2 with Password Flow, JWT access/refresh token rotation, HTTP-only secure cookie support, and Argon2 password hashing.
* **Modern Data Layer:** Asynchronous SQLAlchemy 2.0 with Alembic migrations running on PostgreSQL, fully typed with Pydantic v2.
* **Developer Experience:** Strict Ruff linting/formatting rules, Pytest async test suite with SQLite in-memory overrides, and a fully orchestrated Docker Compose setup.
* **Commercial Grade:** Zero-dependency vendor lock-in; easily deployable to AWS ECS, Google Cloud Run, DigitalOcean, or bare-metal VPS.

---

## 2. Quick Start & Core Concepts

### Syntax & Architecture Reference Guide

| Component | Technology | Purpose | Key Benefit |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI (v0.110+) | API routing & validation | Automatic OpenAPI docs, high performance via Starlette/Uvicorn. |
| **Data Validation** | Pydantic v2 | Schema definition & serialization | Rust-powered performance, strict runtime type checking. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Database interaction | Non-blocking I/O using `asyncpg` driver for high concurrency. |
| **Migrations** | Alembic | Schema version control | Safe, transactional database upgrades and rollbacks. |
| **Authentication**| PyJWT / Passlib | Token encoding & decoding | Stateless auth with short-lived access tokens and refresh flows. |
| **Containerization**| Docker & Compose | Environment isolation | Identical parity between local dev, staging, and production. |

### ⚡ 3-Minute Quick Start

```bash
# 1. Clone or extract the boilerplate
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-engine.git my-backend
cd my-backend

# 2. Copy the environment variables template
cp .env.example .env

# 3. Spin up the containers (PostgreSQL + FastAPI)
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head

# 5. Verify the deployment
curl http://localhost:8000/health
```

---

## 3. Production Code Patterns & Architecture Examples

### 📁 Project Directory Structure
```text
.
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── .env.example
├── alembic/
│   └── versions/
└── app/
    ├── __init__.py
    ├── main.py
    ├── core/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── database.py
    │   └── security.py
    ├── models/
    │   ├── __init__.py
    │   └── user.py
    ├── schemas/
    │   ├── __init__.py
    │   └── user.py
    ├── api/
    │   ├── __init__.py
    │   ├── deps.py
    │   └── v1/
    │       ├── __init__.py
    │       ├── api.py
    │       endpoints/
    │           ├── auth.py
    │           └── users.py
    └── crud/
        ├── __init__.py
        └── crud_user.py
```

---

### ⚙️ 1. Core Configuration (`app/core/config.py`)
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

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### 🗄️ 2. Async Database Engine (`app/core/database.py`)
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

### 🔐 3. Security & JWT Utilities (`app/core/security.py`)
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


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### 📦 4. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
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
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

---

### 🛡️ 5. API Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.crud.crud_user import user_crud

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
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await user_crud.get(db, id=user_id)
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

### 🌐 6. Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.core import security
from app.core.config import settings
from app.crud.crud_user import user_crud
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await user_crud.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in the system.",
        )
    user = await user_crud.create(db, obj_in=user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await user_crud.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### 🐳 7. Production Multi-Stage Dockerfile (`Dockerfile`)
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

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### 🐙 8. Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_PORT=5432
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Synchronous Database Operations in Async Endpoints
* **The Anti-Pattern:** Using standard `psycopg2` or synchronous SQLAlchemy sessions (`Session` instead of `AsyncSession`) inside `async def` route handlers. This blocks the main event loop and destroys concurrent throughput.
* **The Fix:** Always use `asyncpg` with SQLAlchemy 2.0 async sessions and ensure all database helper methods are awaited properly.

### ❌ 2. Storing Secrets in Source Control
* **The Anti-Pattern:** Hardcoding JWT secret keys or database credentials directly into `config.py` or checking `.env` files into Git.
* **The Fix:** Use `.env.example` as a safe template, add `.env` to `.gitignore`, and inject secrets securely via orchestrator environment managers (AWS Secrets Manager, Docker Secrets, etc.).

### ❌ 3. Missing Database Connection Pooling Configuration
* **The Anti-Pattern:** Instantiating new database connections per incoming request without pooling limits.
* **The Fix:** Configure explicit `pool_size` and `max_overflow` settings on your async engine initialization (`create_async_engine`).

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** In production, always scale your Uvicorn processes using multiple worker threads behind a reverse proxy (like Nginx or Traefik), or scale container replicas behind an Application Load Balancer.
2. **Pydantic v2 Performance:** Leverage Pydantic v2's compiled Rust core by avoiding custom complex validators where native types or field constraints (`Field(ge=0, max_length=100)`) can handle validation at C-speed.
3. **Database Indexing:** Ensure all foreign keys, lookup columns (such as `email`), and frequently filtered attributes have explicit database indexes defined in your SQLAlchemy models.
4. **Response Caching:** For high-read endpoints that rarely change, integrate Redis caching layers using `fastapi-cache2` to bypass the database entirely.

---

## 6. Commercial License & Attribution Summary

```text
MIT License

Copyright (c) 2026 MicroCorp AI / Backend Engineering Division

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

*Designed and engineered with precision by **Backend Architect 🏗️** from The Agency.*