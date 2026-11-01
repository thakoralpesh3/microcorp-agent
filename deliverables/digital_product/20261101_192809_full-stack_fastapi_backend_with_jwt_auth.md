# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Commercial Product Suite*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, Async PostgreSQL, & Dockerized Production Ready**

#### **Value Proposition**
Stop wasting 40+ hours writing boilerplate code, configuring CORS, debugging async database sessions, and setting up secure JWT authentication flows from scratch. This production-ready, fully type-hinted FastAPI backend template provides a battle-tested, modular architecture designed for instant deployment. Whether you are delivering a turnkey solution to a high-ticket Fiverr client or bootstrapping your own SaaS, this kit ensures strict separation of concerns, enterprise-level security, and high-performance asynchronous execution out of the box.

#### **What’s Included:**
- **Asynchronous Database Layer:** Powered by `SQLAlchemy 2.0` (async engine) and `Alembic` for bulletproof database migrations.
- **Secure Authentication Flow:** OAuth2 with Password (and hashing via `Passlib` + `Bcrypt`), access tokens, and refresh tokens via HttpOnly cookies.
- **Dependency Injection Routing:** Clean dependency overrides for database sessions and current active user validation.
- **Production-Ready Containerization:** Multi-stage `Dockerfile` and `docker-compose.yml` orchestrated with PostgreSQL and Redis.
- **Automated Validation:** Pydantic v2 strict schemas for runtime data integrity.

---

## 2. ## Quick Start & Core Concepts

### **The Architecture Stack**
| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | High-performance, async-native API routing and auto-docs |
| **ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database operations and models |
| **Migrations** | Alembic | Schema version control and forward/backward migrations |
| **Auth** | python-jose & passlib | Stateless JWT creation, verification, and secure password hashing |
| **Validation** | Pydantic v2 | Strict input/output payload validation and serialization |
| **Runtime** | Uvicorn + Gunicorn | ASGI server orchestration for multi-worker scaling |

### **5-Minute Quick Start**

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
   cd fastapi-enterprise-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Infrastructure via Docker:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify Health Check:**
   Open your browser and navigate to `http://localhost:8000/health` or check the interactive API docs at `http://localhost:8000/docs`.

---

## 3. ## Production Code Patterns & Architecture Examples

### **Directory Structure**
```text
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic BaseSettings for environment variables
│   ├── database.py       # Async engine & sessionmaker factory
│   └── security.py       # JWT creation, verification, & password hashing
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User ORM Model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic schemas (UserCreate, UserResponse, Token)
├── api/
│   ├── v1/
│   │   ├── api.py        # API router aggregator
│   │   └── endpoints/
│   │       ├── auth.py   # Login & Token generation
│   │       └── users.py  # User registration & profile management
│   └── deps.py           # Reusable FastAPI dependencies (get_db, get_current_user)
├── main.py               # FastAPI application factory
└── alembic/              # Database migration scripts
```

---

### **1. Core Configuration (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    def assemble_db_connection(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


settings = Settings()
```

---

### **2. Database Setup & Session Factory (`app/core/database.py`)**
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
    settings.assemble_db_connection(), echo=False, future=True
)

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

---

### **3. Security & JWT Utilities (`app/core/security.py`)**
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
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
```

---

### **4. Dependency Injection (`app/api/deps.py`)**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = await db.get(User, token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user
```

---

### **5. Auth Endpoints (`app/api/v1/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### **6. Main App Factory (`app/main.py`)**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Modify in production to strict origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/health", tags=["Health Check"])
    async def health_check():
        return {"status": "healthy", "service": settings.PROJECT_NAME}

    return application


app = get_application()
```

---

### **7. Production Docker Setup (`Dockerfile`)**
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

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **8. Docker Compose (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes:**
   - *Anti-Pattern:* Utilizing standard library `requests` or blocking ORM queries inside `async def` paths, freezing the event loop.
   - *Fix:* Use `httpx` for async HTTP requests and SQLAlchemy 2.0 `AsyncSession` methods (`await db.execute(...)`).
2. **Hardcoding Environment Variables:**
   - *Anti-Pattern:* Placing database credentials or JWT secrets inside source files.
   - *Fix:* Always load via Pydantic `BaseSettings` reading from `.env` or system environment vectors.
3. **Improper Session Management:**
   - *Anti-Pattern:* Forgetting to close database sessions or failing to rollback transactions upon uncaught exceptions.
   - *Fix:* Leverage FastAPI dependency injection with context managers (`yield` pattern with explicit `try/except/finally` blocks).
4. **Exposing Stack Traces in Production:**
   - *Anti-Pattern:* Letting uncaught internal server errors output full Python tracebacks to external clients.
   - *Fix:* Use custom exception handlers to map system faults to sanitized HTTP 500 error responses.

---

## 5. ## Performance & Optimization Tips

- **Worker Scaling:** Adjust the Uvicorn worker count in production containers based on CPU cores (`--workers $(nproc)`). For I/O-bound microservices, use `uvicorn app.main:app --workers 4`.
- **Connection Pooling:** Configure SQLAlchemy engine pool sizes explicitly via `pool_size` and `max_overflow` arguments to prevent database exhaustion under high concurrency loads.
- **Response Caching:** Implement Redis caching layers for read-heavy, low-volatility database query endpoints using fastapi-cache2.
- **Payload Compression:** Add `GZipMiddleware` to your FastAPI application wrapper to automatically compress responses exceeding 1KB:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware

  app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 6. ## Commercial License & Attribution Summary

### **Commercial Use Grant**
- **License Type:** MicroCorp AI Commercial Developer License (Single-Client / Multi-Project Delivery).
- **Permissions:** You are explicitly authorized to use, modify, rebrand, and distribute this codebase as part of deliverables provided to freelance clients (e.g., Fiverr, Upwork) or proprietary internal software projects.
- **Restrictions:** Reselling or redistributing this repository as an unmodified standalone "boilerplates/templates kit" on open marketplaces (Gumroad, GitHub, etc.) is strictly prohibited.
- **Attribution:** Maintained by MicroCorp AI Engineering Division. Provided *as-is* without express warranty or liability.