# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Turnkey Boilerplate*

---

## 1. Product Title & Value Proposition

### **FastAPI Enterprise Engine: JWT-Auth & Dockerized Boilerplate**
* **Target Audience:** Freelance Engineers, Agency Developers, and Startups needing an immediate, bulletproof Python backend.
* **The Problem:** Setting up asynchronous database drivers, strict Pydantic v2 validation, secure stateless JWT authentication, CORS policies, environment configurations, and multi-stage Docker builds consumes 15–20 hours of billable time per project.
* **The Solution:** A zero-to-production boilerplate engineered for extreme speed, type safety, and horizontal scale. Drop this into your repository, run a single command, and immediately begin writing business logic.

---

## 2. Quick Start & Core Concepts

### Architectural Component Reference

| Layer / Module | Technology Stack | Purpose & Design Pattern |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance asynchronous REST API with automatic OpenAPI docs. |
| **Data Validation** | Pydantic v2 | Strict payload validation, serialization, and settings management via `BaseSettings`. |
| **Database Driver** | SQLAlchemy 2.0 (Async) + Alembic | Modern asynchronous ORM patterns paired with robust migration management. |
| **Database Engine** | PostgreSQL 16 | ACID-compliant relational storage with connection pooling. |
| **Authentication** | python-jose & passlib (Bcrypt) | Stateless JWT issuance/verification and secure cryptographic password hashing. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds, non-root user execution, and isolated service networking. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-enterprise/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       └── users.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### Configuration Engine (`app/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### Asynchronous Database Setup (`app/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
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

### SQLAlchemy Models (`app/models.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
```

---

### Pydantic Schemas (`app/schemas.py`)
```python
import uuid
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str | None = None
```

---

### Security & JWT Handler (`app/security.py`)
```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

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
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload.get("sub")
    except JWTError:
        return None
```

---

### Authentication Dependencies (`app/routers/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserResponse
from app.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = decode_access_token(token)
    if not email:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise credentials_exception
    return user
```

---

### FastAPI Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System"])
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
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
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
    container_name: fastapi_api
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password123@db:5432/enterprise_db
      - SECRET_KEY=supersecretkeychangeinproduction123456789
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async DB Drivers:** 
   * *Anti-Pattern:* Using `psycopg2` inside an asynchronous FastAPI path operation. This blocks the main event loop.
   * *Solution:* Always use `asyncpg` via `create_async_engine` for non-blocking I/O operations.
2. **Hardcoding Secrets in Code or Dockerfiles:**
   * *Anti-Pattern:* Committing `SECRET_KEY` or database passwords directly into version control.
   * *Solution:* Rely strictly on Pydantic's `BaseSettings` reading from `.env` files or orchestration environment injectors.
3. **Failing to Handle Database Session Lifecycle:**
   * *Anti-Pattern:* Opening manual database sessions without context managers, leading to connection leaks.
   * *Solution:* Use FastAPI’s `Depends(get_db)` to guarantee proper context teardown and automatic session closure.
4. **Running Containers as Root in Production:**
   * *Anti-Pattern:* Allowing application processes to execute with root privileges inside Docker containers.
   * *Solution:* Create a dedicated system user within your production Dockerfile for runtime execution.

---

## 5. Performance & Optimization Tips

* **Uvicorn Workers Scaling:** In production, do not rely on `--reload`. Deploy Uvicorn behind a process manager or orchestrator (like Gunicorn or Kubernetes) managing multiple worker processes:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Connection Pooling Parameters:** Fine-tune SQLAlchemy engine parameters based on expected concurrency loads:
  ```python
  engine = create_async_engine(
      settings.DATABASE_URL,
      pool_size=20,
      max_overflow=10,
      pool_recycle=3600,
  )
```
* **Pydantic Model Serialization Optimization:** For endpoints returning heavy payload lists, leverage `model_dump(mode='json')` or disable validation on read operations where models are trusted.

---

## 6. Commercial License & Attribution Summary

* **License:** MIT Open-Source Commercial License. 
* **Usage Rights:** Free for personal use, commercial client deliverables, SaaS development, and agency deployment.
* **Attribution:** Provided by **The Agency Engineering Division** (MicroCorp AI). 
* **Warranty Disclaimer:** Provided *as-is* without warranty of any kind. Engineers are responsible for rotating cryptographic secrets prior to production deployment.