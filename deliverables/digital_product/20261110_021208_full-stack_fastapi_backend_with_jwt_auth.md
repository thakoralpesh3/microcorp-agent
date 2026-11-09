# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Packet*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready JWT Auth & Dockerized PostgreSQL Architecture**

#### **Value Proposition**
Building secure, scalable, and high-performance asynchronous APIs from scratch takes weeks of boilerplate setup. This turnkey solution eliminates 80+ hours of foundational engineering. It provides a battle-tested, strictly typed, production-ready backend architecture combining **FastAPI**, **SQLAlchemy 2.0 (Async)**, **Pydantic v2**, **JWT Authentication (OAuth2 with Password Bearer)**, and a fully orchestrated **Docker Compose** environment. 

Designed for immediate deployment, this codebase guarantees type safety, automatic OpenAPI (Swagger) documentation, secure password hashing via `passlib[bcrypt]`, and robust database connection pooling out of the box.

---

## 2. ## Quick Start & Core Concepts

### System Requirements & Environment Matrix
* **Python**: `3.11+`
* **Database**: `PostgreSQL 15+`
* **Containerization**: `Docker & Docker Compose`

### Clean Syntax & Technology Map

| Layer | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI | High-performance asynchronous routing & automatic Swagger docs |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and settings management |
| **ORM & Database** | SQLAlchemy 2.0 (Async) | Non-blocking database queries and declarative models |
| **Migration Engine** | Alembic | Version-controlled database schema migrations |
| **Security / Auth** | python-jose & passlib | JWT creation/verification and secure bcrypt password hashing |
| **Infrastructure** | Docker Compose | Multi-container orchestration (API + PostgreSQL + Adminer) |

### 5-Minute Local Setup (Without Docker)

```bash
# 1. Clone and enter directory
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your local PostgreSQL credentials

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Instant Setup (With Docker Compose)

```bash
# Spin up PostgreSQL and FastAPI containers in detached mode
docker-compose up --build -d

# Verify logs
docker-compose logs -f api
```
Access the interactive API documentation at: `http://localhost:8000/docs`

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-jwt-docker-boilerplate/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application entrypoint & middleware
│   ├── config.py            # Pydantic BaseSettings configuration
│   ├── database.py          # Async sessionmaker & engine setup
│   ├── models/              # SQLAlchemy ORM Models
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/             # Pydantic Data Transfer Objects (DTOs)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── token.py
│   ├── api/                 # API Route Endpoints
│   │   ├── __init__.py
│   │   ├── deps.py          # Dependency injection (DB, current user)
│   │   └── v1/
│   │       ├── api.py       # API router aggregator
│   │       └── endpoints/
│   │           ├── auth.py
│   │           └── users.py
│   └── core/                # Security & Core Utilities
│       ├── __init__.py
│       ├── security.py      # JWT & Password hashing utilities
│       └── database_init.py # Base class declarations
├── alembic/                 # Database migrations
├── Dockerfile               # Multi-stage production Dockerfile
├── docker-compose.yml       # Orchestration manifest
├── requirements.txt         # Pinned Python dependencies
└── .env.example             # Template for environment variables
```

---

### 1. Configuration Management (`app/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    # SECURITY
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # DATABASE
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    def model_post_init(self, __context) -> None:
        object.__setattr__(
            self,
            "DATABASE_URL",
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
```

---

### 2. Async Database Engine (`app/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

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
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncSession:
    """Dependency for yielding async database sessions."""
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

### 3. Security & JWT Utility (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Any
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 4. SQLAlchemy ORM User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database_init import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

---

### 5. Pydantic Schemas (`app/schemas/user.py`)
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
    is_superuser: bool

    class Config:
        from_attributes = True
```

---

### 6. Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings
from app.database import get_db
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
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    return user
```

---

### 7. Authentication Router (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    
    hashed_pass = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pass,
        is_active=True,
        is_superuser=False,
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 8. Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production environments
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

### 9. Multi-Stage Production Dockerfile (`Dockerfile`)
```dockerfile
# --- Stage 1: Build Dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Runtime Image ---
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### 10. Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
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

  api:
    build: .
    container_name: fastapi_backend
    restart: always
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=MicroCorp Enterprise API
      - SECRET_KEY=super-secret-jwt-key-change-in-production-environments
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

## 4. ## Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Using Synchronous SQLAlchemy Sessions in Async FastAPI Routes
* **The Anti-Pattern**: Injecting standard `Session` from SQLAlchemy into an `async def` path operation. This blocks the main event loop during database I/O, destroying asynchronous concurrency benefits.
* **The Fix**: Always use `AsyncSession` combined with `create_async_engine` and `async_sessionmaker`.

### ❌ 2. Catching Generic Exceptions Without Rolling Back Transactions
* **The Anti-Pattern**: Writing custom try/except blocks around database operations without explicitly triggering a session rollback. This leaves the database session in a failed state, causing subsequent queries in the same request lifecycle to fail silently.
* **The Fix**: Implement a centralized session dependency context manager (as shown in `app/database.py`) that guarantees automatic rollback on exception.

### ❌ 3. Storing Plain Text Passwords or Using Weak Hashing Algorithms
* **The Anti-Pattern**: Hashing passwords using `MD5`, `SHA256`, or plain text storage in the database.
* **The Fix**: Always use `passlib` with `bcrypt` or `argon2` hashing schemas configured with appropriate work factors.

### ❌ 4. Hardcoding Secrets in Source Code
* **The Anti-Pattern**: Committing database passwords and JWT secret keys directly into Git repositories.
* **The Fix**: Utilize Pydantic's `BaseSettings` combined with `.env` files and strict `.gitignore` enforcement.

---

## 5. ## Performance & Optimization Tips

1. **Connection Pooling Tuning**: Adjust `pool_size` and `max_overflow` parameters in `create_async_engine()` based on your PostgreSQL server limits and expected concurrent user load.
2. **Uvicorn Multi-Worker Scaling**: In production environments (behind Nginx or an AWS ALB), run multiple worker processes using Uvicorn CLI flags (`--workers 4` or leveraging `gunicorn` with Uvicorn workers).
3. **Pydantic Model Compilation**: Pydantic v2 utilizes Rust-based core validation (`pydantic-core`). Ensure you are using `model_dump()` and `model_validate()` rather than deprecated v1 methods (`dict()`, `from_orm()`) for up to 10x serialization speedups.
4. **Database Indexing Strategy**: Ensure foreign keys and high-cardinality lookup columns (such as `email` and `id`) are explicitly indexed within your SQLAlchemy models (`index=True`).

---

## 6. ## Commercial License & Attribution Summary

### **Commercial License Terms**
* **Copyright © MicroCorp AI & The Agency Engineering Division.**
* **Grant of License**: Upon delivery to the client or purchase via authorized distribution channels, the licensee is granted a worldwide, non-exclusive, perpetual, royalty-free commercial license to modify, distribute, deploy, and monetize software built upon this boilerplate.
* **Restrictions**: Direct redistribution or resale of this exact boilerplate code as a competing standalone digital product or template is strictly prohibited.
* **Warranty Disclaimer**: This software is provided "as is", without warranty of any kind, express or implied. The Agency and MicroCorp AI disclaim all liability for direct, indirect, or consequential damages resulting from the deployment of this codebase.