# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Turnkey Architecture*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Kit with JWT Authentication & Dockerized Infrastructure

Stop wasting 40+ hours setting up boilerplate, configuring secure password hashing, wiring up SQLAlchemy async sessions, and orchestrating Docker containers. This production-grade turnkey solution provides a fully tested, secure, and scalable backend architecture designed specifically for rapid client delivery and enterprise deployment.

#### Value Proposition
* **Time-to-Market:** Cut backend bootstrap time from days to minutes.
* **Security First:** Implements industry-standard OAuth2 with Password Flow, JWT access/refresh tokens, and bcrypt password hashing out of the box.
* **Modern Stack:** Built on FastAPI, SQLAlchemy (Async), Alembic, Pydantic v2, and PostgreSQL, fully containerized via Docker and Docker Compose.
* **Client-Ready Quality:** Clean, modular project layout adhering to Domain-Driven Design principles, complete with comprehensive error handling and dependency injection.

---

## 2. Quick Start & Core Concepts

Get your local development environment up and running in under 60 seconds.

### Prerequisites
* Docker & Docker Compose v2.20+
* Python 3.11+ (for local execution/testing)

### 1-Minute Quick Start
```bash
# 1. Clone or unpack the template repository
cd fastapi-docker-blueprint

# 2. Configure environment variables
cp .env.example .env

# 3. Spin up the infrastructure (PostgreSQL + FastAPI App)
docker compose up --build -d

# 4. Run database migrations
docker compose exec web alembic upgrade head

# 5. Verify the deployment
curl http://localhost:8000/health
```

### Core Architecture Concepts & Syntax Reference

| Concept | Implementation in this Blueprint | Why It Matters |
| :--- | :--- | :--- |
| **Routing & Validation** | `APIRouter` + Pydantic v2 Models | Automatic request validation, serialization, and interactive OpenAPI docs (`/docs`). |
| **Database ORM** | SQLAlchemy 2.0 (Async Session) | Non-blocking database I/O maximizing throughput under high concurrency. |
| **Migrations** | Alembic | Version-controlled, reproducible schema changes across environments. |
| **Authentication** | JWT (JSON Web Tokens) via `python-jose` | Stateless, cryptographically signed authentication scaling horizontally across server nodes. |
| **Dependency Injection** | FastAPI `Depends` | Clean decoupling of database sessions, current user lookup, and authorization scopes. |

---

## 3. Production Code Patterns & Architecture Examples

This blueprint uses a clean, feature-based modular structure:
```text
app/
├── core/               # Configuration, security, database session
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic validation schemas
├── api/                # API routers (v1 endpoints)
│   ├── v1/
│   │   ├── auth.py
│   │   └── users.py
├── services/           # Business logic layer
└── main.py             # FastAPI application entrypoint
```

### 3.1 Configuration & Environment (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Production Blueprint"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str = ""

    def model_post_init(self, __context) -> None:
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

### 3.2 Asynchronous Database Setup (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


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

### 3.3 Security & JWT Utilities (`app/core/security.py`)
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
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

### 3.4 Authentication Endpoints (`app/api/v1/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.token import TokenSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

### 3.5 Docker Setup (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=production_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking I/O in Async Path Operations**
   * *Anti-Pattern:* Using synchronous libraries like `requests` or standard `sqlite3` inside async FastAPI path operations. This blocks the main event loop and destroys concurrency.
   * *Fix:* Use async-native libraries (`httpx`, `asyncpg`, `databases`) or offload blocking operations using `run_in_threadpool`.

2. **Hardcoding Secrets in Code Repositories**
   * *Anti-Pattern:* Committing database passwords or JWT secrets directly into git.
   * *Fix:* Always utilize environment variables validated via Pydantic `BaseSettings`.

3. **Missing Session Commit/Rollback Management**
   * *Anti-Pattern:* Manually managing sessions inside every single endpoint without proper exception handling, leading to leaked database connections.
   * *Fix:* Use FastAPI dependency injection generators (`yield` with `try/except/finally`) to guarantee session closure.

4. **Catching Generic Exceptions Blindly**
   * *Anti-Pattern:* Using `except Exception:` without logging or re-raising, swallowing critical system errors.
   * *Fix:* Catch specific database and validation exceptions, log them appropriately with structured loggers (e.g., Loguru), and return clean HTTP status codes to clients.

---

## 5. Performance & Optimization Tips

* **Connection Pooling:** Configure SQLAlchemy's pool size and max overflow parameters according to your database tier and expected concurrency load.
* **Gzip Compression:** Add FastAPI's `GZipMiddleware` to automatically compress large JSON payloads for faster client delivery.
* **Response Caching:** Utilize Redis for caching expensive read queries or use HTTP caching headers (`Cache-Control`) where real-time data isn't required.
* **Production ASGI Server:** Always deploy behind Uvicorn workers managed by Gunicorn or optimized container orchestrators (Kubernetes, AWS ECS) in production rather than running `--reload` mode.

---

## 6. Commercial License & Attribution Summary

### Commercial License Agreement
* **Granted Rights:** You are licensed to use, modify, adapt, and distribute this codebase in commercial software products, client deliverables, and SaaS applications created by you or your agency.
* **Restrictions:** You may not resell, sub-license, or redistribute this blueprint as a standalone template, boilerplate kit, or digital product on marketplaces (e.g., Gumroad, GitHub Marketplace, Envato).
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. The author/agency shall not be held liable for any claim, damages, or liability arising from its use.

*Designed & Architected by Backend Architect 🏗️ — The Agency Engineering Division.*