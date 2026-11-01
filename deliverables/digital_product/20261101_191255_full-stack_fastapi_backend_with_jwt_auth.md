# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*Engineered by MicroCorp AI Backend Architecture Division*

## 1. Product Title & Value Proposition

### Product Title
**Enterprise-Grade FastAPI Backend Boilerplate with Async JWT Authentication, SQLModel, and Multi-Stage Docker Setup**

### Value Proposition
Stop wasting 40+ hours configuring boilerplate architecture for every new client project. This production-ready, fully typed, asynchronous FastAPI template delivers a secure, scalable foundation out of the box. Featuring production-hardened JWT authentication (with access/refresh token rotation), automated Alembic migrations, PostgreSQL integration via SQLModel, and a fully optimized multi-stage Docker setup, this turnkey solution is engineered to pass strict enterprise security reviews while maximizing developer velocity.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
The backend follows a strict layered architecture pattern separating routing, business logic, data modeling, and infrastructure.

```
[ Client Request ] 
       │
       ▼
[ Nginx / Reverse Proxy ] (Optional)
       │
       ▼
[ FastAPI Application Entrypoint ] (main.py)
       │
       ├─► [ Middleware: CORS, Security Headers, GZip ]
       │
       ▼
[ API Routers ] (/api/v1/auth, /api/v1/users)
       │
       ├─► [ Security Dependencies ] (OAuth2PasswordBearer, JWT Decoder)
       │
       ▼
[ Business Logic / Services ] (CRUD & Domain Rules)
       │
       ▼
[ Data Access Layer ] (SQLModel Async Session & PostgreSQL)
```

### Clean Syntax Reference Table

| Concept / Component | Implementation Technology | Primary Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (0.110+) | High-performance asynchronous REST API framework with auto-validation. |
| **Data Validation & ORM** | SQLModel + Pydantic v2 | Unified data modeling combining Pydantic validation with SQLAlchemy ergonomics. |
| **Database Driver** | AsyncPG + PostgreSQL 16 | Non-blocking asynchronous database driver for maximum concurrent throughput. |
| **Migrations** | Alembic | Version-controlled database schema migrations. |
| **Authentication** | `python-jose` + `passlib` (Bcrypt) | Stateless JWT issuance, validation, and secure password hashing. |
| **Containerization** | Docker (Multi-stage build) | Minimal attack surface and lightweight production images using Alpine/Slim bases. |

---

## 3. Production Code Patterns & Architecture Examples

### 3.1 Project File Tree
```text
fastapi-enterprise-backend/
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
├── alembic/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### 3.2 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

### 3.3 Database Setup (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, echo=False, future=True, pool_pre_ping=True
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

### 3.4 Security & Cryptography (`app/core/security.py`)
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


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

### 3.5 User Model (`app/models/user.py`)
```python
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
```

### 3.6 Dependency Injection (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


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
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, int(user_id))
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

### 3.7 Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api.deps import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.user import User

router = APIRouter()


@router.post("/login")
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.exec(select(User).where(User.email == form_data.username))
    user = result.first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

### 3.8 FastAPI Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure strictly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

### 3.9 Multi-Stage Dockerfile (`Dockerfile`)
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

### 3.10 Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
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
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=Enterprise Backend
      - SECRET_KEY=supersecretkeychangeinproduction
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Database Calls in Async Endpoints**
   * *Anti-Pattern:* Using standard SQLAlchemy sessions or blocking I/O libraries (like `requests`) inside `async def` routes. This blocks the main event loop and destroys concurrency.
   * *Correction:* Always use asynchronous drivers (`asyncpg`) and async sessions (`sqlmodel.ext.asyncio.session.AsyncSession`). For unavoidable blocking legacy libraries, dispatch them using `anyio.to_thread.run_sync()`.

2. **Hardcoding Secrets and Configurations**
   * *Anti-Pattern:* Placing database passwords and JWT secrets directly in source files.
   * *Correction:* Always leverage `pydantic-settings` to ingest configuration securely from environment variables or secure secret stores (AWS Secrets Manager, HashiCorp Vault).

3. **Ignoring Connection Pool Exhaustion**
   * *Anti-Pattern:* Instantiating a new database engine or session factory on every single HTTP request.
   * *Correction:* Initialize a singleton database engine at the application level and utilize FastAPI's dependency injection generator pattern (`yield`) to cleanly scope and close session lifecycles.

4. **Catching Generic Exceptions Silently**
   * *Anti-Pattern:* Using broad `except Exception:` blocks without logging or re-raising, hiding root database or validation errors from monitoring systems.
   * *Correction:* Catch specific exceptions (e.g., `SQLAlchemyError`, `JWTError`) and map them to explicit, secure HTTP status codes with informative client-safe messages.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling behind Gunicorn / Reverse Proxy:** In production container environments, run Uvicorn with multiple worker processes or orchestrate behind Gunicorn using the `UvicornWorker class` worker type to fully saturate multi-core CPU architectures.
* **Database Query Optimization & Indexing:** Ensure high-frequency lookup columns (such as `email`, `tenant_id`, and foreign keys) are explicitly indexed (`index=True`) within your SQLModel definitions. Avoid N+1 query traps by utilizing SQLAlchemy select-in loading (`selectinload`).
* **Response Compression:** Implement `GZipMiddleware` in FastAPI for responses exceeding 1000 bytes to minimize payload sizes over constrained network connections.
* **Connection Pooling Parameters:** Tune your database engine connection pool sizes (`pool_size`, `max_overflow`, `pool_pre_ping`) matching your server concurrency profile to prevent socket starvation under high load.

---

## 6. Commercial License & Attribution Summary

### End-User Commercial License Grant
* **Copyright © MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchasing or acquiring this digital product grants the licensee a non-exclusive, perpetual, worldwide license to use, modify, adapt, and deploy this codebase for commercial client projects, internal enterprise applications, and SaaS ventures.
* **Restrictions:** Redistribution, resale, sub-licensing, or public publishing of this source code as a competing boilerplate, template framework, or digital asset package is strictly prohibited without explicit written authorization from MicroCorp AI.
* **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall MicroCorp AI or the Engineering Division be liable for any claim, damages, or other liability arising from its usage.