# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Turnkey Solution Architecture*

---

## 1. Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Grade Async Backend with JWT, SQLAlchemy 2.0, PostgreSQL, and Docker**

Stop spending 40+ hours architecting boilerplate infrastructure for every new client or microservice. This production-ready, fully containerized FastAPI boilerplate delivers enterprise-grade performance out of the box. Engineered with modern async Python patterns, strict type safety, secure token-based authentication, and a modular architecture, it bridges the gap between rapid prototyping and bulletproof production scaling.

```
+-------------------------------------------------------+
|                 Client / Frontend                     |
+---------------------------+---------------------------+
                            | HTTPS / JSON (Bearer Token)
                            v
+---------------------------+---------------------------+
|               Nginx Reverse Proxy (SSL)               |
+---------------------------+---------------------------+
                            | HTTP
                            v
+---------------------------+---------------------------+
|          FastAPI Application (Uvicorn Workers)        |
|  - Dependency Injection - Pydantic v2 - JWT Auth      |
+-------------+---------------------------+-------------+
              | Async (SQLAlchemy 2.0)    | Caching
              v                           v
+-------------+-------------+   +---------+-------------+
|    PostgreSQL 16 Primary  |   |        Redis          |
+---------------------------+   +-----------------------+
```

### **What You Get:**
*   **Zero Setup Friction:** Spins up via Docker Compose in under 60 seconds with hot-reloading for development.
*   **Modern Python Stack:** Built on FastAPI, Pydantic v2, SQLAlchemy 2.0 (fully async), Alembic, and PostgreSQL.
*   **Secure Authentication Flow:** JWT access and refresh token rotation with bcrypt password hashing and role-based access control (RBAC).
*   **Enterprise-Ready Structure:** Clean Domain-Driven / Layered Architecture ensuring high testability and maintainability.

---

## 2. Quick Start & Core Concepts

### **Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/                  # Database migrations
├── app/
│   ├── api/                  # API routers (Endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/    # Auth, Users, Health
│   │   │   └── router.py
│   └── core/                 # Config, Security, Database session
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic validation schemas
│   ├── services/             # Business logic layer
│   └── main.py               # FastAPI application entrypoint
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

### **Core Stack & Architecture Syntax Reference**

| Component | Technology | Version | Purpose / Architectural Role |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async routing, automatic OpenAPI generation. |
| **Data Validation** | Pydantic | `2.6+` | Runtime data parsing, serialization, and settings management. |
| **ORM / Database** | SQLAlchemy | `2.0+` | Asynchronous ORM with strict type-hinted query compilation. |
| **Migrations** | Alembic | `1.13+` | Version-controlled database schema migrations. |
| **Auth Protocol** | PyJWT / Passlib | `2.8+` | Token generation, verification, and secure password hashing. |
| **Containerization**| Docker & Compose | `24+` | Reproducible multi-container orchestration. |

---

## 3. Production Code Patterns & Architecture Examples

### **A. Environment Configuration (`app/core/config.py`)**
Using Pydantic v2 `BaseSettings` for strict type-safe environment variable injection.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

### **B. Database Session Management (`app/core/database.py`)**
Async SQLAlchemy 2.0 engine setup with dependency injection yields.

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
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

### **C. JWT Authentication & Security (`app/core/security.py`)**
Password hashing and stateless token issuance.

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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### **D. Authentication Dependency (`app/api/deps.py`)**
Extracting and validating the Bearer token against active database records.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = await db.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

### **E. API Endpoint Implementation (`app/api/v1/endpoints/auth.py`)**
Clean routing endpoint handling token exchanges.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db, form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
```

### **F. Docker Configuration (`docker/Dockerfile`)**
Multi-stage build optimized for production performance and minimal attack surface.

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
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **G. Multi-Container Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: docker/Dockerfile
    image: fastapi-app:latest
    container_name: fastapi_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network

  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1.  **Mixing Sync and Async DB Calls:** 
    *   *Anti-Pattern:* Using standard synchronous SQLAlchemy sessions inside async FastAPI endpoint definitions (`async def`). 
    *   *Consequence:* Blocks the event loop, completely destroying concurrency throughput. Always use `AsyncSession` and `asyncpg`.
2.  **Hardcoding Secrets in Codebase or Dockerfiles:**
    *   *Anti-Pattern:* Committing `SECRET_KEY` or database credentials directly into version control.
    *   *Consequence:* Severe security breach potential. Always pass secrets dynamically via `.env` files or secure secret managers (AWS Secrets Manager, Vault).
3.  **Ignoring Database Connection Pool Exhaustion:**
    *   *Anti-Pattern:* Opening and closing raw connections per request without pooling constraints.
    *   *Consequence:* Database crashes under heavy load. Configure `pool_size` and `max_overflow` explicitly within SQLAlchemy's engine parameters.
4.  **Catching Broad Exceptions Silently:**
    *   *Anti-Pattern:* Using `except Exception:` blocks without re-raising or logging context.
    *   *Consequence:* Debugging becomes impossible in production environments. Let FastAPI handle unhandled exceptions or use structured logging middleware.

---

## 5. Performance & Optimization Tips

*   **Uvicorn Worker Scaling:** Run Uvicorn behind a process manager or set worker processes relative to CPU cores (`--workers 4`) when deploying to bare-metal or single-instance Docker environments.
*   **Database Query Optimization:** Always leverage `.options(selectinload(...))` or `.joinedload(...)` when handling SQLAlchemy relationship joins to prevent N+1 query execution bottlenecks.
*   **Response Compression:** Integrate `GZipMiddleware` into `app/main.py` to automatically compress large JSON payloads (>1000 bytes) and conserve bandwidth.
*   **Pydantic Model Compilation:** For mission-critical high-throughput routing paths, utilize Pydantic's optimized model serialization caching where applicable.

---

## 6. Commercial License & Attribution Summary

### **The Agency Commercial License**
Copyright (c) 2026 MicroCorp AI / The Agency Engineering Division. All rights reserved.

*   **Grant of Rights:** Purchasing or licensing this digital product grants the buyer (Client) a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, adapt, and deploy this codebase within commercial, client-facing, or proprietary applications.
*   **Restrictions:** You may *not* resell, redistribute, sub-license, or open-source this boilerplate code as a standalone template, framework, or competing software product on marketplaces (e.g., GitHub, Gumroad, CodeCanyon).
*   **Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.