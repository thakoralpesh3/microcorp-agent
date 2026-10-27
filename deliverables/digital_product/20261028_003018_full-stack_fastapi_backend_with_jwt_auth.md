# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Production Architecture*  
> **Product ID:** `MCPP-FASTAPI-JWT-004`  
> **Target Audience:** Enterprise Clients, Senior Full-Stack Engineers, Freelance Deliverables  

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Boilerplate: Production-Ready Asynchronous Backend with Secure JWT Authentication & Multi-Stage Dockerization

Stop wasting 40+ billable hours building the same foundational boilerplate for every new client project. This battle-tested, enterprise-grade architecture delivers a lightning-fast asynchronous FastAPI backend complete with enterprise security patterns, database migrations, containerization, and strict type safety out of the box.

### Key Business Value
* **Time-to-Market Acceleration:** Deploy a fully secure, database-backed REST API in under 10 minutes instead of days.
* **Security First:** Implements industry-standard OAuth2 with Password (and hashing), stateless JSON Web Tokens (JWT) with automatic expiration handling, and granular role-based access control (RBAC).
* **Zero Infrastructure Friction:** Fully containerized using multi-stage Docker builds coupled with Docker Compose for seamless local development and production handoff.
* **Strict Type Safety:** Fully leveraged Pydantic v2 schemas and SQLAlchemy 2.0 asynchronous ORM models eliminate runtime type errors.

---

## 2. Quick Start & Core Concepts

### System Architecture Quick-Reference

| Layer | Technology Stack | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (v0.110+) | High-performance asynchronous web routing and auto-docs. |
| **Validation** | Pydantic v2 | Data validation, serialization, and settings management. |
| **ORM / DB** | SQLAlchemy 2.0 (Async) + PostgreSQL | Non-blocking database queries and relational integrity. |
| **Migrations** | Alembic | Version-controlled database schema migrations. |
| **Authentication** | `python-jose` + `passlib[bcrypt]` | Secure password hashing and stateless JWT generation/verification. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds for minimal image size and instant environment sync. |

### ⚡ 3-Minute Quick Start

1. **Clone and configure environment variables:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin up services via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify the installation:**
   * Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
   * Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-backend/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1)
│   │   ├── endpoints/       # Auth, Users, Health
│   │   └── deps.py          # Dependency injections (DB, Current User)
│   ├── core/                # Config, Security, Database session
│   ├── models/              # SQLAlchemy 2.0 Database Models
│   ├── schemas/             # Pydantic v2 Request/Response Schemas
│   ├── services/            # Business logic layer
│   └── main.er              # FastAPI application entrypoint
├── Dockerfile               # Multi-stage production container
├── docker-compose.yml       # Local development orchestration
├── requirements.txt         # Pinned python dependencies
└── .env.example             # Environment template
```

---

### `app/core/config.py` — Type-Safe Environment Settings
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str | None = None

    # JWT Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()

# Dynamic construction if URI isn't explicitly provided
if not settings.SQLALCHEMY_DATABASE_URI:
    settings.SQLALCHEMY_DATABASE_URI = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}/{settings.POSTGRES_DB}"
    )
```

---

### `app/core/database.py` — Async SQLAlchemy Session Factory
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
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

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function that yields db sessions per request."""
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

### `app/core/security.py` — Password Hashing & JWT Minting
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

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
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

### `app/models/user.py` — SQLAlchemy 2.0 Declarative Model
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
```

---

### `app/schemas/user.py` — Pydantic v2 Validation Schemas
```python
import uuid
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserRead(UserBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str | None = None
```

---

### `app/api/deps.py` — Authentication Dependencies & RBAC
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

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
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough administrative privileges",
        )
    return current_user
```

---

### `app/api/endpoints/auth.py` — Authentication Router
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
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
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists in the system.",
        )
        
    hashed_pwd = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
```

---

### `app/main.py` — Application Entrypoint
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import auth, users  # Assume users router maps standard CRUD

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust strictly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### `Dockerfile` — Multi-Stage Production Container
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

# Copy installed python dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `docker-compose.yml` — Local Development Stack
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
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
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangeinproduction1239857
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* ❌ **Mixing Synchronous and Asynchronous DB Drivers:** Using standard `psycopg2` inside async FastAPI routes will block the event loop under heavy loads. Always use `asyncpg` with SQLAlchemy's async extensions.
* ❌ **Hardcoding Secrets in Code:** Never commit keys or connection strings. Always inject secrets via environment variables using Pydantic's `BaseSettings`.
* ❌ **Forgetting Database Session Rollbacks:** Unhandled exceptions that break execution flow without an explicit `session.rollback()` can leave transactions hanging in a dirty state, locking tables.
* ❌ **Omitting Connection Pooling Tuning:** Leaving default connection pools in production can overwhelm PostgreSQL instances. Explicitly configure `pool_size` and `max_overflow` parameters based on server specifications.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production environments, run Uvicorn behind a process manager like Gunicorn or orchestrate multiple Uvicorn instances via Kubernetes/Docker replicas rather than relying on a single python process.
* **Database Indexing:** Ensure foreign keys and high-frequency search columns (such as `email` fields and token identifiers) explicitly include database indices (`index=True`).
* **Pydantic Model Serialization:** For high-throughput endpoints returning large arrays of objects, use `.model_dump()` sparingly or return lightweight scalar response models to minimize serialization overhead.

---

## 6. Commercial License & Attribution Summary

```text
====================================================================
MICROCORP AI COMMERCIAL DIGITAL ASSET LICENSE AGREEMENT
====================================================================
Product: Full-Stack FastAPI Backend with JWT Auth & Docker Setup
Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.
All rights reserved.

1. GRANTED RIGHTS:
   - You are granted a perpetual, non-exclusive license to use, 
     modify, adapt, and deploy this codebase for commercial client 
     deliverables, internal applications, and SaaS products.
   - You may white-label and bundle this code into Fiverr, Upwork, 
     or enterprise direct-client deliverables.

2. RESTRICTIONS:
   - Reselling, redistributing, or publishing this specific code 
     boilerplate as an open-source template, standalone digital 
     product, or marketplace item on Gumroad, GitHub Marketplace, 
     or similar platforms is strictly prohibited.

3. DISCLAIMER:
   - Provided "AS IS" without warranty of any kind, express or 
     implied. The authors are not liable for any damages arising 
     from the use of this software.
====================================================================
```