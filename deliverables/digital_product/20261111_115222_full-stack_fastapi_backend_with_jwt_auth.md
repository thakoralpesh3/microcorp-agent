# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — Enterprise Backend Architecture  
> *Production-grade, secure, and horizontally scalable boilerplate designed for rapid client delivery.*

---

## 1. Product Title & Value Proposition

### Title
**FastAPI Production-Ready Engine: JWT Auth & Dockerized PostgreSQL Architecture**

### Value Proposition
Stop wasting 40+ hours writing boilerplate, configuring security headers, wiring asynchronous database drivers, and debugging Docker multi-stage builds. This turnkey backend solution gives you an enterprise-grade foundation out of the box. Featuring robust OAuth2 with JWT password flow, SQLAlchemy 2.0 asynchronous ORM, Alembic database migrations, Pydantic v2 data validation, and a bulletproof Docker Compose orchestration setup, this architecture is built for scale, performance, and immediate client handoff.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
```
[ Client / Frontend ] 
       │
       ▼ (HTTPS / JSON)
[ Nginx Reverse Proxy ] (Optional Edge)
       │
       ▼
[ FastAPI Application Container ]
       ├── /api/v1/auth (JWT Bearer Token Issuance)
       ├── /api/v1/users (User Management & RBAC)
       └── Dependency Injection (Async Session, Auth Guards)
       │
       ▼ (Asyncpg TCP)
[ PostgreSQL 16 Alpine Container ] (Persistent Volume Storage)
```

### Core Technologies & Syntax Reference

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance asynchronous REST API routing and OpenAPI generation. |
| **Data Validation** | Pydantic | `2.6+` | Runtime type checking, settings management, and serialization schemas. |
| **Database ORM** | SQLAlchemy | `2.0+` | Asynchronous database interactions using the modern Core/ORM hybrid style. |
| **Migrations** | Alembic | `1.13+` | Programmatic schema version control and database evolution tracking. |
| **Authentication** | PyJWT & Passlib | `2.8+ / 1.7+` | Cryptographic token generation (HS256) and Bcrypt password hashing. |
| **Containerization** | Docker & Compose | `24+` | Multi-container isolated development and production deployments. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Tree
```text
fastapi-enterprise-engine/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── crud/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           └── users.py
│   └── core/
│       ├── __init__.py
│       ├── security.py
│       └── config.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### `app/core/config.py` (Environment & Settings)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    ASYNC_DATABASE_URI(str) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
```

---

### `app/database.py` (Async SQLAlchemy Engine & Session)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
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

---

### `app/models/user.py` (SQLAlchemy 2.0 Model)
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

---

### `app/core/security.py` (JWT & Hashing Utilities)
```python
from datetime import datetime, timedelta, timezone
import jwt
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
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### `app/api/deps.py` (Authentication Dependencies)
```python
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.database import get_db
from app.models.user import User
from sqlalchemy import select

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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### `app/api/v1/endpoints/auth.py` (Authentication Endpoint)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from pydantic import BaseModel

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### `Dockerfile` (Optimized Multi-Stage Production Build)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.11-slim-bookworm

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

### `docker-compose.yml` (Local & Staging Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: postgres_password
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

  api:
    build: .
    container_name: fastapi_api
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=postgres_password
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous Operations in Asynchronous Paths:**
   * *Anti-Pattern:* Using standard `psycopg2` or blocking libraries (like standard `requests` or blocking file IO) inside `async def` path operations. This blocks the main event loop and freezes the entire server thread.
   * *Correction:* Always use asynchronous drivers (`asyncpg`, `httpx`) inside async endpoints. If blocking code is unavoidable, offload it using `run_in_threadpool`.

2. **Open Database Sessions on Request Failure:**
   * *Anti-Pattern:* Manually opening sessions without proper `try/finally` blocks or generator yielding, leading to connection pool exhaustion.
   * *Correction:* Leverage FastAPI dependency injection with context managers to guarantee clean session closure and automatic transaction rollback upon exception.

3. **Hardcoding Secrets in Configuration Files:**
   * *Anti-Pattern:* Storing JWT keys, database credentials, and third-party API keys directly within `config.py` defaults.
   * *Correction:* Use Pydantic-settings coupled with a strict `.env` file structure. Never commit `.env` files into version control.

4. **Ignoring Alembic Migration Reversibility:**
   * *Anti-Pattern:* Writing migration files containing only `upgrade()` blocks while leaving `downgrade()` blank or raising NotImplementedError.
   * *Correction:* Ensure every schema modification includes a robust, fully tested reversal routine to maintain database state consistency.

---

## 5. Performance & Optimization Tips

* **Database Connection Pooling:** Fine-tune `pool_size` and `max_overflow` in your SQLAlchemy engine configuration based on your server's available vCPUs and expected concurrency thresholds.
* **Uvicorn Worker Scaling:** In production container deployments, run Uvicorn behind a process manager like Gunicorn or use multiple worker processes managed via Docker replica services or Kubernetes pods behind an Nginx load balancer.
* **Response Serialization Tuning:** For heavy JSON payloads involving large database lists, use Pydantic's `model_dump()` optimizations or leverage ultra-fast serialization bridges like `orjson`.
* **Database Indexing Strategy:** Ensure high-cardinality lookup columns (such as `email`, foreign keys, and status flags queried frequently in filters) have explicit indexes applied via SQLAlchemy model definitions.

---

## 6. Commercial License & Attribution Summary

### Commercial Distribution License
* **Grant of Rights:** MicroCorp AI grants the purchasing client an irrevocable, perpetual, non-exclusive commercial license to use, modify, adapt, and deploy this codebase for internal business systems, SaaS platforms, and client-facing commercial applications.
* **Restrictions:** Redistribution of this raw boilerplate as a competing commercial template, code pack, or digital asset library is strictly prohibited.
* **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. The Agency Engineering Division disclaims liability for any direct or indirect damages resulting from improper configuration or deployment of production infrastructure.

---
*Architected and certified by The Agency Engineering Division.*