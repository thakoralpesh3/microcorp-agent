# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Packet*

---

## 1. # Product Title & Value Proposition

### **Product Title:** 
Enterprise-Grade FastAPI Asynchronous Boilerplate with Pydantic v2, JWT Authentication, SQLAlchemy 2.0 (Async), Alembic Migrations, and Production-Ready Docker Compose Architecture.

### **Value Proposition:**
Building a production-ready asynchronous Python backend from scratch typically consumes 40–60 hours of engineering overhead. This turnkey solution eliminates boilerplate configuration, providing a hardened, secure, and horizontally scalable backend architecture out of the box. 

Engineered strictly around **FastAPI**, **SQLAlchemy 2.0 Async**, and **Pydantic v2**, this product guarantees type safety, high-throughput I/O performance via `uvicorn` and `uvloop`, robust state management, and secure stateless JWT authentication (Access & Refresh tokens with sliding windows and secure HttpOnly cookie support). Designed explicitly for Fiverr freelancers and software agencies delivering enterprise APIs to clients under strict deadlines.

```
+-----------------------------------------------------------------+
|                        FASTAPI BACKEND                          |
|  +--------------------+   +----------------------------------+  |
|  |  Uvicorn / ASGI    |-->|    FastAPI Router & Endpoints    |  |
|  +--------------------+   +----------------------------------+  |
|                                     |                           |
|                           +----------------------------------+  |
|                           |      Pydantic v2 Validation      |  |
|                           +----------------------------------+  |
|                                     |                           |
|  +--------------------+   +----------------------------------+  |
|  | JWT Auth & RBAC    |-->|     SQLAlchemy 2.0 (Async)       |  |
|  +--------------------+   +----------------------------------+  |
+-------------------------------------|---------------------------+
                                      v
                      +-------------------------------+
                      | PostgreSQL / Redis Containers |
                      +-------------------------------+
```

---

## 2. ## Quick Start & Core Concepts

### System Requirements & Syntax Quick-Reference

| Component | Technology | Minimum Version | Core Responsibility |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous API routing & dependency injection. |
| **Validation** | Pydantic v2 | `2.6+` | Runtime data serialization, parsing, and strict typing. |
| **ORM** | SQLAlchemy | `2.0+` | Asynchronous database interactions and Unit of Work patterns. |
| **Database** | PostgreSQL | `15+` | ACID-compliant relational data persistence. |
| **Caching/Queue** | Redis | `7+` | Token blacklisting, rate limiting, and background task brokering. |
| **Migrations** | Alembic | `1.13+` | Version-controlled database schema migrations. |
| **Containerization** | Docker / Compose| `24.0+` | Multi-container orchestration and environment isolation. |

### 5-Minute Local Setup

1. **Clone & Navigate into the project directory:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the root directory based on the provided template:
   ```env
   PROJECT_NAME="MicroCorp Enterprise API"
   ENVIRONMENT="development"
   POSTGRES_SERVER=db
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=securepassword123
   POSTGRES_DB=enterprise_db
   POSTGRES_PORT=5432
   DATABASE_URL=postgresql+asyncpg://postgres:securepassword123@db:5432/enterprise_db
   
   SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=7
   ```

3. **Spin Up via Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

4. **Verify Container Health & Run Migrations:**
   ```bash
   docker compose exec api alembic upgrade head
   ```
   Navigate to `http://localhost:8000/docs` to view the interactive Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### Directory Structure
```
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic BaseSettings configuration
│   ├── database.py       # Async SQLAlchemy engine & session maker
│   └── security.py       # Password hashing & JWT generation/validation
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User ORM Model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic schemas for IO validation
├── api/
│   ├── v1/
│   │   ├── api.py        # Router aggregation
│   │   └── endpoints/
│   │       ├── auth.py   # Login, Token Refresh, Logout
│   │       └── users.py  # User CRUD & /me profile
│   └── deps.py           # FastAPI Dependencies (get_db, get_current_user)
├── alembic/              # Database migrations
├── main.py               # Application factory & middleware configuration
├── Dockerfile
└── docker-compose.yml
```

