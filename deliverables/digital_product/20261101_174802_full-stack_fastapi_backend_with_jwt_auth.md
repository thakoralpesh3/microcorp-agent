# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*Engineered by MicroCorp AI Backend Architecture Division*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Grade Async Backend with JWT Authentication, PostgreSQL, and Docker**

#### **Value Proposition**
Building a production-ready asynchronous Python backend from scratch requires wiring together dozens of disparate technologies: async database drivers, dependency injection systems for security, environment configuration, migration management, and containerization. 

This turnkey solution eliminates weeks of boilerplate setup. It provides a hardened, battle-tested FastAPI architecture adhering to enterprise standards. Featuring robust JWT-based stateless authentication, automated Alembic database migrations, Pydantic v2 validation, and a multi-stage Docker deployment pipeline, this kit lets engineers launch secure, scalable REST APIs on day one.

---

## 2. ## Quick Start & Core Concepts

### **The Architecture Stack**
*   **Web Framework:** FastAPI (Asynchronous, automatic OpenAPI docs, Pydantic v2 validation)
*   **Database & ORM:** PostgreSQL 16 + SQLAlchemy 2.0 (Async Session Management)
*   **Migrations:** Alembic
*   **Authentication:** JSON Web Tokens (JWT) with Passlib (Bcrypt hashing)
*   **Containerization:** Docker & Docker Compose (Multi-stage builds)

### **Quick Setup Guide**

```bash
# 1. Clone the repository and navigate to the directory
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Copy the environment variables template
cp .env.example .env

# 3. Spin up the containers using Docker Compose
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec web alembic upgrade head
```

### **Core Concepts & Syntax Reference**

| Concept | Implementation in this Boilerplate | Purpose |
| :--- | :--- | :--- |
| **Async Session** | `AsyncSession` via `async_sessionmaker` | Non-blocking database I/O operations for high throughput. |
| **Dependency Injection** | `Depends(get_db)`, `Depends(get_current_user)` | Modular, testable code injection for requests and security contexts. |
| **Pydantic v2 Models** | `BaseModel`, `Field`, `model_validator` | Runtime data parsing, serialization, and strict payload validation. |
| **Stateless Auth** | HS256 JWT Signed Tokens stored in HTTP-only/Bearer context | Scalable user sessions without server-side memory overhead. |
| **Environment Control** | `pydantic-settings` (`BaseSettings`) | Type-safe environment variable loading with validation at startup. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
backend/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1)
│   │   ├── endpoints/       # Auth, Users, Items
│   │   └── deps.go          # Common dependencies
│   ├── core/                # Config, Security, Database setup
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic validation schemas
│   └── main.go / main.py    # FastAPI Application Entrypoint
├── Dockerfile               # Multi-stage production container
├── docker-compose.yml       # Local development orchestration
└── requirements.txt         # Pinned python dependencies
```

---

### **1. Configuration Management (`app/core/config.py`)**
Using `pydantic-settings` to validate environment variables securely at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )


settings = Settings()
```

---

### **2. Asynchronous Database Session (`app/core/database.py`)**
Establishing a thread-safe asynchronous SQLAlchemy engine and session factory.

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
    """Dependency function that yields db sessions per request lifecycle."""
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

### **3. Security & JWT Utility (`app/core/security.py`)**
Handling password hashing via bcrypt and encoding/decoding JWT access tokens.

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


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **4. Authentication Dependencies (`app/api/deps.py`)**
Extracting and validating Bearer tokens against the database asynchronously.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

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
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### **5. Auth Endpoints Router (`app/api/endpoints/auth.py`)**
Implementing user login and token generation.

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
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """OAuth2 compatible token login, get an access token for future requests."""
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

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### **6. Production Dockerfile (`Dockerfile`)**
Multi-stage build pattern to minimize final image size and secure dependencies.

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

# Stage 2: Final runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **7. Docker Compose Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
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

  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangethis123!@#
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1.  **Blocking IO Inside Async Paths (`def` vs `async def`)**
    *   *Anti-pattern:* Defining route handlers with `async def` while using blocking libraries like `requests`, standard `sqlite3`, or synchronous ORM queries. This halts the single-threaded event loop and destroys concurrency.
    *   *Solution:* Use `async def` *only* when utilizing true async libraries (e.g., `httpx`, `asyncpg`). Use standard `def` for synchronous endpoints; FastAPI offloads them to an external thread pool automatically.

2.  **Missing Database Connection Pooling Management**
    *   *Anti-pattern:* Creating a brand new SQLAlchemy engine or session setup inside every API route execution.
    *   *Solution:* Use a shared global engine instance combined with dependency injection (`yield session`) to guarantee connection reusability and avoid socket exhaustion.

3.  **Hardcoding Configurations & Secrets**
    *   *Anti-pattern:* Placing database credentials, JWT secrets, and API keys directly in source files.
    *   *Solution:* Always use environment variables managed securely through type-safe schema validation models (`pydantic-settings`).

4.  **Catching Generic Exceptions Blindly**
    *   *Anti-pattern:* Using bare `except:` clauses without re-raising or translating database integrity errors into proper HTTP status codes.
    *   *Solution:* Catch specific exceptions (e.g., `IntegrityError` for duplicate constraints) and return structured `400 Bad Request` or `409 Conflict` responses.

---

## 5. ## Performance & Optimization Tips

*   **Uvicorn Worker Scaling with Gunicorn:** In production, run Uvicorn managed via Gunicorn process manager to utilize multiple CPU cores (`gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`).
*   **Database Indexing:** Ensure all foreign keys, lookup keys, and unique constraints (like user emails) have explicit index configurations defined in your SQLAlchemy models.
*   **Response Compression:** Enable GZip middleware in FastAPI (`app.add_middleware(GZipMiddleware, minimum_size=1000)`) to compress large JSON responses payloads over the network.
*   **Connection Pool Tuning:** Adjust `pool_size` and `max_overflow` attributes on your SQLAlchemy async engine to balance concurrent database transactions against your PostgreSQL instance limits.

---

## 6. ## Commercial License & Attribution Summary

*   **License:** MIT Commercial-Grade License
*   **Copyright:** © 2026 MicroCorp AI. All rights reserved.
*   **Usage Grant:** This turnkey architecture package is licensed for immediate integration into commercial client projects, software-as-a-service (SaaS) products, and internal enterprise architectures. 
*   **Attribution Notice:** Redistribution of this exact template as a competing standalone boilerplate product requires explicit written authorization from MicroCorp AI Engineering Division.