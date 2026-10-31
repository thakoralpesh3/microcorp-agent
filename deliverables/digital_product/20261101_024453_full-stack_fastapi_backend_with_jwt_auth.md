# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*  
> **Product Code:** MC-TURKEY-FASTAPI-042  
> **Target Audience:** Enterprise Clients, Senior Engineers, and Freelance Deliverables

---

## 1. # Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Boilerplate
Stop wasting 40+ hours setting up boilerplate authentication, database migrations, and container orchestration for every new client project. This is a battle-tested, highly optimized **Full-Stack FastAPI Backend** featuring asynchronous SQLAlchemy 2.0, robust JWT-based authentication (Access & Refresh tokens), Alembic migrations, and a fully configured multi-stage Docker environment.

### 💰 Commercial Value Proposition
* **Time-to-Market:** Cut your backend setup phase from 3 days to 15 minutes.
* **Security First:** Implements stateless JWT authentication with secure password hashing via `passlib[bcrypt]` and strict CORS middleware.
* **Developer Experience (DX):** Fully typed with Python 3.11+, auto-generated interactive OpenAPI/Swagger documentation, and an intuitive project layout.
* **Production Scalability:** Engineered with connection pooling, asynchronous database sessions, and stateless container design ready for AWS ECS, Google Cloud Run, or DigitalOcean App Platform.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview
```
[ Client / Frontend ] 
       │ (HTTPS / Bearer Token)
       ▼
[ Nginx / Reverse Proxy ] (Optional)
       │
       ▼
[ FastAPI Application (ASGI / Uvicorn) ]
       ├── /api/v1/auth    (JWT Login, Refresh, Register)
       ├── /api/v1/users   (User Management & Profiles)
       └── /docs           (Interactive OpenAPI Docs)
       │
       ├── Async SQLAlchemy 2.0 ORM
       │
       ▼
[ PostgreSQL 15 Database ]
```

### Clean Syntax & Component Reference Table

| Component | Technology | Purpose / Configuration |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance asynchronous API routing and validation. |
| **ASGI Server** | Uvicorn | Production-grade ASGI application server worker runner. |
| **Database Driver** | Asyncpg + SQLAlchemy 2.0 | Non-blocking database operations and modern ORM querying. |
| **Migrations** | Alembic | Version-controlled database schema migrations. |
| **Authentication** | `python-jose` + `passlib` | JWT encoding/decryption and secure password hashing. |
| **Environment Management** | Pydantic-Settings (`pydantic-settings`) | Strongly typed environment variable validation. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds for minimal image size and instant orchestration. |

---

## 3. ## Production Code Patterns & Architecture Examples

This section contains copy-paste ready, production-grade code structured using a modular service-repository pattern.

### Project Directory Structure
```text
fastapi-production-boilerplate/
├── alembic/
│   └── versions/
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

### Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # SECURITY
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # DATABASE
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    def model_post_init(self, __context) -> None:
        object.__setattr__(
            self,
            "DATABASE_URL",
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

### Database Session (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

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

### Security Utilities (`app/core/security.py`)
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
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
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
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
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
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

---

### Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(
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
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

---

### FastAPI Main Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
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

### Multi-Stage Dockerfile (`Dockerfile`)
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

# Stage 2: Runtime Image
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

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
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

  api:
    build: .
    container_name: fastapi_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=FastAPI Enterprise Backend
      - SECRET_KEY=super-secret-production-jwt-key-change-me
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=production_db
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Synchronous Database Drivers with Async FastAPI:** Using standard `psycopg2` inside an `async def` path operation blocks the entire event loop. Always use `asyncpg` combined with SQLAlchemy's asynchronous session management.
2. ❌ **Hardcoding Secrets in Code:** Storing database passwords or JWT signing keys inside source control. Always utilize Pydantic-Settings (`pydantic-settings`) and enforce environment variables.
3. ❌ **Not Committing or Closing Sessions Manually:** Forgetting to handle session context correctly leads to connection leaks. Use context managers (`async with`) and dependency injection generators (`yield`) to automatically handle cleanup.
4. ❌ **Infinite Circular Schema Imports:** Defining models and Pydantic schemas in a way that causes circular imports (`app.models` importing `app.schemas` importing `app.models`). Decouple your business logic and enforce strict layer separation.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a load balancer (like Nginx or AWS ALB), run multiple worker processes rather than threads:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Connection Pooling tuning:** Tune SQLAlchemy engine arguments `pool_size` and `max_overflow` based on your database tier limitations.
* **Gzip Compression:** Add FastAPI's built-in Gzip middleware for payloads larger than 1KB to drastically decrease bandwidth usage over public networks:
  ```python
  from fastapi.middleware.gzip import GzipMiddleware
  app.add_middleware(GzipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure frequently queried columns (such as foreign keys, user emails, and lookup tokens) have explicit database indexes (`index=True`).

---

## 6. ## Commercial License & Attribution Summary

* **License Type:** Commercial Client Delivery License (Perpetual, Royalty-Free)
* **Usage Rights:** You are permitted to modify, rebrand, distribute, and embed this codebase into any client deliverable, commercial SaaS product, or internal system.
* **Attribution:** Attribution to **The Agency Engineering Division** is appreciated but not legally required for commercial delivery.
* **Warranty Disclaimer:** Provided *as-is* without warranty of any kind. Engineering teams assume full responsibility for production security configurations, HTTPS termination, and final secret rotation.