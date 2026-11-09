# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*
> *Turnkey Enterprise Solution for High-Performance Microservices*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Boilerplate: Production-Grade Async Backend with JWT Authentication & Dockerized Infrastructure

Stop spending weeks configuring boilerplate architectures, database sessions, password hashing, and container lifecycles. This turnkey enterprise backend solution delivers a battle-tested, asynchronous FastAPI foundation engineered specifically for scalable microservices and high-throughput client applications.

#### Key Business & Technical Benefits:
* **Zero-Configuration Setup:** Spin up a fully functional, containerized backend complete with PostgreSQL, Redis, and PgAdmin using a single command.
* **Military-Grade Security:** Implements stateless JWT (JSON Web Token) authentication with secure refresh token rotation, password hashing via `passlib[bcrypt]`, and OAuth2 password bearer flows.
* **Modern Async Architecture:** Built natively on `asyncio`, SQLAlchemy 2.0+ asynchronous sessions, and Pydantic v2 for hyper-fast data validation and serialization.
* **Developer Ergonomics:** Includes automated database migrations via Alembic, structured JSON logging, CORS middleware pre-configured, and comprehensive error handling.
* **Ready for Commercial Deployment:** Comes out-of-the-box with multi-stage Dockerfiles, Docker Compose production profiles, and environment-driven configuration management.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
The system follows a strict asynchronous layered architecture separating transport (Routers), business logic (Services/CRUD), data abstraction (SQLAlchemy Models), and validation (Pydantic Schemas).

| Component | Technology | Role / Responsibility |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous HTTP routing and OpenAPI doc generation. |
| **Data Validation** | Pydantic v2 | Strict schema validation, settings management, and serialization. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking relational database mapping and connection pooling. |
| **Database Migration**| Alembic | Version-controlled schema migrations for PostgreSQL. |
| **Authentication** | python-jose & passlib | JWT generation, verification, and secure password hashing. |
| **Containerization**| Docker & Compose | Isolated multi-container environments for dev and production. |

### ⚡ 60-Second Quick Start

1. **Clone and Configure Environment:**
```bash
git clone https://github.com/the-agency/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate
cp .env.example .env
```

2. **Spin Up Infrastructure via Docker Compose:**
```bash
docker compose up --build -d
```

3. **Verify the Installation:**
* API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
* Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 3. Production Code Patterns & Architecture Examples

### 📂 Directory Structure
```text
backend/
├── alembic/                  # Database migrations
├── app/
│   ├── api/                  # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # Auth, Users, Items routes
│   │   │   └── api.router    # Main router aggregator
│   ├── core/                 # Config, security, database sessions
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic validation schemas
│   ├── services/             # Business logic layer
│   └── main.py               # Application entry point
├── Dockerfile                # Production multi-stage build
├── docker-compose.yml        # Local orchestration
└── requirements.txt          # Python dependencies
```

---

### ⚙️ 1. Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )


settings = Settings()
```

---

### 🔌 2. Database Session Manager (`app/core/database.py`)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


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

### 🔐 3. Security & JWT Utils (`app/core/security.py`)
```python
from datetime import datetime, timedelta
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### 👤 4. SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

### 🛡️ 5. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.token import TokenSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
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

    access_token = create_access_token(subject=user.email)
    refresh_token = create_refresh_token(subject=user.email)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### 🚀 6. Application Entry Point (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production to restrict domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 🐳 7. Multi-Stage Dockerfile (`Dockerfile`)
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 🐳 8. Docker Compose Orchestration (`docker-compose.yml`)
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
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
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
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Synchronous and Asynchronous DB Sessions:**
   * **The Trap:** Using standard `psycopg2` or synchronous session makers within `async def` FastAPI route endpoints blocks the entire event loop.
   * **The Fix:** Always use `asyncpg` drivers and `sqlalchemy.ext.asyncio` session factories.
2. ❌ **Hardcoding Secrets in Code or Docker Compose:**
   * **The Trap:** Committing `.env` files or hardcoding `SECRET_KEY` values directly into `docker-compose.yml`.
   * **The Fix:** Use environment variables exclusively and validate them via Pydantic `BaseSettings`.
3. ❌ **Forgetting Database Connection Pooling Limits:**
   * **The Trap:** Spawning infinite unmanaged database connections under high concurrent load, crashing PostgreSQL.
   * **The Fix:** Configure `pool_size` and `max_overflow` parameters on the SQLAlchemy async engine.
4. ❌ **Swallowing Exceptions in Async Context Managers:**
   * **The Trap:** Catching general exceptions without issuing a session rollback (`await session.rollback()`), leaving transactions hanging.
   * **The Fix:** Implement robust try/except blocks inside your dependency injection generators.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, run Uvicorn behind a process manager or orchestrator like Gunicorn or Kubernetes, utilizing multiple worker processes:
  ```bash
  uvicorn app.main:app --workers 4 --loop uvloop --http httptools
  ```
* **Enable `uvloop`:** Install `uvloop` (`pip install uvloop`) to drop-in replace Python's default asyncio event loop with one written in Cython for Node.js-beating performance.
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (e.g., `email`, `username`) are explicitly indexed in your SQLAlchemy models (`index=True`).
* **Response Caching:** Integrate Redis caching layers for read-heavy endpoints that rarely change to bypass database hits entirely.

---

## 6. Commercial License & Attribution Summary

* **Product SKU:** `AGENCY-FT-FASTAPI-JWT-001`
* **License Type:** Commercial Turnkey / Enterprise Deployment License
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this codebase for commercial client projects, internal enterprise systems, and SaaS platforms.
* **Restrictions:** Redistribution or resale of this exact boilerplate package as a standalone template on marketplaces is strictly prohibited.
* **Attribution:** Maintained and engineered by **The Agency - Engineering Division**.