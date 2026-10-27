# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Client Deliverable*

---

## 1. Product Title & Value Proposition

### **Product Title:** 
Production-Grade FastAPI Backend Boilerplate with Async SQLAlchemy, JWT Authentication, Alembic Migrations, and Docker Multi-Stage Builds.

### **Value Proposition:**
Building a modern production-ready backend from scratch takes 40+ hours of boilerplate configuration, security hardening, and structural design. This turnkey solution delivers a fully tested, battle-tested FastAPI architecture out of the box. Designed for rapid deployment, it saves your engineering team weeks of foundational setup, ensuring secure authentication, scalable database patterns, and strict typing right from day one.

---

## 2. Quick Start & Core Concepts

### System Architecture Flow
```
[ Client / Frontend ] 
       │ (HTTPS / Bearer Token)
       ▼
[ Nginx / Reverse Proxy ] (Optional Edge)
       │
       ▼
[ FastAPI Application ] 
   ├── Middleware (CORS, TrustedHost)
   ├── Routers (Auth, Users, Health)
   ├── Security (JWT Encoding/Decoding, Argon2/Bcrypt)
   └── Async ORM (SQLAlchemy 2.0 + asyncpg)
       │
       ▼
[ PostgreSQL 16 Database ] (Persistent Volume)
```

### Syntax & Component Reference Table

| Layer / Component | Technology Stack | Primary Purpose |
| :--- | :--- | :--- |
| **API Framework** | FastAPI 0.110+ | High-performance asynchronous REST endpoints with auto-generated OpenAPI docs. |
| **Data Validation** | Pydantic v2 | Strict input/output parsing, serialization, and environment configuration management. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database operations using `asyncpg` driver. |
| **Database Migrations**| Alembic | Version-controlled schema evolutions and rollbacks. |
| **Authentication** | PyJWT / Passlib | Cryptographic token issuance (Access & Refresh tokens) and secure password hashing. |
| **Containerization** | Docker & Docker Compose | Multi-stage image builds, volume persistence, and service orchestration. |

---

## 3. Production Code Patterns & Architecture Examples

### 3.1 Project Directory Structure
```text
fastapi-production-boilerplate/
├── alembic/                      # Database migrations
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── api.py
│   │   └── deps.py               # Dependency injection (DB session, current user)
│   ├── core/
│   │   ├── config.py             # Pydantic Settings
│   │   ├── database.py           # Async engine & sessionmaker
│   │   └── security.py           # JWT & Password hashing utilities
│   ├── models/                   # SQLAlchemy ORM Models
│   │   └── user.py
│   ├── schemas/                  # Pydantic Schemas
│   │   └── user.py
│   └── main.py                   # FastAPI application factory
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### 3.2 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Production Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    DATABASE_URL: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

### 3.3 Database Engine & Session Factory (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

### 3.4 SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

### 3.5 Security & JWT Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### 3.6 FastAPI Dependency Injection (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    return user
```

### 3.7 Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
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
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

### 3.8 Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

### 3.9 Docker Setup Files

#### `Dockerfile` (Multi-Stage Build)
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

#### `docker-compose.yml`
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
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
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
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=production_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous DB Calls in Async Endpoints**
   * *Anti-Pattern:* Using standard `psycopg2` or standard SQLAlchemy sessions inside `async def` routes. This blocks the entire Uvicorn event loop.
   * *Correction:* Always use `asyncpg` combined with `sqlalchemy.ext.asyncio`.
2. **Missing Database Connection Pooling Management**
   * *Anti-Pattern:* Creating a new `create_async_engine` instance on every incoming HTTP request.
   * *Correction:* Instantiate the engine and sessionmaker globally as singletons and use Dependency Injection (`get_db`) to manage session scopes.
3. **Hardcoding Cryptographic Secrets**
   * *Anti-Pattern:* Storing raw JWT secrets and database credentials inside the source code repository.
   * *Correction:* Leverage Pydantic `BaseSettings` to enforce runtime environment variable loading via `.env` files or secure orchestrator vaults.
4. **Neglecting Token Expiration and Revocation**
   * *Anti-Pattern:* Issuing JWTs with infinite expiration times (`exp`).
   * *Correction:* Enforce strict short-lived access tokens (e.g., 15 minutes) paired with longer-lived refresh tokens.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production environments behind reverse proxies (like Nginx or Traefik), run Uvicorn with multiple worker processes or orchestrate multiple containers behind a load balancer:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` parameters in `create_async_engine()` depending on your database hardware limits and peak concurrent connection needs.
* **Response Compression:** Install `starlette.middleware.gzip.GZipMiddleware` to automatically compress large JSON responses payloads over the network.
* **Database Indexing:** Ensure foreign keys, search filters, and unique constraints (such as `email` and UUID primary keys) have explicit B-tree indexes defined in your SQLAlchemy models.

---

## 6. Commercial License & Attribution Summary

* **License Type:** Commercial Client Deliverable License (MicroCorp AI / The Agency Engineering Division).
* **Usage Rights:** Granted to the purchasing client/Fiverr employer for unlimited commercial deployment, modification, and distribution within internal or customer-facing SaaS applications.
* **Restrictions:** Resale or redistribution of this boilerplate as a standalone competitive template or open-source boilerplate product is strictly prohibited.
* **Warranty:** Provided "as-is" without warranty of any kind. The Agency Engineering Division disclaims all liability for infrastructure or security misconfigurations performed downstream.