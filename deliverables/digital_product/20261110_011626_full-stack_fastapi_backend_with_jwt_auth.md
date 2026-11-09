# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division**  
> *Production-Grade Turnkey Solution for Enterprise & Freelance Deployments*

---

## 1. # Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Architecture
**The ultimate boilerplate for high-performance, asynchronous REST APIs backed by robust JWT Authentication, SQLAlchemy 2.0, Alembic migrations, and containerized via Docker Compose.**

```
+-----------------------------------------------------------------+
CLIENT (React / Next.js / Mobile)                                 
  |                                                               
  v (HTTPS / Bearer Token)                                        
[ Nginx / Reverse Proxy ]                                         
  |                                                               
  v                                                               
[ FastAPI Application Container (Uvicorn Workers) ]               
  |-- Dependency Injection (Auth, DB Session)                     
  |-- Pydantic v2 Validation                                      
  |-- SQLAlchemy 2.0 Async ORM                                    
  |                                                               
  +---> [ PostgreSQL 15 Container ] (Persistent Volume)           
  +---> [ Redis Container ] (Rate Limiting / Caching)             
+-----------------------------------------------------------------+
```

### 💰 Commercial Value Proposition
Stop wasting 40+ hours configuring boilerplate architecture, security dependencies, and container orchestration for every new client project. This turnkey solution provides an enterprise-grade backend foundation that is secure, scalable, and immediately deployable.

* **Time-to-Market:** Cut initial backend setup time from days to minutes.
* **Security First:** Implements industry-standard OAuth2 with Password (and hashing), JWT access/refresh token rotation, CORS policies, and secure password hashing via `passlib[bcrypt]`.
* **Developer Experience:** Fully typed with Python 3.11+, Pydantic v2 data validation, interactive Swagger/ReDoc documentation, and automated database migrations.
* **Production Ready:** Pre-configured with multi-stage Dockerfiles, health checks, environment separation, and robust error handling.

---

## 2. ## Quick Start & Core Concepts

### System Architecture & Technology Matrix

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async REST API framework |
| **Runtime** | Python | `3.11-slim` | Modern, typed execution environment |
| **Database ORM** | SQLAlchemy | `2.0+` | Asynchronous data mapping and query generation |
| **Migrations** | Alembic | `1.13+` | Database schema version control |
| **Database** | PostgreSQL | `15-alpine` | Relational data store |
| **Cache/Queue** | Redis | `7-alpine` | Token blacklisting, rate limiting, caching |
| **Containerization** | Docker & Compose | `3.8+` | Isolated, reproducible deployment environments |

### 5-Minute Setup Guide

#### 1. Clone & Configure Environment
```bash
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate
cp .env.example .env
```

#### 2. Configure `.env`
Ensure your local environment variables are set correctly:
```env
PROJECT_NAME="MicroCorp API"
POSTGRES_USER=postgres
POSTGRES_PASSWORD=supersecretpassword
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=microcorp_dev
SECRET_KEY=generate_a_secure_random_key_here_using_openssl_rand_hex_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### 3. Spin Up via Docker Compose
```bash
docker compose up --build -d
```

#### 4. Verify Installation
* **API Documentation (Swagger):** `http://localhost:8000/docs`
* **Alternative Docs (ReDoc):** `http://localhost:8000/redoc`
* **Health Check Endpoint:** `http://localhost:8000/api/v1/health`

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```
app/
├── alembic/                  # Database migration versions
├── core/                     # Application configuration & security
│   ├── __init__.py
│   ├── config.py             # Pydantic BaseSettings
│   ├── database.py           # Async SQLAlchemy session setup
│   └── security.py           # JWT encoding/decoding & hashing
├── models/                   # SQLAlchemy ORM Models
│   └── user.py
├── schemas/                  # Pydantic validation schemas
│   └── user.py
├── api/                      # API Routers (v1)
│   ├── v1/
│   │   ├── api.py            # Router aggregator
│   │   └── endpoints/
│   │       ├── auth.py
│   │       └── users.py
│   └── deps.py               # FastAPI Dependencies (get_db, get_current_user)
├── main.py                   # FastAPI Application Entrypoint
├── Dockerfile                # Multi-stage production container
└── docker-compose.yml        # Orchestration manifest
```

