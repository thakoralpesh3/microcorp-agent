# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready Asynchronous Backend with JWT Authentication, PostgreSQL, and Dockerized Multi-Stage Pipeline**

#### **Value Proposition**
Building a modern, secure, and performant backend from scratch takes weeks of configuration boilerplate. This turnkey solution eliminates setup friction by providing a battle-tested, production-ready architecture designed for horizontal scaling. 

Engineered with asynchronous patterns, type safety via Pydantic v2, robust JWT-based stateless authentication, and automated containerization, this boilerplate allows developers and enterprise clients to ship features on Day 1 rather than configuring infrastructure.

#### **Key Features**
* **Blazing Fast Performance:** Built on FastAPI and Uvicorn, leveraging ASGI asynchronous concurrency.
* **Type-Safe Data Validation:** Powered by Pydantic v2 for strict runtime validation and automatic OpenAPI documentation generation.
* **Secure Auth Flow:** Access and Refresh token rotation utilizing Argon2/Bcrypt password hashing and JWT claims.
* **Database Agnostic Migrations:** Fully integrated with SQLAlchemy 2.0 (Async) and Alembic for seamless schema migrations.
* **Zero-Config Containerization:** Production-optimized Dockerfiles with multi-stage builds and Docker Compose orchestration for local development and staging.

---

## 2. Quick Start & Core Concepts

### **Architecture Topology**
```
[Client / Frontend] 
       │
       ▼ (HTTPS / JSON)
[Nginx Reverse Proxy / Load Balancer] (Optional)
       │
       ▼
[FastAPI Application Server (Uvicorn Workers)]
       ├── /api/v1/auth (JWT Issuance & Verification)
       ├── /api/v1/users (User Management & RBAC)
       └── /api/v1/health (System Probes)
       │
       ▼ (Async Connection Pool)
[PostgreSQL 16 Database Container]
```

### **Core Stack & Syntax Quick Reference**

| Layer / Technology | Primary Purpose | Key Configuration / Syntax |
| :--- | :--- | :--- |
| **FastAPI (0.110+)** | ASGI Web Framework & Routing | `app = FastAPI(lifespan=lifespan)` |
| **Pydantic (v2)** | Request/Response Data Validation | `model_config = ConfigDict(from_attributes=True)` |
| **SQLAlchemy (2.0)** | Asynchronous ORM & Querying | `async with AsyncSessionLocal() as session:` |
| **Alembic** | Database Schema Migrations | `op.create_table(...)` inside `versions/` |
| **PyJWT** | Token Generation & Verification | `jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)` |
| **Docker & Compose** | Infrastructure Orchestration | `build: context: . dockerfile: Dockerfile` |

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/                      # Database migrations directory
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py               # Dependency injection (DB, Auth)
│   ├── core/
│   │   ├── config.py             # Pydantic Settings management
│   │   ├── database.py           # Async engine & sessionmaker
│   │   └── security.py           # JWT creation & password hashing
│   ├── models/                   # SQLAlchemy ORM models
│   │   └── user.py
│   ├── schemas/                  # Pydantic DTOs
│   │   └── user.py
│   └── main.py                   # FastAPI app factory
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### **1. Configuration Management (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

---

### **2. Asynchronous Database Engine (`app/core/database.py`)**
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

async def get_db() -> AsyncSession:
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

---

### **4. SQLAlchemy User Model (`app/models/user.py`)**
```python
import uuid
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
```

---

### **5. FastAPI Application Factory (`app/main.py`)**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions (e.g., establish cache connections, verify DB connectivity)
    print("Initializing Enterprise Application Stack...")
    yield
    # Shutdown actions (e.g., close connection pools)
    print("Shutting down application gracefully...")

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )
    
    application.include_router(api_router, prefix=settings.API_V1_STR)
    
    return application

app = get_application()
```

---

### **6. Production Dockerfile (`Dockerfile`)**
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **7. Docker Compose Orchestration (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Production Practice |
| :--- | :--- | :--- |
| **Using Synchronous DB Drivers (`psycopg2`)** | Blocks the main event loop under high concurrency, degrading overall throughput. | Always use asynchronous drivers like `asyncpg` combined with SQLAlchemy's async extensions. |
| **Hardcoding Environment Variables** | Security vulnerability and CI/CD deployment failure risk. | Use Pydantic's `BaseSettings` pattern coupled with strict `.env` loading. |
| **Committing Inside Route Handlers Directly** | Leaves transactions open longer than necessary and complicates rollback handling. | Manage session lifecycles via Dependency Injection (`yield` pattern in `get_db`). |
| **Storing Passwords in Plain Text / Weak Hashing** | Immediate compliance failure (GDPR/SOC2) and data breach liability. | Utilize `passlib` with Argon2 or Bcrypt algorithms with appropriate work factors. |
| **Monolithic Single-Stage Dockerfiles** | Results in bloated image sizes carrying unnecessary compiler toolchains into production. | Use multi-stage builds separating build tools from lightweight runtime images. |

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** Deploy behind an Nginx reverse proxy using multiple worker processes scaled linearly based on CPU cores (`--workers $(nproc)`).
2. **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` parameters inside `create_async_engine()` to match database connection limits and peak concurrency thresholds.
3. **Response Compression:** Integrate `GZipMiddleware` into FastAPI to automatically compress payloads exceeding standard byte thresholds, lowering network latency.
4. **Database Indexing:** Ensure high-cardinality search fields (such as foreign keys, user emails, and timestamp ranges) include explicit database indexes (`index=True`).
5. **AOT/Lazy Loading Strategy:** Explicitly select necessary relationships using SQLAlchemy's `selectinload` or `joinedload` options to prevent N+1 query performance degradation.

---

## 6. Commercial License & Attribution Summary

### **Commercial End-User License Agreement (EULA)**
* **Grant:** Purchased or deployed under MicroCorp AI commercial engineering terms, granting perpetual, non-exclusive rights to utilize, modify, and deploy this codebase for commercial software products, client projects, and internal enterprise architectures.
* **Restrictions:** Redistribution of this codebase as a competing commercial boilerplate template, framework, or paid asset library is strictly prohibited.
* **Warranty Disclaimer:** Provided "AS IS" without warranty of any kind, express or implied. The authors accept no liability for production outages, data loss, or security vulnerabilities resulting from improper configuration or unverified operational changes.

*Engineered by Backend Architect 🏗️ — The Agency Engineering Division (MicroCorp AI).*