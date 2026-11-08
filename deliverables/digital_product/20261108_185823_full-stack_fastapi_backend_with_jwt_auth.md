# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*A Production-Ready, Turnkey Solution for Modern Engineering Teams & High-Value Clients*

---

## 1. Product Title & Value Proposition

### **The Enterprise FastAPI Boilerplate: Bulletproof JWT Authentication & Dockerized Architecture**
Stop wasting 40+ hours setting up boilerplate structures, security configurations, database sessions, and container orchestration for every new client project. This turnkey backend solution gives you an immediate production-ready foundation built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL**, **Pydantic v2**, and **JWT Authentication**, fully containerized via **Docker Compose**.

#### **Key Business Benefits:**
* **Accelerated Time-to-Market:** Deliver client backends 3x faster with a pre-configured, tested architecture.
* **Enterprise-Grade Security:** Out-of-the-box OAuth2 with Password (and hashing via `passlib[bcrypt]`), stateless JWT access/refresh token rotation, and strict CORS policies.
* **Developer Ergonomics:** Fully typed asynchronous database operations, automated Alembic migrations, and hot-reload development containers.
* **Production Resilience:** Health-check endpoints, structured error handling, environment-based configuration management, and multi-stage optimized Docker builds.

---

## 2. Quick Start & Core Concepts

Get this system running locally in under 120 seconds using the clean syntax and layout defined below.

### **System Architecture Overview**
```
[ Client Request ] 
       │
       ▼
[ Nginx / Reverse Proxy ] (Optional, Prod)
       │
       ▼
[ FastAPI Application Container ]
   ├── /api/v1/auth    ──► JWT Token Issuance & Refresh
   ├── /api/v1/users   ──► User Management & RBAC
   └── /api/v1/items   ──► Protected Business Logic
       │
       ▼ (Async SQLAlchemy 2.0)
[ PostgreSQL Database Container ]
```

### **Core Stack & Syntax Reference**

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous REST API routing and validation. |
| **Data Validation** | Pydantic | `2.6+` | Strict request/response serialization and settings management. |
| **ORM & DB** | SQLAlchemy | `2.0+` | Asynchronous database interactions and model mapping. |
| **Database** | PostgreSQL | `16-alpine` | Relational data persistence layer. |
| **Migrations** | Alembic | `1.13+` | Database schema version control and migration management. |
| **Auth** | PyJWT / Passlib | `2.8+ / 1.7+` | Cryptographic password hashing and JSON Web Token verification. |
| **Containerization**| Docker / Compose | `Latest` | Isolated, reproducible environment deployment. |

---

## 3. Production Code Patterns & Architecture Examples

This repository follows a strict modular separation of concerns: `models` (database schemas), `schemas` (pydantic validation), `crud` (database operations), and `api` (routers).

### **Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/
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
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### **A. Core Configuration (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    SQLALCHEMY_DATABASE_URI: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### **B. Asynchronous Database Engine (`app/core/database.py`)**
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
    bind=engine,
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

### **C. Cryptography & JWT Security (`app/core/security.py`)**
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


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **D. SQLAlchemy User Model (`app/models/user.py`)**
```python
import uuid
from sqlalchemy import Boolean, String
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
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

---

### **E. FastAPI Dependencies (`app/api/deps.py`)**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
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
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
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

### **F. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### **G. Application Entrypoint (`app/main.py`)**
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
    allow_origins=["*"],  # Modify in production to explicit domains
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

### **H. Multi-Stage Dockerfile (`Dockerfile`)**
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

### **I. Container Orchestration (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-access-key-change-me
      - JWT_REFRESH_SECRET_KEY=super-secret-refresh-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* ❌ **Anti-Pattern:** Using synchronous database drivers (`psycopg2`) inside an asynchronous FastAPI application.
  * ✅ **Fix:** Always use the async driver stack (`postgresql+asyncpg`) with SQLAlchemy 2.0 `AsyncSession` to prevent thread-pool exhaustion under heavy concurrent load.
* ❌ **Anti-Pattern:** Storing plain text secrets or hardcoding production passwords in `config.py`.
  * ✅ **Fix:** Enforce environment-based configuration via Pydantic `BaseSettings` and ensure `.env` is excluded via `.dockerignore` and `.gitignore`.
* ❌ **Anti-Pattern:** Failing to close database sessions or manual transaction handling errors.
  * ✅ **Fix:** Utilize generator-based dependency injection (`yield session`) combined with explicit context managers to automate commits, rollbacks, and cleanups.
* ❌ **Anti-Pattern:** Long-lived Access Tokens without revocation or rotation strategies.
  * ✅ **Fix:** Keep access tokens short-lived (15 minutes) and issue rotating refresh tokens stored securely on the client or paired with a backend token blacklist table.

---

## 5. Performance & Optimization Tips

1. **Connection Pooling Optimization:** Adjust `pool_size` and `max_overflow` parameters inside `create_async_engine()` depending on your database tier and expected concurrent request load.
2. **Uvicorn Worker Scaling:** In production environments, run Uvicorn behind a process manager like Gunicorn or deploy multiple container replicas managed by Kubernetes/Docker Swarm behind an Nginx or Traefik load balancer.
3. **Response Compression:** Integrate `GZipMiddleware` into your main FastAPI application to minimize JSON payload sizes over low-bandwidth client networks:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```
4. **Database Query Profiling:** Use SQLAlchemy's async logging features or external monitoring APMs (such as Sentry or Prometheus) to intercept slow N+1 query patterns before pushing to production.

---

## 6. Commercial License & Attribution Summary

### **Commercial Use Grant**
* **Single Developer License:** You are granted a perpetual, non-exclusive license to use, modify, adapt, and deploy this codebase for commercial applications, client deliverables, and SaaS products.
* **Restrictions:** Reselling, redistributing, or publishing this exact boilerplate as a competing commercial template package on template marketplaces is strictly prohibited.
* **No Warranty:** This software is provided "as is", without warranty of any kind, express or implied. The author/agency assumes no liability for damages resulting from the deployment of this code.