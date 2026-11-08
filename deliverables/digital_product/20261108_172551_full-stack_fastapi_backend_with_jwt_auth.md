# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Systems Blueprint*

---

## 1. Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready JWT Auth & Dockerized PostgreSQL Architecture**

#### **Value Proposition**
Building a secure, scalable, and fully containerized backend from scratch takes days of boilerplate configuration, security auditing, and architecture planning. This turnkey solution provides a **battle-tested, production-grade FastAPI backend** complete with asynchronous database sessions (SQLAlchemy 2.0), secure JWT authentication (Access & Refresh tokens with sliding expiration), password hashing (Argon2), automated migrations (Alembic), and a fully orchestrated Docker Compose setup.

#### **Target Audience & Use Cases**
*   **Fiverr & Upwork Freelancers:** Drop-in backend template for high-paying client web applications, mobile app APIs, and SaaS MVPs.
*   **Indie Hackers:** Ship secure authentication and database layers in minutes instead of weeks.
*   **Enterprise Engineers:** Standardized microservice skeleton enforcing strict typing, dependency injection, and security best practices.

---

## 2. Quick Start & Core Concepts

### **Architecture Topology**
```
[ Nginx Reverse Proxy ] (Optional / Production)
         │
         ▼
[ FastAPI Application (Uvicorn Workers) ]
   ├── /api/v1/auth    (JWT Login, Refresh, Register)
   ├── /api/v1/users   (User Management, RBAC)
   └── /api/v1/health  (Liveness & Readiness Probes)
         │
         ▼
[ PostgreSQL 16 Alpine ] (Persistent Docker Volume)
```

### **Core Stack & Syntax Quick Reference**

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous REST API routing and validation. |
| **Runtime** | Python | `3.11-slim` | Type-hinted, high-speed execution environment. |
| **Database Driver** | asyncpg | `0.29+` | Non-blocking PostgreSQL driver for Python. |
| **ORM** | SQLAlchemy | `2.0+` | Modern asynchronous Object Relational Mapper with strict typing. |
| **Migrations** | Alembic | `1.13+` | Database schema migration version control. |
| **Auth** | python-jose / passlib | Latest | JWT generation, validation, and secure password hashing. |
| **Containerization** | Docker & Compose | Latest | Isolated multi-container deployment architecture. |

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi-enterprise/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API Routers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   ├── core/                 # Configuration & Security
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/               # SQLAlchemy ORM Models
│   │   └── user.py
│   ├── schemas/              # Pydantic Validation Schemas
│   │   └── user.py
│   └── main.py               # FastAPI Application Entrypoint
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### **Configuration Management (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # SECURITY
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # DATABASE
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### **Asynchronous Database Engine (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

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

### **Security & JWT Utilities (`app/core/security.py`)**
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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **SQLAlchemy User Model (`app/models/user.py`)**
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
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
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

---

### **Pydantic Schemas (`app/schemas/user.py`)**
```python
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_string=100)


class UserResponse(UserBase):
    id: uuid.UUID
    is_superuser: bool
    created_at: datetime

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

### **Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

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
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### **FastAPI Application Entrypoint (`app/main.py`)**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import auth

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### **Production Dockerfile (`Dockerfile`)**
```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **Docker Compose Orchestration (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: secure_password_change_me
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres_user -d enterprise_db"]
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
      - PROJECT_NAME=FastAPI Enterprise
      - SECRET_KEY=super_secret_jwt_key_change_in_production_123456
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=secure_password_change_me
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1.  **Blocking I/O in Async Routes (`def` vs `async def`)**
    *   *Anti-Pattern:* Using standard `def` for routes that perform heavy database querying without async drivers, or executing blocking third-party HTTP requests inside `async def` without `run_in_threadpool`.
    *   *Correction:* Always pair SQLAlchemy 2.0 async sessions with `async def` endpoints, or use `def` for standard synchronous handlers where FastAPI automatically dispatches to a threadpool.
2.  **Hardcoding Secrets in Code Repositories**
    *   *Anti-Pattern:* Committing `.env` files or hardcoding database passwords and JWT secrets directly into `config.py`.
    *   *Correction:* Always leverage Pydantic-Settings with strict environment variable parsing and keep `.env` in `.gitignore`.
3.  **Missing Database Connection Pooling Management**
    *   *Anti-Pattern:* Creating a new SQLAlchemy engine instance per request cycle.
    *   *Correction:* Instantiate a single global engine and sessionmaker pool (as shown in `app/core/database.py`) and use dependency injection (`Depends(get_db)`) to cleanly scope session lifecycles.
4.  **Ignoring Token Revocation & Sliding Expiration**
    *   *Anti-Pattern:* Issuing infinitely valid JWT access tokens without refresh tokens or revocation strategies.
    *   *Correction:* Keep access token lifetimes extremely short (e.g., 15 minutes) and issue a distinct refresh token stored securely with an expiration date.

---

## 5. Performance & Optimization Tips

*   **Uvicorn Worker Scaling:** In production Docker environments behind an Nginx or Traefik reverse proxy, calculate worker count using the formula `(2 * CPU_Cores) + 1`, or deploy container replicas orchestrated via Kubernetes/Docker Swarm.
*   **Database Query Optimization:** Always use SQLAlchemy 2.0 select statements with explicit `.options(selectinload(...))` or `.joinedload(...)` parameters to prevent N+1 query performance degradation during relationship mapping.
*   **Response Model Compression:** Integrate Starlette's `GZipMiddleware` to automatically compress JSON responses exceeding 1KB, minimizing network payload overhead.
*   **Connection Keep-Alive:** Tune PostgreSQL `max_connections` and SQLAlchemy `pool_size` parameters in tandem to prevent exhausting database connection limits during traffic spikes.

---

## 6. Commercial License & Attribution Summary

### **The Agency Commercial End-User License Agreement (EULA)**

*   **Grant of Rights:** Purchasing or utilizing this digital product grants the licensee (Developer, Agency, or Freelancer) a perpetual, non-exclusive, worldwide license to use, modify, adapt, and incorporate this codebase into commercial client projects, SaaS products, and internal enterprise architectures.
*   **Restrictions:** Licensees are strictly prohibited from reselling, sublicensing, or redistributing this exact boilerplate as a standalone template, open-source competitor kit, or digital marketplace asset.
*   **No Warranty:** This software is provided "as is", without warranty of any kind, express or implied. The Agency Engineering Division disclaims all liability for direct or indirect damages resulting from the deployment of this architecture.

*© 2026 MicroCorp AI / The Agency Engineering Division. All Rights Reserved.*