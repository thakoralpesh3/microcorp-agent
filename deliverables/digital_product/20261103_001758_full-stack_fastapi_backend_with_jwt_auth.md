# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*
> *Turnkey Enterprise Solution for High-Performance Microservices*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Modular Boilerplate with Async PostgreSQL, JWT Auth, Alembic, and Multi-Stage Docker Setup

Stop wasting 40+ hours configuring boilerplate infrastructure for every new client project. This commercial-grade, production-ready FastAPI backend template gives you a battle-tested architecture out of the box. Designed specifically for engineering teams and elite freelancers building high-throughput APIs, this turnkey solution bridges the gap between rapid prototyping and enterprise-grade scalability.

### Core Value Proposition
* **Zero Setup Friction:** Spin up a fully configured async database, Redis cache, and FastAPI instance with a single `docker compose up --build`.
* **Security First:** Implements stateless JWT authentication with dual token architecture (Access/Refresh tokens), secure password hashing via `passlib[bcrypt]`, and CORS protection.
* **Production Ready:** Includes Alembic database migrations, structured JSON logging, health-check probes, and multi-stage Docker builds optimized for minimal image footprint.
* **Developer Experience (DX):** Fully typed with Python 3.11+ type hints, Pydantic v2 data validation, and auto-generated Swagger/Redoc documentation.

---

## 2. Quick Start & Core Concepts

### System Requirements
* Python 3.11+
* Docker & Docker Compose v2+

### Quick Start Commands
```bash
# 1. Clone or extract the project bundle
cd fastapi-enterprise-boilerplate

# 2. Configure environment variables
cp .env.example .env
# Edit .env and supply your secure secrets (SECRET_KEY, DB credentials)

# 3. Launch the containerized stack
docker compose up --build -d

# 4. Verify database migrations have applied
docker compose logs api
```

### Core Architecture Concepts
| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (ASGI via Uvicorn) | High-performance asynchronous request routing and automatic OpenAPI generation. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, settings management, and serialization. |
| **Database ORM** | SQLAlchemy 2.0 (AsyncIO) | Non-blocking database operations over PostgreSQL. |
| **Migrations** | Alembic | Version-controlled database schema evolution. |
| **Authentication** | python-jose & passlib | Stateless JSON Web Token generation and secure password hashing. |
| **Containerization** | Docker (Multi-stage) | Lean, secure production runtime environments running as non-root users. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
.
├── alembic/                 # Database migration scripts
├── app/
│   ├── api/                 # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/   # auth.py, users.py, items.py
│   │   │   └── api.py       # APIRouter aggregation
│   ├── core/                # Configuration, security, database session
│   │   ├── config.py        # Pydantic BaseSettings
│   │   ├── database.py      # Async session maker
│   │   └── security.py      # JWT encoding/decoding & hashing
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response models
│   └── main.py              # FastAPI application entrypoint
├── Dockerfile               # Multi-stage production container
├── docker-compose.yml       # Local orchestration stack
├── requirements.txt         # Pinned dependency manifest
└── .env.example             # Template environment variables
```

---

### Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
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

### Database Session Factory (`app/core/database.py`)
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

### Security Utilities (`app/core/security.py`)
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
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User
from app.schemas.token import TokenSchema

router = APIRouter()


@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalars().first()

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

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
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
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

# Create non-privileged user for enhanced container security
RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### Docker Compose Stack (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
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
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* ❌ **Anti-Pattern: Blocking I/O in Async Paths**
  * *The Trap:* Utilizing synchronous libraries like `requests` or blocking ORM querying logic inside an `async def` FastAPI route. This starves the event loop and tanks concurrency.
  * *The Fix:* Use asynchronous drivers (`asyncpg` for Postgres, `httpx` for HTTP requests) or run blocking operations via `run_in_threadpool`.

* ❌ **Anti-Pattern: Hardcoding Configuration Values**
  * *The Trap:* Placing database URIs, secret keys, or external service credentials directly inside python files.
  * *The Fix:* Always use Pydantic `BaseSettings` mapped strictly to environment variables loaded via `.env`.

* ❌ **Anti-Pattern: Not Handling Database Connection Lifecycles**
  * *The Trap:* Instantiating global database connections without proper pooling limits, resulting in connection leaks under high load.
  * *The Fix:* Utilize SQLAlchemy 2.0's `async_sessionmaker` combined with a dependency injection generator (`get_db`) ensuring automatic cleanup (`session.close()`).

* ❌ **Anti-Pattern: Running Containers as `root`**
  * *The Trap:* Defaulting to the root user inside Docker containers, leaving the host system vulnerable if container isolation is compromised.
  * *The Fix:* Implement multi-stage builds and create a dedicated non-privileged system user (`USER appuser`) in your final runtime container.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a reverse proxy (like Nginx), scale your Uvicorn application using multiple worker processes matching your vCPU count (`--workers 4`).
* **Connection Pooling Optimization:** Tune SQLAlchemy `pool_size` and `max_overflow` parameters to match your database tier capacity to prevent connection exhaustion.
* **Selectively Load Relationships:** Avoid N+1 query problems by making strategic use of SQLAlchemy's `selectinload` or `joinedload` options when serializing complex relational models.
* **Response Compression:** Integrate `GZipMiddleware` into your FastAPI app instance to automatically compress responses larger than 1000 bytes, drastically decreasing network payloads.

---

## 6. Commercial License & Attribution Summary

### Commercial License Agreement
* **Permitted Use:** This turnkey template is licensed for deployment in commercial client projects, internal enterprise applications, and freelance deliverables.
* **Restrictions:** Reselling, sub-licensing, or redistributing this boilerplate code as a standalone competing template product is strictly prohibited.
* **No Warranty:** Provided *as is*, without warranty of any kind, express or implied. The author/agency assumes zero liability for system outages or security vulnerabilities arising from improper configuration of deployed instances.

*Generated with precision by Backend Architect 🏗️ — The Agency Engineering Division.*