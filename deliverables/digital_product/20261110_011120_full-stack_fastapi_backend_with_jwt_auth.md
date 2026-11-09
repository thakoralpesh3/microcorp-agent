# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise-Grade FastAPI Backend Boilerplate
*Secure, Scalable, and Production-Ready Asynchronous Python Architecture with Complete JWT Authentication and Multi-Stage Dockerization.*

#### Value Proposition
Building a modern, secure, and production-ready backend from scratch wastes weeks of valuable engineering bandwidth. This enterprise-grade boilerplate provides a battle-tested foundation combining **FastAPI**, **SQLAlchemy 2.0 (Async)**, **Pydantic v2**, **JWT Authentication (OAuth2 with Password Flow)**, and **Docker Compose orchestration**. 

Designed for high-throughput microservices and SaaS backends, this turnkey solution eliminates boilerplate setup, enforces industry-best security paradigms, and guarantees strict type safety.

```
+------------------------------------------------------------+
                 CLIENT REQUEST (React / Mobile)             
+------------------------------------------------------------+
                              │
                              ▼
+------------------------------------------------------------+
                NGINX / REVERSE PROXY (Optional)             
+------------------------------------------------------------+
                              │
                              ▼
+------------------------------------------------------------+
            FASTAPI ASYNCHRONOUS APP CONTAINER               
  ┌────────────────────────────────────────────────────────┐ 
  │ Uvicorn Worker ──> FastAPI Router ──> Pydantic v2      │ 
  │                           │                            │ 
  │                           ▼                            │ 
  │               SQLAlchemy 2.0 (Async ORM)               │ 
  └────────────────────────────────────────────────────────┘ 
+------------------------------------------------------------+
                              │
                              ▼
+------------------------------------------------------------+
                 POSTGRESQL 16+ DATABASE                     
+------------------------------------------------------------+
```

---

## 2. Quick Start & Core Concepts

### System Requirements
* **Python** >= 3.11+
* **Docker** & **Docker Compose** (v2.20+)

### Clean Syntax Table: Key Architectural Components

| Component | Technology | Purpose | Key Benefit |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI (0.110+) | Asynchronous HTTP handling & OpenAPI doc generation | High I/O performance via ASGI (`Uvicorn`) |
| **Validation** | Pydantic v2 | Data parsing, serialization, and settings management | Rust-powered speed with strict runtime type checks |
| **Database ORM** | SQLAlchemy 2.0 | Asynchronous database interactions (`asyncpg`) | Non-blocking queries under heavy concurrent loads |
| **Auth Engine** | PyJWT + Passlib | Secure token generation, verification, and password hashing | Stateless session management using cryptographic signatures |
| **Containerization**| Docker / Compose | Multi-stage, isolated environments for app and database | Environment parity across dev, staging, and production |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```
fastapi-enterprise-boilerplate/
├── alembic/                      # Database migrations
├── app/
│   ├── api/                      # API Routers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/        # Auth, Users, Health
│   │   │   └── router.py         # Router aggregation
│   ├── core/                     # Configurations, Security, DB
│   │   ├── config.py             # Pydantic BaseSettings
│   │   ├── database.py           # Async sessionmaker
│   │   └── security.py           # JWT & Password hashing
│   ├── models/                   # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic request/response models
│   ├── services/                 # Business logic layer
│   └── main.py                   # FastAPI Application factory
├── .env.example                  # Environment variable template
├── Dockerfile                    # Multi-stage production image
├── docker-compose.yml            # Local orchestration
└── requirements.txt              # Pinned dependencies
```

---

### Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

---

### Asynchronous Database Engine (`app/core/database.py`)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False, future=True)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
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

### Security & JWT Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

---

### User SQLAlchemy Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

### Pydantic Schemas (`app/schemas/user.py`)
```python
import uuid
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserResponse(UserBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str = None
```

---

### Authentication & Dependency Injection (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }
```

---

### Main Application Factory (`app/main.py`)
```python
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    application.include_router(api_router, prefix=settings.API_V1_STR)
    
    return application

app = get_application()

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### Docker Configuration

#### Multi-Stage Production Dockerfile (`Dockerfile`)
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Orchestration Setup (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Synchronous and Asynchronous ORM Calls:**
   * **The Gotcha:** Using standard `Session` or blocking database calls inside `async def` path operations blocks the entire Uvicorn event loop thread.
   * **The Fix:** Always use `AsyncSession` alongside `asyncpg` and asynchronous SQLAlchemy query execution primitives (`await db.execute(...)`).
2. ❌ **Hardcoding Configuration Settings:**
   * **The Gotcha:** Storing secrets, database URIs, or environment URLs directly in code modules.
   * **The Fix:** Utilize Pydantic's `BaseSettings` pattern to enforce validation and type checking via environment variables (`.env`).
3. ❌ **Catching Base Exceptions Blindly:**
   * **The Gotcha:** Using `except Exception:` without rolling back the active database session leaves transactions dangling in an aborted state.
   * **The Fix:** Always structure session dependency yields with explicit try/except/rollback blocks as shown in `app/core/database.py`.
4. ❌ **Neglecting Multi-Stage Docker Builds:**
   * **The Gotcha:** Copying compiler toolchains (`build-essential`) into production runtime containers, leading to bloated images and expanded security attack surfaces.
   * **The Fix:** Separate the dependency builder stage from the lean execution runtime image.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container setups, run multiple worker processes matching your CPU core density via `--workers N` or manage instances with process managers like Gunicorn.
* **Connection Pooling:** Configure SQLAlchemy's connection pool size (`pool_size` and `max_overflow`) depending on your database hosting limits and concurrency requirements.
* **Response Compression:** Integrate `GZipMiddleware` into FastAPI for payloads exceeding 1000 bytes to minimize network bandwidth consumption.
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (such as user email strings) feature explicit database indexes.

---

## 6. Commercial License & Attribution Summary

* **License:** MIT Commercial-Ready License
* **Usage Rights:** Grants perpetual, non-exclusive usage across client projects, internal enterprise architecture, and commercial SaaS applications.
* **Attribution:** Maintained by **The Agency Engineering Division**. No mandatory runtime attribution required in client-facing UI products.