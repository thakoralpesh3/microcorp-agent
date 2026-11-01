# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Turnkey Solution Package*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Blueprint
*Secure, Scalable, Containerized API Engine with Asynchronous SQLAlchemy, Alembic Migrations, and JWT Authentication.*

#### The Problem
Building a production-grade backend from scratch requires stitching together dozens of disparate technologies—ASGI servers, ORMs, migration engines, security/hashing layers, dependency injection systems, and container runtimes. Doing this correctly while enforcing type safety, security best practices, and horizontal scalability typically takes an engineering team weeks.

#### The Solution
This turnkey repository provides a battle-tested, standardized backend architecture built on **FastAPI**, **PostgreSQL**, **SQLAlchemy (Async)**, and **Docker**. It is structured for immediate deployment to AWS, GCP, or DigitalOcean via containerized services, saving you 80+ hours of boilerplate configuration and security hardening.

#### Target Buyers & Use Cases
* **Fiverr & Upwork Freelancers:** Deliver production-grade client backends in hours instead of weeks.
* **SaaS Founders:** Jumpstart your MVP with built-in user management, secure token authentication, and robust database tooling.
* **Enterprise Teams:** Establish an internal standard for clean, modular, async Python microservices.

---

## 2. Quick Start & Core Concepts

### System Architecture Stack
| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous API routing & validation |
| **Runtime** | Uvicorn | `0.28+` | ASGI application server with worker management |
| **Database** | PostgreSQL | `16-alpine` | Relational data store for ACID-compliant persistence |
| **ORM** | SQLAlchemy | `2.0+` (Async) | Pythonic database toolkit with type-hinted models |
| **Migrations** | Alembic | `1.13+` | Database schema version control and migration management |
| **Security** | PyJWT & Passlib | `2.8+` / `1.7+` | Token generation, validation, and bcrypt password hashing |
| **Containerization**| Docker & Compose | `v2+` | Multi-container orchestration and environment isolation |

---

### Instant Setup (5-Minute Bootstrap)

Clone the repository structure, configure your environment, and spin up the entire stack using Docker Compose.

```bash
# 1. Clone or initialize the project structure
mkdir fastapi-enterprise-backend && cd fastapi-enterprise-backend

# 2. Create the environment configuration file
cat << 'EOF' > .env
PROJECT_NAME="MicroCorp Enterprise API"
POSTGRES_USER=postgres
POSTGRES_PASSWORD=supersecurepassword123
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=enterprise_db
DATABASE_URL=postgresql+asyncpg://postgres:supersecurepassword123@db:5432/enterprise_db
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

# 3. Spin up containers in detached mode
docker compose up --build -d
```

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Tree
```text
fastapi-enterprise-backend/
├── app/
│   ├── __init__.py
│   ├── main.py               # Application factory & middleware
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic BaseSettings configuration
│   │   ├── database.py       # Async SQLAlchemy sessionmaker
│   │   └── security.py       # JWT creation & password hashing
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py           # SQLAlchemy User ORM Model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py           # Pydantic validation schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py           # FastAPI Dependencies (DB session, current user)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.v1.py     # API Router aggregator
│   │       endpoints/
│   │           ├── auth.py   # Login & Token generation
│   │           └── users.py  # User CRUD operations
│   └── alembic/              # Database migrations
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### 1. Configuration Engine (`app/core/config.py`)
Utilizes Pydantic Settings to safely parse, validate, and type-cast environment variables.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### 2. Database Session Management (`app/core/database.py`)
Configures an asynchronous SQLAlchemy engine and session factory for non-blocking I/O operations.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
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

---

### 3. Security & JWT Utility (`app/core/security.py`)
Implements secure password hashing via `passlib[bcrypt]` and JWT creation/verification via `PyJWT`.

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


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### 4. SQLAlchemy User Model (`app/models/user.py`)
Type-safe declarative base model mapping to PostgreSQL.

```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

### 5. Pydantic Validation Schemas (`app/schemas/user.py`)
Enforces strict input validation and output serialization rules.

```python
import uuid
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None
```

---

### 6. Dependency Injection (`app/api/deps.py`)
Extracts and validates JWT tokens from incoming requests, providing the current active user to endpoints.

```python
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
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

---

### 7. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
Handles OAuth2-compliant token generation.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 8. Application Factory (`app/main.py`)
Initializes FastAPI, configures CORS middleware, and mounts API routers.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api_v1 import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 9. Docker Configuration

#### `Dockerfile`
Multi-stage build pattern for optimal security and minimized image footprint.

```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

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
Orchestrates backend services alongside a persistent PostgreSQL instance with health checks.

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: supersecurepassword123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:supersecurepassword123@db:5432/enterprise_db
      - SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Using Synchronous Database Drivers (`psycopg2`) in Async FastAPI Endpoints
* **The Antipattern:** Mixing synchronous blocking database operations (e.g., standard SQLAlchemy sessions) inside `async def` route handlers blocks the main event loop, destroying throughput under concurrent load.
* **The Fix:** Always use asynchronous drivers (`asyncpg`) paired with `sqlalchemy.ext.asyncio`.

### ❌ 2. Storing Secrets in Source Control
* **The Antipattern:** Hardcoding database credentials, JWT secret keys, or third-party API tokens directly in `config.py` or `.env` committed to git.
* **The Fix:** Maintain a `.env.example` file with placeholder values. Ensure `.env` is listed in your `.gitignore`. Use secret managers (AWS Secrets Manager, Doppler, Vault) in production.

### ❌ 3. Catching Broad Exceptions Without Context
* **The Antipattern:** Using `except Exception:` blindly across database transactions without rolling back the session state. This leaves the async session in a corrupt state, causing subsequent queries to fail.
* **The Fix:** Always explicitly execute `await session.rollback()` inside exception blocks before re-raising or returning error responses.

---

## 5. Performance & Optimization Tips

1. **Connection Pooling Tuning:** Adjust SQLAlchemy pool parameters (`pool_size`, `max_overflow`, `pool_recycle`) in high-concurrency environments to prevent database exhaustion.
2. **Response Compression:** Integrate `GZipMiddleware` in `app/main.py` for payloads exceeding 1000 bytes to minimize network transfer overhead.
3. **Uvicorn Worker Scaling:** In production container deployments behind a reverse proxy (like Nginx or Traefik), scale Uvicorn workers using `--workers $(nproc)` or deploy via Gunicorn with Uvicorn worker classes.
4. **Database Indexing:** Ensure foreign keys and high-cardinality lookup columns (such as `email` or UUID primary keys) feature explicit database indexes.

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp Commercial Client License (MCCL-v1.0)
* **Copyright © MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchasing or receiving this turnkey architecture package grants the licensee a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, adapt, and deploy this codebase for commercial client deliverables (e.g., Fiverr, Upwork, agency contracts) and internal SaaS products.
* **Restrictions:** Licensee may not resell, redistribute, sub-license, or open-source this exact boilerplate repository as a standalone competing digital template product on marketplaces (e.g., Gumroad, GitHub Marketplace).
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any direct, indirect, incidental, or consequential damages arising from the deployment of this architecture.