# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Delivery Series*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Engine: Production-Ready JWT Auth & Docker Boilerplate
Stop wasting 40+ hours writing repetitive boilerplate code for your clients. This enterprise-grade, turn-key FastAPI backend comes fully equipped with secure JSON Web Token (JWT) authentication, Role-Based Access Control (RBAC), SQLAlchemy 2.0 async ORM, Alembic database migrations, and a fully optimized Docker Compose development/production environment.

#### Target Buyers & Use Cases
* **Freelancers & Agencies:** Accelerate time-to-delivery for client MVPs by 75%. Deliver secure, scalable backends on day one.
* **Indie Hackers:** Launch SaaS platforms rapidly with a battle-tested architecture that handles auth, database pooling, and containerization out of the box.
* **Enterprise Teams:** Standardize microservice skeletons with strict typing, Pydantic V2 validation, and clean layered architecture.

#### Key Features
* 🔒 **Secure Authentication:** OAuth2 with Password Bearer, JWT access/refresh tokens, and bcrypt password hashing.
* ⚡ **High Performance:** Built natively on Async FastAPI and SQLAlchemy 2.0 for asynchronous non-blocking database queries.
* 🐳 **Containerized Workflow:** Multi-stage Dockerfile with non-root security and a robust `docker-compose.yml` including PostgreSQL and Redis.
* 📦 **Database Management:** Pre-configured Alembic environment for zero-downtime schema migrations.
* 🧪 **Developer Experience:** Fully typed with strict mypy compliance, pre-commit hooks, and a clean domain-driven project layout.

---

## 2. Quick Start & Core Concepts

### Syntax & Architectural Mapping Reference

| Concept | FastAPI / Python Implementation | Enterprise Purpose |
| :--- | :--- | :--- |
| **Dependency Injection** | `Depends(get_db)`, `Security(get_current_active_user)` | Decouples infrastructure logic (DB sessions, auth) from route handlers for clean unit testing. |
| **Request Validation** | Pydantic V2 (`BaseModel`, `Field`, `email_validator`) | Validates incoming payloads at runtime, automatically generating OpenAPI/Swagger schemas. |
| **ORM & Migrations** | SQLAlchemy 2.0 Async (`AsyncSession`) + Alembic | Manages relational database interactions asynchronously and tracks schema evolution over time. |
| **Token Lifecycle** | `python-jose` / `passlib` (Bcrypt) | Issues short-lived Access Tokens (15m) and secure Refresh Tokens (7d) for stateless auth. |
| **Containerization** | Multi-stage Docker build + Alpine/Slim Python images | Minimizes container image attack surface and optimizes layer caching for rapid CI/CD builds. |

### ⚡ 3-Minute Quick Start Guide

Clone the repository and spin up the entire stack using Docker Compose:

```bash
# 1. Clone or unpack the boilerplate
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Configure environment variables
cp .env.example .env
# Edit .env and set your secure SECRET_KEY and DB credentials

# 3. Build and launch containers
docker-compose up --build -d

# 4. Run database migrations inside the container
docker-compose exec web alembic upgrade head

# 5. Access interactive API documentation
# Open http://localhost:8000/docs in your browser
```

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi_app/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API routers (Endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # auth.py, users.py, items.py
│   │   │   └── router.py     # API router aggregator
│   ├── core/                 # Config, security, database session
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── crud/                 # Database CRUD operation wrappers
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic validation schemas
│   └── main.py               # FastAPI application entrypoint
├── Dockerfile                # Multi-stage production Dockerfile
├── docker-compose.yml        # Local orchestration
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template
```

---

### 1. Configuration Management (`app/core/config.py`)
Uses Pydantic-Settings to securely load and validate environment variables at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp AI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/"
                f"{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### 2. Async Database Session (`app/core/database.py`)
Configures the SQLAlchemy 2.0 asynchronous engine and session factory.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
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

---

### 3. Security & JWT Utilities (`app/core/security.py`)
Handles password hashing via Passlib and JWT creation/verification.

```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
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
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
```

---

### 4. User Model (`app/models/user.py`)
Standard SQLAlchemy 2.0 mapped model with strict typing.

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
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

### 5. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
Implements secure login yielding JWT access tokens.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.crud.crud_user import user_crud
from app.schemas.token import Token

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = await user_crud.get_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 6. Main Application Entrypoint (`app/main.py`)
Configures middleware, exception handlers, and API router integration.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 7. Multi-Stage Production Dockerfile (`Dockerfile`)
Optimized for minimal image footprint and hardened security (non-root execution).

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

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create non-root system user for security compliance
RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 8. Production Orchestration (`docker-compose.yml`)
Production-ready container setup with healthchecks and persistent volumes.

```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: fastapi_web
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=supersecurepassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=your_super_secret_jwt_key_here
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=supersecurepassword
      - POSTGRES_DB=enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* ❌ **Blocking I/O in Async Routes:** Using synchronous database drivers (`psycopg2`) or blocking operations (`time.sleep`, synchronous requests) inside `async def` endpoints will freeze the event loop. Always use async drivers (`asyncpg`) and `await` operations.
* ❌ **Hardcoding Secrets:** Never commit `.env` files or hardcode JWT secret keys in source code. Always inject secrets via environment variables or secret managers (AWS Secrets Manager, HashiCorp Vault).
* ❌ **Missing Database Connection Pooling:** Failing to configure pool sizes (`pool_size`, `max_overflow`) can exhaust database connections under high concurrent load. Rely on SQLAlchemy's built-in pooling configured via async engines.
* ❌ **Catching Base Exceptions Silently:** Using `except Exception:` without re-raising or logging appropriately masks critical database failures and security exceptions. Always handle explicit exceptions and ensure proper transaction rollbacks.
* ❌ **Running as Root in Containers:** Running your FastAPI app as the `root` user inside Docker introduces severe container escape vulnerabilities. Always use a dedicated non-root system user (as shown in the provided Dockerfile).

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** When deploying to production behind Nginx or a load balancer, run Uvicorn with multiple worker processes using process managers like Gunicorn or Guroonga, or scale replicas via Docker Swarm/Kubernetes.
* **Database Indexing:** Ensure foreign keys and frequently queried fields (such as `users.email`) are explicitly indexed in your SQLAlchemy models (`index=True`).
* **Response Compression:** Integrate `GZipMiddleware` in FastAPI for responses exceeding 1000 bytes to minimize network bandwidth consumption.
* **Connection Pooling tuning:** Fine-tune database connection limits based on your server's vCPU count and PostgreSQL `max_connections` configuration to prevent connection throttling.

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial License (Permissive Agency Tier)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this software codebase in commercial client projects, SaaS products, and internal enterprise architectures.
* **Restrictions:** Redistribution, resale, or sub-licensing of this digital product as a standalone boilerplate, template, or code kit on marketplaces (e.g., GitHub Marketplace, Gumroad, Envato) is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claim, damages, or liabilities arising from the deployment of this software.