---

### Core Implementation Files

#### 1. `app/core/config.py` - Configuration Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    
    @property
    SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
```

#### 2. `app/core/database.py` - Async Database Session Setup
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    future=True,
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

async def get_db() -> AsyncSession:
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

#### 3. `app/models/user.py` - SQLAlchemy 2.0 ORM Model
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
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
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### 4. `app/core/security.py` - JWT Token Management & Hashing
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

def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

#### 5. `app/api/deps.py` - Authentication Dependencies
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
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

#### 6. `app/main.py` - FastAPI Application Entrypoint
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
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
    allow_origins=["*"],  # Configure strictly for production clients
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/api/v1/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

#### 7. `Dockerfile` - Multi-Stage Production Build
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

# Stage 2: Final Runtime Image
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

#### 8. `docker-compose.yml` - Infrastructure Manifest
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
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

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_SERVER=db
      - POSTGRES_PORT=5432
      - POSTGRES_DB=${POSTGRES_DB}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails in Production | Correct Enterprise Approach |
| :--- | :--- | :--- |
| **Synchronous Database Drivers (`psycopg2`)** | Blocks the main event loop under high concurrency, defeating FastAPI's async speed advantages. | Always use asynchronous drivers like `asyncpg` with SQLAlchemy 2.0 (`create_async_engine`). |
| **Hardcoding Environment Secrets** | Exposes credentials in version control, leading to immediate security breaches. | Use Pydantic's `BaseSettings` to enforce environment variable ingestion via `.env` or orchestrator secrets. |
| **Session Leaks on Exceptions** | Database sessions remain open during unhandled exceptions, causing connection pool exhaustion. | Use dependency injection with context managers (`async with` / `yield`) and explicit try/except/rollback blocks. |
| **Infinite JWT Lifespans** | Compromised access tokens remain valid indefinitely, exposing user accounts. | Implement short-lived Access Tokens (15–30 mins) paired with rotating Refresh Tokens stored securely. |
| **Missing DB Migration Strategy** | Manually running raw SQL scripts creates drift between dev, staging, and production environments. | Use Alembic for automated, version-controlled schema migrations integrated into CI/CD pipelines. |

---

## 5. ## Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** In production, do not rely on `--reload`. Run multiple workers matching your CPU cores (`--workers 4` or use Gunicorn with Uvicorn worker class).
2. **Connection Pooling Optimization:** Tune SQLAlchemy pool size parameters (`pool_size=20`, `max_overflow=10`) based on your PostgreSQL database tier limits.
3. **Response Compression:** Add `GZipMiddleware` to your FastAPI application to automatically compress large JSON payloads over 1KB:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```
4. **Database Indexing:** Ensure foreign keys and frequently queried fields (such as `email` or search columns) have explicit indexes defined on your SQLAlchemy models (`index=True`).
5. **Query Load Optimization:** Leverage SQLAlchemy 2.0 `selectinload` or `joinedload` options when handling relationship queries to prevent N+1 query execution bottlenecks.

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MACC-v1.0)
* **Grant of Rights:** Purchasing or acquiring this turnkey codebase grants the licensee (developer, agency, or enterprise) a perpetual, non-exclusive, worldwide license to use, modify, copy, and deploy this software for commercial client projects, SaaS products, and internal applications.
* **Restrictions:** Licensees may not resell, sub-license, or redistribute this raw boilerplate as a competing backend template or commercial code-kit on digital marketplaces (e.g., Gumroad, GitHub, Envato) without explicit written authorization from MicroCorp AI.
* **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied. The Agency and MicroCorp AI shall not be held liable for any claim, damages, or liability arising from the deployment of this code in production environments.

---
*Built with precision by Backend Architect 🏗️ — The Agency Engineering Division.*