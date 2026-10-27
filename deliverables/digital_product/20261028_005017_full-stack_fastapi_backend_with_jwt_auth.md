# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Product ID: MC-FS-FASTAPI-01*

---

## 1. Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate with Async SQLAlchemy, JWT Authentication, and Production-Ready Dockerized Infrastructure**

Stop wasting 40+ hours configuring boilerplate architecture for every new client project. This commercial turnkey solution provides a fully asynchronous, highly scalable backend foundation built on **FastAPI**, **SQLAlchemy 2.0 (asyncio)**, **Pydantic v2**, and **PostgreSQL**, complete with robust stateless **JWT Authentication**, role-based access control (RBAC), and a zero-downtime multi-stage **Docker Compose** deployment topology.

#### **Key Business & Technical Value:**
* **Instant Client Delivery:** Ship production-ready MVP backends for Fiverr, Upwork, or direct enterprise clients in hours instead of weeks.
* **Modern Asynchronous Stack:** Fully non-blocking I/O operations from HTTP routing down to database queries using `asyncpg`.
* **Enterprise Security Standards:** Implements secure HTTP-only cookies or Bearer token management, password hashing via `passlib[bcrypt]`, and granular dependency injection for auth scopes.
* **Developer Ergonomics:** Fully typed codebase with strict mypy compliance, auto-generated OpenAPI documentation, and structured JSON logging.

---

## 2. Quick Start & Core Concepts

### **System Architecture & Data Flow**
```
[ Client / SPA ] 
       │ 
       ▼ (HTTPS / Bearer Token)
[ Nginx / Reverse Proxy ] (Optional Layer)
       │
       ▼
[ FastAPI App Container ] ──(Async SQLAlchemy / asyncpg)──► [ PostgreSQL DB ]
       │
       └──(Connection Pool)
```

### **Core Stack & Syntax Quick Reference**

| Layer / Component | Technology | Primary Role in System |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous REST API routing and auto-validation. |
| **Data Validation** | Pydantic v2 | Strict payload parsing, serialization, and settings management. |
| **Database Driver** | Asyncpg + SQLAlchemy 2.0 | Non-blocking database connection pooling and ORM models. |
| **Authentication** | python-jose / Passlib | JWT generation, token verification, and bcrypt password hashing. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds, isolated networks, and persistent volumes. |

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi-enterprise-backend/
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
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### **3.1 Environment & Configuration (`app/core/config.py`)**
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
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### **3.2 Database Session & Engine (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
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
    autoflush=False,
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

---

### **3.3 User Database Model (`app/models/user.py`)**
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
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

---

### **3.4 JWT Security & Hashing Utilities (`app/core/security.py`)**
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
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### **3.5 Authentication Dependencies (`app/api/deps.py`)**
```python
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

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
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=uuid.UUID(user_id))
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def get_current_active_superuser(
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

### **3.6 Authentication Router (`app/api/v1/endpoints/auth.py`)**
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
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
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### **3.7 FastAPI Entrypoint (`app/main.py`)**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

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

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### **3.8 Multi-Stage Dockerfile (`Dockerfile`)**
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **3.9 Production Docker Compose (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    container_name: fastapi_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    volumes:
      - .:/app
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "8000:8000"
    restart: always
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async Drivers (`psycopg2` vs `asyncpg`):**
   * *Anti-Pattern:* Using standard synchronous database drivers inside async FastAPI route handlers. This blocks the event loop and defeats the performance benefits of ASGI.
   * *Correction:* Always use `postgresql+asyncpg://` with `create_async_engine`.
2. **Hardcoding Database Commit Inside Routers:**
   * *Anti-Pattern:* Manual session commits scattered across disparate API route files, leading to partial writes or unhandled rollback states.
   * *Correction:* Handle transaction lifecycles cleanly within dependency yields (`get_db`) or use dedicated service/repository layers.
3. **Exposing Raw Database Models in API Responses:**
   * *Anti-Pattern:* Returning SQLAlchemy models directly from endpoints, risking data leakage (e.g., hashed passwords) and tight database coupling.
   * *Correction:* Always validate and serialize outgoing payloads using Pydantic response models (`response_model=UserResponse`).
4. **Ignoring Connection Pool Exhaustion:**
   * *Anti-Pattern:* Unbounded concurrent requests opening infinite database connections under high load.
   * *Correction:* Explicitly configure `pool_size` and `max_overflow` on the async engine.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container environments, run Uvicorn with multiple worker processes behind an Nginx reverse proxy or leverage Gunicorn with Uvicorn worker classes:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Database Indexing Strategy:** Ensure all foreign keys, lookup columns (like `email`), and high-cardinality query filters have explicit database indices defined in your SQLAlchemy models.
* **ORM Lazy Loading Pitfalls:** Async SQLAlchemy does not support lazy loading of relationships across network boundaries after the session is closed. Use explicit `.options(selectinload(...))` or `.joinedload(...)` for related entities.
* **Response Compression:** Integrate `GZipMiddleware` into FastAPI to automatically compress large JSON payloads for clients over slow networks:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```

---

## 6. Commercial License & Attribution Summary

```text
================================================================================
COMMERCIAL DIGITAL PRODUCT LICENSE — MICROCORP AI ENGINEERING DIVISION
================================================================================
Product: Full-Stack FastAPI Backend with JWT Auth and Docker Setup (MC-FS-FASTAPI-01)
Copyright (c) 2026 MicroCorp AI. All Rights Reserved.

1. PERMITTED USE & CLIENT DELIVERY
   - Licensed engineer/purchaser is granted a non-exclusive, perpetual license 
     to deploy, modify, and distribute this codebase within client solutions 
     (Fiverr, Upwork, direct contract work, or internal SaaS products).
   - You may rebrand and bundle this architecture as part of your paid deliverables.

2. RESTRICTIONS
   - Reselling, redistributing, or publishing this exact boilerplate as a standalone 
     commercial template on code marketplaces (e.g., ThemeForest, GitHub Marketplace) 
     without explicit written authorization from MicroCorp AI is strictly prohibited.

3. DISCLAIMER OF WARRANTY
   - This software is provided "as is", without warranty of any kind, express or implied.
   - MicroCorp AI shall not be held liable for any direct, indirect, or incidental 
     damages arising from the deployment of this backend architecture.
================================================================================
```