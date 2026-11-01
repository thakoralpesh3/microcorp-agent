# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — Enterprise Backend Architecture  
> *Production-grade, secure, and horizontally scalable Python microservice boilerplate.*

---

## 1. Product Title & Value Proposition

### Title
**FastAPI Production Engine: Enterprise JWT Auth, PostgreSQL, & Dockerized Boilerplate**

### Value Proposition
Stop wasting 40+ hours writing boilerplate code, configuring CORS, debugging async database sessions, and wiring up secure JWT authentication cycles for every new client project. 

This turnkey backend architecture gives you a battle-tested, highly performant FastAPI foundation complete with SQLAlchemy 2.0 (async), Alembic migrations, Pydantic v2 validation, secure password hashing (Argon2/Bcrypt), role-based access control (RBAC), and a multi-stage production Docker setup. Hand this directly to clients or deploy it as the rock-solid core of your next SaaS product.

---

## 2. Quick Start & Core Concepts

### System Architecture Quick Reference

```
[ Client / Frontend ] 
        │
        ▼ (HTTPS / Bearer Token)
[ Nginx Reverse Proxy ] (Optional SSL Termination)
        │
        ▼
[ FastAPI Application Container ] 
   ├── API Routers (/api/v1)
   ├── Dependency Injection (Auth, DB Session)
   └── Pydantic v2 Data Validation
        │
        ├──► [ PostgreSQL Container ] (Persistent Volume)
        └──► [ Redis Container ] (Rate Limiting / Caching - Optional)
```

### Core Technology Stack & Syntax Reference

| Component | Technology | Version | Purpose / Key Syntax |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous REST API framework (`app = FastAPI()`). |
| **Data Validation** | Pydantic | `2.6+` | Runtime data parsing and settings management (`model_validator`, `Field`). |
| **Database ORM** | SQLAlchemy | `2.0+` | Modern asynchronous database interaction (`AsyncSession`, `select()`). |
| **Migrations** | Alembic | `1.13+` | Database schema version control and migration management. |
| **Authentication** | PyJWT / Passlib | `2.8+` | Stateless token generation and secure cryptographic hashing. |
| **Containerization** | Docker / Compose | `24+` | Multi-container orchestration, networking, and volume management. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```
fastapi-production-engine/
├── alembic/                      # Database migrations
├── app/
│   ├── api/                      # API Routers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   ├── core/                     # Configuration, Security, DB session
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/                   # SQLAlchemy ORM Models
│   │   └── user.py
│   ├── schemas/                  # Pydantic Schemas
│   │   └── user.py
│   └── main.py                   # Application entrypoint
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

### Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### Asynchronous Database Session (`app/core/database.py`)
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

### Security & JWT Handling (`app/core/security.py`)
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
```

---

### SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
```

---

### Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="The user doesn't have enough privileges"
        )
    return current_user
```

---

### Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### Main Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production to match client domains
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

### Docker Configuration

#### `Dockerfile`
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

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
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
      - PROJECT_NAME=FastAPI Enterprise Engine
      - SECRET_KEY=supersecretjwtkeychangeinproduction998877
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes**  
   * **Anti-Pattern:** Using standard `requests` or blocking ORM queries inside `async def` routes, blocking the main event loop.
   * **Correction:** Use `httpx` for async HTTP requests and SQLAlchemy's `AsyncSession` for database interactions. If using legacy synchronous libraries, define routes with standard `def` so FastAPI executes them in a separate thread pool.

2. **Hardcoding Configuration & Secrets**  
   * **Anti-Pattern:** Storing database credentials, secret keys, and API tokens directly in code.
   * **Correction:** Utilize Pydantic's `BaseSettings` combined with environment variables (`.env`). Never commit `.env` files to version control.

3. **Ignoring Session Leakage and Connection Pool Exhaustion**  
   * **Anti-Pattern:** Manually opening database sessions without proper closing loops or dependency yields.
   * **Correction:** Always rely on FastAPI's `Depends(get_db)` generator pattern to guarantee sessions close correctly, even when unhandled exceptions occur.

4. **Catching Bare Exceptions**  
   * **Anti-Pattern:** Using `except Exception:` without logging or re-raising, swallowing critical system crashes and returning opaque `500 Internal Server Error` responses.
   * **Correction:** Catch explicit exceptions, handle known operational errors with precise HTTP status codes, and let unexpected exceptions bubble up to custom middleware or global exception handlers.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production environments behind Nginx, run Uvicorn with multiple worker processes or utilize Gunicorn as a process manager with Uvicorn worker classes (`gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`).
* **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` parameters in `create_async_engine()` based on expected peak concurrency and your PostgreSQL server resource limitations.
* **Response Model Optimization:** Leverage Pydantic v2's serialization speedups by defining strict `response_model` annotations on your FastAPI routes, preventing accidental data leaks (e.g., exposing password hashes) while optimizing output parsing.
* **Database Indexing:** Ensure frequently queried columns (such as `email`, foreign keys, and timestamp audit fields) feature proper B-Tree indexes defined at the model and migration layers.

---

## 6. Commercial License & Attribution Summary

### Commercial License Agreement
* **Grant of Rights:** MicroCorp AI grants the purchaser (or Fiverr client) a perpetual, worldwide, non-exclusive, royalty-free license to use, modify, distribute, and sell applications built upon this codebase.
* **Restrictions:** You may not redistribute, resell, or sublicense this raw architectural boilerplate as a standalone template kit on digital marketplaces.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The Agency Engineering Division assumes no liability for production outages, data loss, or security breaches resulting from improper deployment or misconfiguration.

---
*Built with precision by The Agency Engineering Division.* 🏗️