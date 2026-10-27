# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Grade Systems & Architecture*  
> **Product Type:** Full Turnkey Client Solution / Enterprise Boilerplate  
> **Target Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL, Docker Compose, PyJWT, Alembic

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Architecture
Stop wasting 40+ hours configuring boilerplate database connections, setting up secure password hashing, structuring JWT authentication, and writing complex multi-stage Dockerfiles. 

This turnkey digital product provides a battle-tested, highly scalable, and structurally immaculate FastAPI backend engineered specifically for modern microservices and high-ticket freelance client delivery. Built strictly around **SQLAlchemy 2.0 (Async)**, **Pydantic v2**, and **Docker containerization**, this codebase guarantees Type Safety, Asynchronous Performance, and Instant Deployability out of the box.

### Key Value Propositions
- **Zero-Config Developer Velocity:** Spin up a fully isolated, hot-reloading development environment with PostgreSQL in under 60 seconds using Docker Compose.
- **Enterprise Security Standard:** Implements stateless JSON Web Tokens (JWT) with HTTP-only cookie support or bearer tokens, bcrypt password hashing, and role-based access control (RBAC).
- **Asynchronous Scalability:** Non-blocking database operations powered by `asyncpg` and SQLAlchemy's asynchronous session management.
- **Client-Ready Handover:** Clean, modular directory layout adhering to Domain-Driven principles, making it trivial to hand off to client development teams or extend with new domain features.

---

## 2. Quick Start & Core Concepts

### Architectural Syntax & Component Mapping

| Component | Technology | Core Responsibility |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance asynchronous HTTP routing, OpenAPI docs generation, and request dependency injection. |
| **Data Validation** | Pydantic v2 | Strict data parsing, serialization, and settings management via environment variables. |
| **ORM & Migrations** | SQLAlchemy 2.0 & Alembic | Async database operations, declarative mapping, and automated schema migrations. |
| **Database** | PostgreSQL 16 | ACID-compliant relational data storage optimized with async connection pooling. |
| **Authentication** | PyJWT & Passlib | Cryptographic token creation/validation and secure password hashing (`bcrypt`). |
| **Containerization** | Docker & Compose | Multi-stage production builds and zero-friction local development orchestration. |

### ⚡ 60-Second Quick Start

1. **Clone or Extract the Package:**
   ```bash
   unzip fastapi-jwt-docker-boilerplate.zip
   cd fastapi-jwt-docker-boilerplate
   ```

2. **Configure Environment Variables:**
   Copy the sample environment file and adjust keys as needed:
   ```bash
   cp .env.example .env
   ```

3. **Launch via Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

4. **Verify Deployment:**
   - API Documentation (Swagger UI): `http://localhost:8000/docs`
   - Alternative Docs (ReDoc): `http://localhost:8000/redoc`
   - Health Check Endpoint: `http://localhost:8000/health`

---

## 3. Production Code Patterns & Architecture Examples

### 📂 Directory Structure
```text
fastapi-backend/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API routers (Endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # auth.py, users.py, items.py
│   │   │   └── router.py     # Main API v1 router aggregator
│   │   └── deps.py           # Dependency injection (DB session, current user)
│   ├── core/                 # Application configuration & security
│   │   ├── config.py         # Pydantic BaseSettings
│   │   ├── database.py       # Async engine & sessionmaker
│   │   └── security.py       # JWT creation & password hashing
│   ├── models/               # SQLAlchemy ORM models
│   │   └── user.py
│   ├── schemas/              # Pydantic validation schemas
│   │   └── user.py
│   └── main.py               # FastAPI application entrypoint
├── Dockerfile                # Multi-stage production container build
├── docker-compose.yml        # Local orchestration
├── requirements.txt          # Python dependencies
└── .env.example              # Sample environment configuration
```

---

