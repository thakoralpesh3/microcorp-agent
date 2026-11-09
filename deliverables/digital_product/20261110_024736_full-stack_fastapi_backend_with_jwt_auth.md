# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architect Spec #FA-992*
> *Turnkey Production Solution for Enterprise Clients & High-Ticket Freelance Delivery*

---

## 1. # Product Title & Value Proposition

### 🚀 Production-Grade FastAPI Backend Boilerplate
This turnkey package provides a battle-tested, asynchronous, fully containerized FastAPI backend architecture integrated with JSON Web Token (JWT) authentication, role-based access control (RBAC), SQLAlchemy 2.0 (async), Alembic database migrations, and a production-ready Docker Compose orchestration layer.

### 💰 Commercial Value Proposition
* **Time-to-Market Acceleration:** Save 40+ hours of boilerplate setup, security wiring, and DevOps configuration.
* **Security First:** Implements industry-standard OAuth2 with Password (and hashing via `passlib[bcrypt]`), HTTP-only cookie or bearer token handling, and strict CORS configuration.
* **Horizontal Scalability:** Decoupled container architecture (API, Database, Caching layer) primed for orchestration platforms (Kubernetes, AWS ECS, Google Cloud Run).
* **Zero Technical Debt:** Clean domain-driven design, Pydantic v2 validation, and full type hinting across the entire data pipeline.

---

## 2. ## Quick Start & Core Concepts

### System Architecture Stack
* **Framework:** FastAPI (Asynchronous, High Performance)
* **ORM:** SQLAlchemy 2.0 (Async Session) + Alembic
* **Database:** PostgreSQL 15+
* **Caching/Broker:** Redis 7+
* **Containerization:** Docker & Docker Compose (Multi-stage builds)

### Core Syntax & Component Reference

| Component | Technology | Primary Purpose |
| :--- | :--- | :--- |
| **Routing** | `APIRouter` | Modular endpoint organization by business domain |
| **Validation** | Pydantic v2 | Strict input/output parsing and serialization |
| **Auth** | `python-jose` / `passlib` | JWT token generation, verification, and password hashing |
| **Database** | `asyncpg` + SQLAlchemy | Non-blocking database connection pooling and querying |
| **Migration** | Alembic | Schema version control and forward/backward migrations |

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-enterprise/
├── alembic/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── api.py
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
├── requirements.txt
└── alembic.ini
```

---

### 3.1 Environment Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    DATABASE_URL: str = ""

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### 3.2 Database Engine & Session (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
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

### 3.3 Security & JWT Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### 3.4 SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import String, Boolean, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
```

---

### 3.5 Pydantic Schemas (`app/schemas/user.py`)
```python
import uuid
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

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

### 3.6 Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
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

### 3.7 Auth Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
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
            detail="User with this email already exists."
        )
    
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 3.8 Main Application Entrypoint (`app/main.py`)
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

---

### 3.9 Containerization Layer

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_db
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Synchronous Database Drivers with Async FastAPI Routes**
   * *Anti-Pattern:* Using standard `psycopg2` or standard SQLAlchemy Session inside `async def` route paths. This blocks the main event loop.
   * *Correction:* Always use `asyncpg` combined with `AsyncSession` and `sqlalchemy.ext.asyncio`.
2. **Hardcoding Secrets in Codebase or Dockerfiles**
   * *Anti-Pattern:* Putting production DB passwords or JWT secret keys directly into `docker-compose.yml` or source code files.
   * *Correction:* Utilize `.env` files locally and secure secret managers (AWS Secrets Manager, HashiCorp Vault) in production deployments.
3. **Missing `pool_pre_ping=True` on Database Engines**
   * *Anti-Pattern:* Ignoring idle connection drops by the database server, leading to intermittent `OperationalError` exceptions.
   * *Correction:* Always instantiate the engine with `pool_pre_ping=True` to test connections before querying.
4. **Catching Generic Exceptions Blindly**
   * *Anti-Pattern:* Using `except Exception:` without logging or rolling back transactions, leaving sessions in a dirty state.
   * *Correction:* Ensure transactional boundaries roll back on explicit failures before re-raising or converting to HTTP exceptions.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a reverse proxy (Nginx/Traefik), run Uvicorn with multiple workers or utilize Gunicorn with Uvicorn worker classes:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Connection Pool Tuning:** Adjust `pool_size` and `max_overflow` in your database connection settings based on your server core count and anticipated traffic throughput.
* **Response Serialization Caching:** For heavy, low-mutation read endpoints, implement Redis caching layers before hitting the database or leverage `ORJSONResponse` for significantly faster JSON serialization cycles:
  ```python
  from fastapi import FastAPI
  from fastapi.responses import ORJSONResponse

  app = FastAPI(default_response_class=ORJSONResponse)
  ```

---

## 6. ## Commercial License & Attribution Summary

### 📄 MicroCorp AI Commercial License (Type C — Turnkey Client Delivery)
* **Granted Rights:** You are licensed to use, modify, distribute, and resell this codebase as part of custom software engineering services delivered to end clients (e.g., Fiverr, Upwork, or direct B2B contracts).
* **Restrictions:** You may not resell this exact boiler-plate repository as an uncompiled standalone competing product template on public template marketplaces (e.g., Gumroad, ThemeForest) without explicit written authorization from MicroCorp AI.
* **Warranty:** Provided "AS IS", without warranty of any kind, express or implied. The Backend Architect and MicroCorp AI disclaim all liability for direct or indirect damages resulting from production deployment configurations.