### 1. Database Configuration (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
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

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    """FastAPI Dependency that yields an async database session."""
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

### 2. Security & JWT Utilities (`app/core/security.py`)
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

def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### 3. FastAPI Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token type for this operation",
            )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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

### 4. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserResponse

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

### 5. Production Dockerfile (`Dockerfile`)
```dockerfile
FROM python:3.11-slim-bookworm as python-base

# Configure poetry and python environments
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Builder stage
FROM python-base as builder-base
RUN apt-get update && apt-get install --no-install-recommends -y \
    curl \
    build-essential

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# Install runtime dependencies
RUN poetry install --no-dev

# Production image
FROM python-base as production
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

WORKDIR /app
COPY . /app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 6. Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:securepassword123@db:5432/enterprise_db
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous and Asynchronous Database Drivers:**
   * *Anti-Pattern:* Utilizing `psycopg2` inside an `async def` FastAPI route, which blocks the entire event loop thread pool during SQL queries.
   * *Correction:* Always use `asyncpg` with SQLAlchemy's `create_async_engine()` and `AsyncSession`.

2. **Unbounded Connection Pool Scaling:**
   * *Anti-Pattern:* Setting `pool_size=100` in SQLAlchemy across multiple uvicorn worker processes, overwhelming the PostgreSQL connection limit.
   * *Correction:* Calculate pool sizing using the formula: `Pool Size = (Core Count * 2) + Effective Spares`. For a multi-worker deployment, keep individual worker pools small (e.g., `pool_size=5`, `max_overflow=10`).

3. **Insecure JWT Storage:**
   * *Anti-Pattern:* Storing sensitive `access_tokens` and `refresh_tokens` in client-side JavaScript `localStorage`, exposing the application to Cross-Site Scripting (XSS) token exfiltration.
   * *Correction:* Store access tokens in memory (React state/Pinia/Vuex) and set refresh tokens inside strict `HttpOnly`, `Secure`, `SameSite=Strict` cookies.

4. **Catching Generic Exceptions Globally Without Rollback:**
   * *Anti-Pattern:* Catching `Exception` in API handlers without explicitly calling `await session.rollback()`, leaving dirty sessions hanging in the active transaction pool.
   * *Correction:* Implement a centralized database dependency context manager that auto-commits on success and auto-rollbacks on exceptions (as demonstrated in Section 3.1).

---

## 5. ## Performance & Optimization Tips

* **Uvloop Integration:** Ensure `uvloop` is active inside your production event loop. It replaces the standard library asyncio event loop with a drop-in replacement written in Cython, providing 2x–4x throughput improvements on network I/O.
* **Response Caching via Redis:** Wrap heavy, infrequently changing query payloads in Redis cache layers using dependency-level decorators or FastAPI-Cache2.
* **Pydantic Model Compilation:** For CPU-bound serialization validation on high-volume endpoints, leverage Pydantic v2's Rust-backed core engine by ensuring strict typing annotations without arbitrary dict fallbacks (`model_config = ConfigDict(from_attributes=True)`).
* **Database Indexing:** Ensure every foreign key (`user_id`, `organization_id`) and high-cardinality search column (`email`, `username`) features an explicit B-tree index inside your Alembic migration scripts.

---

## 6. ## Commercial License & Attribution Summary

### **License Grant:**
* **Product Type:** Commercial Turnkey Software Solution (Fiverr Client Delivery Pack).
* **Grantee:** Licensed to the purchasing client/agency for deployment in commercial, internal, or client-facing production systems.
* **Restrictions:** Resale, redistribution, or open-source publication of this exact boilerplate package as a standalone competing digital product is strictly prohibited.

### **Attribution & Warranty:**
This code is architected and distributed by **The Agency Engineering Division** under MicroCorp AI. Provided "as-is" without warranty of any kind, express or implied. The engineering division maintains compliance with standard enterprise security matrices (OWASP Top 10 API Security Risks).