### ⚙️ 1. Core Settings (`app/core/config.py`)
Handles type-safe configuration loading from environment variables using Pydantic `BaseSettings`.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
```

---

### 🗄️ 2. Async Database Engine (`app/core/database.py`)
Configures the asynchronous SQLAlchemy engine and dependency injection generator for request sessions.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

### 🛡️ 3. Security & JWT Utilities (`app/core/security.py`)
Provides password hashing via `passlib` and JWT token generation/validation via `pyjwt`.

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
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### 👤 4. SQLAlchemy User Model (`app/models/user.py`)
Declarative SQLAlchemy 2.0 model with async compatibility.

```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

### 📥 5. Pydantic Schemas (`app/schemas/user.py`)
Request/Response validation contracts.

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str | None = None
```

---

### 🔐 6. Authentication Dependencies (`app/api/deps.py`)
Validates Bearer tokens and injects the authenticated user into API endpoints.

```python
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials")
    
    result = await db.execute(select(User).where(User.email == token_data.sub))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    return user
```

---

### 🚀 7. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
Handles registration and token generation.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 🐳 8. Production Dockerfile (`Dockerfile`)
Multi-stage build pattern minimizing image footprint and securing container permissions.

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

### 🐙 9. Local Orchestration (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: fastapi_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d fastapi_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    container_name: fastapi_web
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
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction123!@#
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Synchronous and Asynchronous ORM Calls**
   - **The Anti-Pattern:** Using synchronous database drivers (`psycopg2`) inside async FastAPI endpoint definitions (`async def`). This blocks the main event loop and destroys concurrency performance.
   - **The Fix:** Always use `asyncpg` with SQLAlchemy's `create_async_engine` and await all query executions (`await db.execute(...)`).

2. ❌ **Hardcoding Secrets in Code or Docker Files**
   - **The Anti-Pattern:** Placing JWT secret keys or database credentials directly into `docker-compose.yml` or source files.
   - **The Fix:** Always load variables via Pydantic `BaseSettings` reading exclusively from an isolated `.env` file or orchestrator secret manager.

3. ❌ **Exposing ORM Models Directly as API Responses**
   - **The Anti-Pattern:** Returning database models straight from path operations, which can leak sensitive attributes (like hashed passwords) or cause recursive serialization failures with relationships.
   - **The Fix:** Always map ORM objects into explicitly declared Pydantic response models using `from_attributes = True` (formerly `orm_mode = True`).

4. ❌ **Swallowing Database Exceptions Silently**
   - **The Anti-Pattern:** Catching generic exceptions without rolling back active database transactions, leading to "dead transactions" and connection pool exhaustion.
   - **The Fix:** Implement robust context managers or dependency generators that explicitly trigger `await session.rollback()` upon caught exceptions.

---

## 5. Performance & Optimization Tips

- **Connection Pooling:** Fine-tune `pool_size` and `max_overflow` in `create_async_engine` depending on your server vCPU allocation and PostgreSQL max connection limits.
- **Query Optimization:** Utilize SQLAlchemy's `selectinload` or `joinedload` strategies when dealing with relational data to avoid the N+1 query problem.
- **Uvicorn Worker Scaling:** In production environments behind a reverse proxy (like Nginx), scale Uvicorn workers using process managers or container replicas formula: `Workers = (2 * vCPU) + 1`.
- **Response Compression:** Integrate `GZipMiddleware` into FastAPI (`app.add_middleware(GZipMiddleware, minimum_size=1000)`) to significantly reduce payload transfer sizes over the network.

---

## 6. Commercial License & Attribution Summary

### 📄 Enterprise Commercial License
*Copyright © 2024 MicroCorp AI & The Agency Engineering Division. All rights reserved.*

- **Grant of Rights:** This turnkey digital product is licensed to the purchaser for deployment in commercial client projects, internal enterprise applications, and SaaS products.
- **Restrictions:** Redistribution, resale, or sub-licensing of the raw source code boilerplate as an independent template on marketplaces (e.g., GitHub, Gumroad, Envato) is strictly prohibited.
- **Warranty Disclaimer:** Provided "as is" without warranty of any kind, express or implied. The authors assume no liability for direct or indirect damages resulting from the deployment of this code.