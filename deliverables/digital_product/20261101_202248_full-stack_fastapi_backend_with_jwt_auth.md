# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Client Delivery Blueprint*

---

## 1. Product Title & Value Proposition

### **Enterprise FastAPI Boilerplate: Production-Grade Async Backend with JWT Auth, SQLAlchemy 2.0, Alembic, and Docker**

#### **Value Proposition**
Building a modern, asynchronous Python backend from scratch requires wiring together dozens of disparate components—authentication flows, database connection pooling, async ORM queries, environment management, and containerization. 

This turnkey solution eliminates weeks of boilerplate setup. It provides a battle-tested, modular architecture designed for horizontal scaling, strict type safety using Pydantic v2, secure password hashing with bcrypt, stateless JWT authentication with refresh token patterns, and a fully orchestrated Docker Compose development and production pipeline.

---

## 2. Quick Start & Core Concepts

### **Quick Start Guide**

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
   cd fastapi-enterprise-boilerplate
   cp .env.example .env
   ```

2. **Spin Up with Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

3. **Run Database Migrations:**
   ```bash
   docker compose exec web alembic upgrade head
   ```

4. **Access Interactive Docs:**
   * Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   * ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### **Core Concepts & Architecture Matrix**

| Layer / Component | Technology Stack | Architectural Responsibility |
| :--- | :--- | :--- |
| **API Framework** | FastAPI (v0.110+) | High-performance ASGI routing, automatic OpenAPI schema generation, dependency injection. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and strict schema validation for requests and responses. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database operations utilizing `asyncpg` driver and declarative mapping. |
| **Migrations** | Alembic | Version-controlled schema migrations synchronized with SQLAlchemy models. |
| **Authentication** | PyJWT / Passlib (Bcrypt) | Stateless token generation, role-based access control (RBAC), secure hashing. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds for minimal image size, isolated network bridges, volume persistence. |

---

## 3. Production Code Patterns & Architecture Examples

### **Directory Structure**
```text
backend/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1 endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/   # auth.py, users.py, items.py
│   │   │   └── api.py       # Router aggregation
│   ├── core/                # Configuration, security, database session
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/              # SQLAlchemy ORM Models
│   ├── schemas/             # Pydantic Schemas
│   ├── services/            # Business logic layer
│   └── main.py              # Application entrypoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### **1. Configuration (`app/core/config.py`)**
Manages environment variables safely using Pydantic Settings.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

### **2. Database Session Management (`app/core/database.py`)**
Async engine setup with scoped session dependency injection.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
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

### **3. Security & JWT Utilities (`app/core/security.py`)**
Password hashing and token generation.

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
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### **4. SQLAlchemy User Model (`app/models/user.py`)**
Declarative mapping utilizing SQLAlchemy 2.0 type annotations.

```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

---

### **5. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**
Token issuing and validation endpoints.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from app.schemas.token import TokenSchema

router = APIRouter()

@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }
```

---

### **6. Application Factory (`app/main.py`)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application

app = get_application()
```

---

### **7. Production Docker Setup (`Dockerfile`)**
Multi-stage build reducing attack surface and image weight.

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

### **8. Docker Compose Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  web:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_prod
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app

  db:
    image: postgres:15-alpine
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_prod
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d fastapi_prod"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations inside Async Endpoints:**
   * *Anti-Pattern:* Using standard `requests`, `time.sleep()`, or blocking database operations inside `async def` routes. This blocks the event loop entirely.
   * *Correction:* Use `httpx` for async HTTP requests, `asyncio.sleep()`, and SQLAlchemy's async session engine. For CPU-bound tasks, offload via `run_in_threadpool`.

2. **Database Session Leaks:**
   * *Anti-Pattern:* Opening sessions manually without ensuring they close during unhandled exceptions.
   * *Correction:* Always use FastAPI's dependency injection system with `yield` combined with `try...finally` blocks to guarantee cleanup.

3. **Exposing Full ORM Models directly in Responses:**
   * *Anti-Pattern:* Returning `User` SQLAlchemy models straight from endpoints, risking data exposure (e.g., hashed passwords).
   * *Correction:* Always map data to strict Pydantic `ResponseSchema` objects (`response_model=UserResponse`).

4. **Hardcoding Secrets in Codebase:**
   * *Anti-Pattern:* Storing JWT secrets or database connection strings directly in `config.py` defaults.
   * *Correction:* Fail fast by requiring environment variables via Pydantic Settings without insecure fallback strings.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production environments behind Nginx or a load balancer, run Uvicorn with multiple workers or process managers (e.g., Gunicorn with Uvicorn worker class):
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Connection Pooling:** Tune `pool_size` and `max_overflow` in your SQLAlchemy engine setup based on your database tier and expected concurrent load.
* **Gzip Compression:** Add FastAPI's GZip middleware for payloads exceeding 1KB to reduce network transfer latency:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure columns frequently queried in `WHERE` clauses (like `email` or foreign keys) carry explicit database indexes (`index=True`).

---

## 6. Commercial License & Attribution Summary

### **Commercial Turnkey License (Fiverr Client Delivery)**

* **Grant of Rights:** MicroCorp AI grants the commissioning client a perpetual, worldwide, non-exclusive, royalty-free license to use, modify, distribute, and sell commercial applications built upon this codebase.
* **Restrictions:** Reselling or redistributing this exact boilerplate as an independent standalone software template or digital product framework is strictly prohibited.
* **Warranty Disclaimer:** Provided "as is" without warranty of any kind, express or implied. The Engineering Division of MicroCorp AI accepts no liability for production deployment failures resulting from improper environment configuration or omitted infrastructure hardening.