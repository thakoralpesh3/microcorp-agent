# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Commercial Product Suite*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, Async PostgreSQL, and Production Docker Architecture**

#### **Value Proposition**
Building secure, high-throughput asynchronous APIs from scratch wastes valuable engineering bandwidth. This production-ready turnkey solution provides a battle-tested, modular FastAPI backend architecture equipped with robust JWT authentication, role-based access control (RBAC), async database operations via SQLAlchemy 2.0, Alembic migrations, and an optimized, multi-stage Docker containerization pipeline. 

Designed for Senior Backend Engineers and enterprise agencies, this boilerplate saves over **40+ hours** of foundational setup, security hardening, and CI/CD structuring. Deploy with absolute confidence into AWS, GCP, or bare-metal environments.

---

## 2. ## Quick Start & Core Concepts

Get your local development environment running in under 60 seconds using Docker Compose.

### **Prerequisites**
- Docker Engine 24.0+ & Docker Compose v2+
- Python 3.11+ (if running bare-metal)

### **Rapid Deployment Guide**
```bash
# 1. Clone the repository and navigate to the root
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Configure your environment variables
cp .env.example .env
# (Optional: Modify secrets in .env if needed)

# 3. Spin up containers (PostgreSQL + FastAPI Application)
docker compose up --build -d

# 4. Verify health check
curl http://localhost:8000/health
```

### **Core Architectural Syntax & Concepts**

| Concept | Implementation Layer | Primary Purpose | Best Practice Standard |
| :--- | :--- | :--- | :--- |
| **Dependency Injection** | FastAPI `Depends` | Manages database sessions, auth state, and configuration. | Avoid global state; inject scoped sessions per request. |
| **Async ORM** | SQLAlchemy 2.0 (`AsyncSession`) | Non-blocking database I/O operations. | Use explicit `await` on all queries and commit/rollback blocks. |
| **Token Handling** | `python-jose` & `passlib` | Stateless JWT creation, validation, and bcrypt hashing. | Keep access token lifespans short (15-30m) with secure refresh tokens. |
| **Data Validation** | Pydantic v2 (`BaseModel`) | Strict request/response serialization and schema enforcement. | Leverage Field validators for custom input sanitization. |
| **Migrations** | Alembic | Track and execute incremental database schema changes. | Never modify production schemas manually; always generate scripts. |

---

## 3. ## Production Code Patterns & Architecture Examples

This repository follows a strict **Layered Modular Architecture** separating transport (routers), business logic (services), data persistence (models/repositories), and configuration.

### **Directory Structure**
```text
app/
├── core/               # Configuration, security, database connection
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/             # SQLAlchemy ORM Models
│   └── user.py
├── schemas/            # Pydantic Validation Models
│   └── user.py
├── api/                # API Routers (Endpoints)
│   ├── v1/
│   │   ├── api.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       └── users.py
│   └── deps.py         # Common FastAPI Dependencies
├── services/           # Business Logic Layer
│   └── user_service.py
└── main.py             # FastAPI Application Entrypoint
```

---

### **1. Core Configuration (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    # JWT Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### **2. Asynchronous Database Session (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
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


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### **4. Authentication Dependencies (`app/api/deps.py`)**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from sqlalchemy import select

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
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
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

### **5. Auth & Login Router (`app/api/v1/endpoints/auth.py`)**
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token, UserResponse

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
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }
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

### **7. Docker Compose Stack (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking I/O in Async Paths (`async def`)**:
   - *Anti-Pattern*: Using synchronous libraries like `requests` or standard `psycopg2` inside `async def` route handlers. This blocks the entire event loop.
   - *Fix*: Use `httpx` for async HTTP calls and `asyncpg` via SQLAlchemy async drivers for database interaction. If synchronous code must be run, use `run_in_threadpool`.

2. **Global Database Sessions**:
   - *Anti-Pattern*: Instantiating a single global `AsyncSession` object and importing it across multiple modules.
   - *Fix*: Use FastAPI's dependency injection (`Depends(get_db)`) to open and close sessions safely per HTTP request lifecycle.

3. **Exposing Raw ORM Models in Responses**:
   - *Anti-Pattern*: Returning SQLAlchemy model instances directly from route decorators (`return user_orm_object`). This risks exposing internal fields (like `hashed_password`) or triggering lazy-loading serialization errors.
   - *Fix*: Always validate and serialize outgoing data using Pydantic response models (`response_model=UserResponse`).

4. **Hardcoding Secret Keys & Configurations**:
   - *Anti-Pattern*: Writing JWT secrets and database credentials directly into python code.
   - *Fix*: Use Pydantic's `BaseSettings` combined with environment variables and secure secret management tools (AWS Secrets Manager, HashiCorp Vault).

---

## 5. ## Performance & Optimization Tips

- **Uvicorn Workers Scaling**: In production container environments, run Uvicorn behind a process manager like Gunicorn or scale instances via Kubernetes/Docker replicas rather than heavy multi-worker threading inside a single container.
- **Connection Pooling**: Configure SQLAlchemy connection pool sizes (`pool_size`, `max_overflow`) based on your database tier limitations to prevent connection starvation under high concurrent load.
- **Response Caching**: Implement Redis-backed caching layers for read-heavy endpoints that rarely change to bypass database roundtrips entirely.
- **Database Indexing**: Ensure high-cardinality lookup columns (such as `email` in user authentication tables) have explicit database indices defined in your SQLAlchemy models (`index=True`).

---

## 6. ## Commercial License & Attribution Summary

### **Commercial Distribution License**
Copyright © 2024 MicroCorp AI. All rights reserved.

- **Permitted Usage**: This digital asset is licensed for commercial deployment, client handoff, internal product development, and modification under the terms of the MicroCorp Commercial Engineering License.
- **Restrictions**: Redistribution, resale, or public publishing of this source code as a standalone boilerplate template on open-source marketplaces or template stores without explicit written consent is strictly prohibited.
- **Warranty Disclaimer**: Provided "as is", without warranty of any kind, express or implied. MicroCorp AI assumes zero liability for security misconfigurations or infrastructure vulnerabilities resulting from improper deployment.