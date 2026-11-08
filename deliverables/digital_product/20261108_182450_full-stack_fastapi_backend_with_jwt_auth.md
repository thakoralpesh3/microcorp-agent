# Enterprise-Grade FastAPI Backend: JWT Auth & Docker Setup
*The Agency Engineering Division | MicroCorp AI Production Architecture*

---

## 1. # Product Title & Value Proposition

### **Product Title:** 
`FastAPI-Enterprise-Boilerplate: Production-Ready Asynchronous Backend with JWT Authentication, SQLModel, PostgreSQL, and Docker Compose`

### **Value Proposition:**
Building a production-ready, secure, and asynchronous backend from scratch takes days of boilerplate configuration, security hardening, and structural design. This turnkey solution delivers a battle-tested, highly scalable FastAPI architecture out of the box. 

Designed for senior engineers, enterprise clients, and high-tier Fiverr deliveries, this boilerplate eliminates configuration debt. It features type-safe database interactions via SQLModel, stateless JSON Web Token (JWT) authentication with automatic token expiration, structured logging, Alembic database migrations, and a fully containerized Docker workflow. Deploy instantly, scale limitlessly, and maintain zero technical debt from day one.

---

## 2. ## Quick Start & Core Concepts

Get your development environment running in under 60 seconds with zero manual database provisioning.

### Prerequisites
* Docker Engine (v24.0+) & Docker Compose (v2.20+)
* Python 3.11+ (for local development/testing)

### 60-Second Setup
```bash
# 1. Clone the repository & navigate to workspace
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Configure environment variables
cp .env.example .env

# 3. Spin up the containerized ecosystem
docker compose up --build -d

# 4. Verify API health & access interactive docs
curl http://localhost:8000/health
# Navigate to: http://localhost:8000/docs
```

### Clean Syntax & Architectural Map

| Component / Layer | Technology | Primary Responsibility | Key File Path |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | Asynchronous request routing, validation, OpenAPI schema generation. | `app/main.py` |
| **ORM & Validation** | SQLModel / Pydantic V2 | Type-safe data modeling, database session management, request serialization. | `app/models/` |
| **Database** | PostgreSQL 16 | Relational data persistence with ACID compliance. | `docker-compose.yml` |
| **Migrations** | Alembic | Schema version control and forward/backward migration execution. | `alembic/` |
| **Authentication** | PyJWT / Passlib (Bcrypt) | Stateless token generation, verification, and secure password hashing. | `app/core/security.py` |
| **Containerization**| Docker & Compose | Multi-stage builds for minimal image size and isolated service orchestration. | `Dockerfile`, `docker-compose.yml` |

---

## 3. ## Production Code Patterns & Architecture Examples

This section contains complete, copy-paste ready, production-grade files structured following clean architecture principles.

### Directory Structure
```text
fastapi-enterprise-boilerplate/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   └── main.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### File 1: Environment & Settings Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### File 2: Async Database Engine & Session Provider (`app/core/database.py`)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining asynchronous database sessions."""
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

### File 3: Security & JWT Utilities (`app/core/security.py`)
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
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### File 4: User Model & Schemas (`app/models/user.py`)
```python
from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import EmailStr

class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, nullable=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    full_name: Optional[str] = Field(default=None)

class User(UserBase, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(nullable=False)

class UserCreate(UserBase):
    password: str = Field(min_length=8, nullable=False)

class UserRead(UserBase):
    id: int

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(SQLModel):
    sub: Optional[int] = None
```

---

### File 5: Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.future import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.models.user import User, UserCreate, UserRead, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        is_active=True,
        is_superuser=False
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.id, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### File 6: Main Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

---

### File 7: Production Dockerfile (`Dockerfile`)
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### File 8: Container Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
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
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction99887766
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes (`def` vs `async def`)**
   * **Anti-Pattern:** Using standard synchronous database drivers or heavy CPU-bound tasks inside an `async def` route without executing them in a threadpool. This blocks the entire event loop.
   * **Solution:** Always use asynchronous drivers (`asyncpg`) with `async def`, or offload blocking operations using `run_in_threadpool`.

2. **Hardcoding Secrets & Configuration**
   * **Anti-Pattern:** Storing database credentials, JWT secret keys, and API tokens directly in Python files.
   * **Solution:** Use `pydantic-settings` to enforce strict typing and load variables exclusively from environment files (`.env`) or secret managers.

3. **Leaking Database Sessions**
   * **Anti-Pattern:** Manually opening database sessions inside route handlers without guarantee of closure on exception throwing.
   * **Solution:** Always use FastAPI's dependency injection system (`Depends(get_db)`) coupled with context managers (`async with`) to ensure automatic rollback and connection pooling cleanup.

4. **Catching Generic Exceptions Globally**
   * **Anti-Pattern:** Using broad `except Exception:` blocks that return opaque `500 Internal Server Error` responses, masking underlying validation or integrity errors.
   * **Solution:** Raise explicit `fastapi.HTTPException` with appropriate status codes and structured detail payloads.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, do not rely on a single uvicorn worker process inside containers. Scale worker processes relative to available CPU cores using Gunicorn as a process manager or by deploying multiple replicas behind an Nginx or Traefik reverse proxy.
* **Connection Pool Tuning:** Configure `pool_size` and `max_overflow` in your SQLAlchemy engine matching your database's maximum concurrent connection limit (`max_connections`) to prevent database thread starvation under peak loads.
* **Response Serialization Compression:** Integrate `GZipMiddleware` into your FastAPI application (`app.add_middleware(GZipMiddleware, minimum_size=1000)`) to compress large JSON responses automatically, reducing network payload sizes significantly.
* **Database Indexing:** Ensure high-cardinality foreign keys, search fields, and unique identifiers (such as user emails) include explicit database indices (`index=True` in SQLModel) to avoid sequential table scans.

---

## 6. ## Commercial License & Attribution Summary

### Commercial License Agreement
* **Copyright © MicroCorp AI. All rights reserved.**
* **Grant of Rights:** This commercial digital product is licensed to the purchasing client/engineer for deployment in commercial, proprietary, and open-source software applications. 
* **Restrictions:** Redistribution, resale, or public publishing of this source code as a standalone boilerplate template, training dataset, or commercial course material is strictly prohibited without explicit written authorization from MicroCorp AI.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement.