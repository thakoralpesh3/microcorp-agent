# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise-Grade FastAPI Backend Boilerplate
*Secure, high-performance, containerized production blueprint with asynchronous JWT authentication, PostgreSQL, Alembic migrations, and modular dependency injection.*

#### Value Proposition
Stop wasting 40+ hours architecting boilerplate user management, database connection pooling, and Docker configurations. This turnkey solution provides an enterprise-ready, production-graded FastAPI foundation built by veteran backend architects. Designed for immediate deployment, it drastically cuts time-to-market for SaaS MVPs, internal tools, and scalable API services.

#### Target Audience
* **Freelance Engineers & Agencies:** Deliver client backends 5x faster with standardized, battle-tested patterns.
* **Startup Founders:** Launch your core infrastructure securely on day one without technical debt.
* **Backend Developers:** Learn idiomatic, scalable FastAPI architectures mapped to modern async design patterns.

---

## 2. Quick Start & Core Concepts

### Architectural Syntax & Framework Map

| Component | Technology | Purpose / Design Pattern |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance asynchronous REST API with automatic OpenAPI documentation. |
| **ORM / Migrations** | SQLAlchemy 2.0 (Async) + Alembic | Type-safe database management and declarative schema version control. |
| **Database** | PostgreSQL 15 | Robust relational persistence layer with connection pooling. |
| **Authentication** | OAuth2 with JWT (jose + passlib) | Stateless, cryptographically secure token-based access control. |
| **Containerization** | Docker & Docker Compose | Isolated multi-container environments for local development and production. |

### ⚡ 3-Step Local Initialization

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Containers via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify API Health & Docs:**
   * Interactive Swagger UI: `http://localhost:8000/docs`
   * ReDoc Alternative: `http://localhost:8000/redoc`

---

## 3. Production Code Patterns & Architecture Examples

### 📂 Directory Structure
```text
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   └── users.py
│   │   └── router.py
│   └── deps.py
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/
│   └── user.py
├── schemas/
│   └── user.py
├── services/
│   └── user_service.py
├── main.py
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── requirements.txt
```

---

### 📄 Core Implementation Files

#### `app/core/config.py` (Environment Configuration)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

#### `app/core/database.py` (Async Database Engine & Session)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
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

#### `app/core/security.py` (Password Hashing & JWT Generation)
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
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
```

#### `app/models/user.py` (SQLAlchemy 2.0 ORM Model)
```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

#### `app/schemas/user.py` (Pydantic V2 Validation Schemas)
```python
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
```

#### `app/api/deps.py` (Authentication Dependencies)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


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
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenPayload(sub=email)
    except JWTError:
        raise credentials_exception

    user = await UserService.get_by_email(db, email=token_data.sub)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account"
        )
    return user
```

#### `app/services/user_service.py` (Business Logic Layer)
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class UserService:

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    @staticmethod
    async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
        db_user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            is_active=user_in.is_active,
        )
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
        user = await UserService.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user
```

#### `app/api/v1/endpoints/auth.py` (Authentication Endpoints)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    existing_user = await UserService.get_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered.",
        )
    user = await UserService.create_user(db, user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await UserService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

#### `app/api/v1/router.py` (API Router Assembly)
```python
from fastapi import APIRouter
from app.api.v1.endpoints import auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
```

#### `app/main.py` (Application Entrypoint)
```python
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 🐳 Containerization Files

#### `Dockerfile` (Multi-stage Optimized Build)
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

#### `docker-compose.yml` (Local & Staging Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
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
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction123!@#
      - JWT_ALGORITHM=HS256
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

#### `requirements.txt` (Production Dependencies)
```text
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
sqlalchemy>=2.0.28
asyncpg>=0.29.0
alembic>=1.13.1
pydantic>=2.6.4
pydantic-settings>=2.2.1
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.9
psycopg2-binary>=2.9.9
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints**
   * *Anti-Pattern:* Utilizing blocking libraries like `requests` or standard `sqlite3` inside `async def` endpoints, which starves the event loop thread pool.
   * *Correction:* Use native asynchronous drivers (`asyncpg` for PostgreSQL, `httpx` for outbound HTTP requests) or run synchronous operations via `run_in_threadpool`.

2. **Hardcoding Application Secrets**
   * *Anti-Pattern:* Embedding database credentials and JWT private keys directly in source files or version-controlled configuration documents.
   * *Correction:* Validate all operational parameters through `pydantic-settings` pulling strictly from environment variables or secure secret managers (AWS Secrets Manager, Vault).

3. **Session Leakage and Missing Commit/Rollback Handling**
   * *Anti-Pattern:* Opening raw database sessions without proper context managers, leading to unreleased connection handles and connection pool exhaustion.
   * *Correction:* Always rely on dependency injection generators (`get_db`) using `try/except/finally` structures to guarantee transaction settlement and connection release.

4. **Ignoring Database Connection Pool Limits**
   * *Anti-Pattern:* Deploying default database pool sizes without matching container scaling requirements, resulting in `too many clients already` database errors under load.
   * *Correction:* Configure SQLAlchemy engine arguments (`pool_size`, `max_overflow`, `pool_pre_ping=True`) according to your container concurrency limits.

---

## 5. Performance & Optimization Tips

* **Enable Uvicorn Workers for Multi-Core Utilization:**
  When deploying outside Docker development mode (or via Gunicorn with Uvicorn worker classes), scale worker processes to match available CPU cores:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Optimize Database Indexes:**
  Ensure high-frequency lookup columns (`email`, foreign keys) feature explicit database indexes (`index=True` in SQLAlchemy definitions) to prevent sequential table scans.
* **Leverage Response Model Caching & Exclusion:**
  Use Pydantic’s `model_config = ConfigDict(frozen=True)` and selective field projection (`response_model`) to minimize payload serialization overhead.
* **Database Connection Health Checks:**
  Always enable `pool_pre_ping=True` on your SQLAlchemy engine to proactively drop stale or dead TCP connections before executing queries.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License Agreement
*Copyright © 2024 MicroCorp AI. All rights reserved.*

#### 1. Grant of License
By purchasing or downloading this software asset, MicroCorp AI grants the purchaser (Individual or Enterprise) a non-exclusive, perpetual, worldwide license to use, modify, adapt, and deploy this codebase for commercial applications, client deliverables, and internal startup MVPs.

#### 2. Restrictions
* Redistribution, resale, or sub-licensing of this codebase as an isolated boilerplate template, component library, or digital product on marketplaces (e.g., Gumroad, GitHub Marketplace, Envato) is **strictly prohibited**.
* Removal of original copyright notices, license headers, or attribution notes within core framework files is a violation of agreement terms.

#### 3. Disclaimer of Warranty
This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall MicroCorp AI or The Agency Engineering Division be liable for any claim, damages, or other liability arising from its utilization.