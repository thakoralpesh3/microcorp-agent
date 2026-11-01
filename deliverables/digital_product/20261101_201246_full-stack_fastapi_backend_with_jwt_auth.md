# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Commercial Delivery Unit*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Boilerplate (JWT Auth + PostgreSQL + Docker)

#### The Problem
Building a production-grade backend from scratch is time-consuming and error-prone. Engineers spend dozens of hours wiring up database connections, configuring secure JWT authentication, structuring clean project hierarchies, and containerizing services for deployment.

#### The Solution
This turn-key, enterprise-grade FastAPI boilerplate provides a battle-tested architecture designed for immediate deployment. It comes pre-configured with industry best practices, asynchronous database sessions, secure password hashing, OAuth2 token handling, CORS middleware, and complete Docker orchestration. 

#### What You Get
* **Zero Setup Time:** Clone, run `docker compose up`, and hit the interactive Swagger documentation.
* **Security First:** Implements modern JWT (JSON Web Token) authentication with access/refresh token rotation and Bcrypt password hashing.
* **Modern Async Architecture:** Built natively on SQLAlchemy 2.0 async sessions and Pydantic v2 for maximum I/O performance.
* **Production Ready:** Includes health-check endpoints, structured environment variable validation, and a multi-stage Dockerfile optimized for minimal image size.

---

## 2. Quick Start & Core Concepts

### Architectural Overview
```
[ Client ] ---> ( Nginx / Reverse Proxy ) ---> [ FastAPI App (Uvicorn) ]
                                                        |
                                              (Async SQLAlchemy)
                                                        |
                                                [ PostgreSQL DB ]
```

### Clean Syntax & Configuration Table

| Component | Technology | Purpose / Configuration Rule |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance async request routing and auto-validation. |
| **Data Validation** | Pydantic v2 | Strict payload serialization and runtime type checking. |
| **ORM & Migrations**| SQLAlchemy 2.0 (Async) + Alembic | Non-blocking database interactions and schema version control. |
| **Authentication** | python-jose & passlib | HMAC-SHA256 JWT generation and secure password hashing. |
| **Containerization**| Docker & Docker Compose | Isolated multi-container environments for app and database. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```
fastapi-production-boilerplate/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1)
│   │   ├── endpoints/       # Auth, Users, Items
│   │   └── deps.py          # Dependency injections (DB, Current User)
│   ├── core/                # App config, security, database session
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic validation schemas
│   └── main.py              # Application entrypoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### Configuration Engine (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Production Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

---

### Asynchronous Database Engine (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URI, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
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

### Security & JWT Utilities (`app/core/security.py`)
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
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import auth, users

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])


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
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

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

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: postgres_password
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres_user -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    container_name: fastapi_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=postgres_password
      - POSTGRES_DB=production_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super_secret_access_key_change_me
      - JWT_REFRESH_SECRET_KEY=super_secret_refresh_key_change_me
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

❌ **Blocking I/O Operations in Async Routes**
* **The Mistake:** Using standard blocking libraries (like `requests` or synchronous DB drivers) inside `async def` route handlers, freezing the entire event loop.
* **The Fix:** Use native async drivers (`asyncpg`, `httpx`) or wrap blocking code using `run_in_threadpool`.

❌ **Hardcoding Secrets & Configuration**
* **The Mistake:** Placing database passwords or JWT secrets directly into codebase files.
* **The Fix:** Always utilize Pydantic `BaseSettings` combined with runtime `.env` injections.

❌ **Forgetting Database Session Cleanup**
* **The Mistake:** Manually opening sessions without proper context managers, leading to connection pool exhaustion.
* **The Fix:** Use FastAPI dependency injection (`Depends(get_db)`) to guarantee automatic session closing and transaction rollback on failure.

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** In production behind a reverse proxy (like Nginx), scale Uvicorn workers based on CPU cores rather than running a single instance:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
2. **Connection Pooling Tuning:** Adjust SQLAlchemy connection pool sizes (`pool_size`, `max_overflow`) depending on your database tier and expected concurrent load.
3. **Response Caching:** Leverage Redis for caching heavy read operations or frequently accessed static query results to minimize direct DB load.

---

## 6. Commercial License & Attribution Summary

* **License:** MIT License (Commercial Use, Modification, and Distribution Permitted).
* **Attribution:** Provided by **MicroCorp AI Engineering Division**. 
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. Always rotate default security keys and passwords before deploying to any production environment.