# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Client Delivery Specification*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, PostgreSQL, & Dockerized Microservices**

#### **Value Proposition**
Building production-ready asynchronous Python backends requires wiring together dozens of disparate components: secure password hashing, stateless JSON Web Token (JWT) authentication cycles, asynchronous database connection pooling, dependency injection, and deterministic containerization. 

This turnkey solution eliminates 80+ hours of boilerplate setup. It provides a battle-tested, type-safe, and fully asynchronous architecture designed to scale from day one. Hand-crafted for engineering teams and high-end freelance deliverables, this codebase implements modern Python best practices (Python 3.11+, Pydantic v2, SQLAlchemy 2.0 Async, and Alembic migrations) wrapped in a clean Docker Compose topology.

---

## 2. ## Quick Start & Core Concepts

### **The Architecture Stack**
*   **Web Framework:** FastAPI (ASGI via Uvicorn)
*   **Database ORM:** SQLAlchemy 2.0 (Async) + asyncpg driver
*   **Migrations:** Alembic
*   **Authentication:** OAuth2 with Password (Bearer), passlib (Bcrypt), python-jose (JWT)
*   **Containerization:** Docker & Docker Compose (Multi-stage builds)

### **Quick-Start Command Matrix**

| Action | Command | Description |
| :--- | :--- | :--- |
| **Clone & Setup** | `git clone <repo> && cd fastapi-boiler` | Initialize working directory |
| **Configure Env** | `cp .env.example .env` | Populate environment variables |
| **Launch Stack** | `docker compose up --build -d` | Spin up API, DB, and Adminer |
| **Run Migrations** | `docker compose exec api alembic upgrade head` | Apply latest DB schema revisions |
| **Test Suite** | `docker compose exec api pytest -v` | Execute asynchronous unit tests |

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi-backend/
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
└── .env
```

---

### **Core Implementation Files (Copy-Paste Ready)**

#### `app/core/config.py` (Environment Configuration via Pydantic Settings)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
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
    SQLALCHEMY_DATABASE_URI(str) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

#### `app/core/database.py` (Async SQLAlchemy Session Management)
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
    autocommit=False,
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

#### `app/core/security.py` (Password Hashing & JWT Token Generation)
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
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
```

#### `app/models/user.py` (SQLAlchemy 2.0 Async Model)
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
```

#### `app/api/deps.py` (FastAPI Dependency Injection for Authentication)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
        
    return user
```

#### `app/api/v1/endpoints/auth.py` (Authentication Router)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

#### `app/main.py` (ASGI Application Factory)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
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

@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

#### `Dockerfile` (Multi-Stage Production Build)
```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner

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

#### `docker-compose.yml` (Orchestration Specification)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: postgres_password
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres_user -d enterprise_db"]
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
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=postgres_password
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-jwt-key-change-in-production-123456
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1.  **Mixing Synchronous and Asynchronous Database Drivers:** Never use standard `psycopg2` or synchronous sessions inside async FastAPI route handlers. This blocks the event loop and completely destroys throughput. Always use `asyncpg` combined with `AsyncSession`.
2.  **Hardcoding Secrets in Code:** Never commit raw API keys, database URLs, or JWT secrets to source control. Always inject them via environment variables mapped through `pydantic-settings`.
3.  **Ignoring Database Connection Pool Limits:** Failing to configure `pool_size` and `max_overflow` on high-load applications will result in PostgreSQL connection exhaustion under heavy concurrent traffic.
4.  **Catching Global Exceptions Incorrectly:** Catching raw `Exception` broadly without rolling back the active SQLAlchemy transaction causes corrupted session states, leading to hanging API worker processes.
5.  **Running Migrations Inside the App Startup Lifecycle:** Running `alembic upgrade head` programmatically inside `main.py` causes race conditions in horizontal multi-container deployments. Run migrations as an explicit step in your CI/CD pipeline or Docker entrypoint wrapper.

---

## 5. ## Performance & Optimization Tips

*   **Uvicorn Worker Scaling:** In production, do not run a single Uvicorn process. Use a process manager like Gunicorn with Uvicorn worker classes (`gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`) matching your CPU core counts.
*   **Database Query Optimization:** Utilize SQLAlchemy's `selectinload` or `joinedload` strategies for relationship loading to avoid the N+1 query problem during serialization.
*   **Response Compression:** Enable Gzip middleware for large JSON payload outputs to reduce network transit time:
    ```python
    from fastapi.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    ```
*   **Token Payload Minimization:** Keep JWT claims minimal. Store only the user identifier (`sub`) inside the token payload to reduce overhead and network packet sizes. Fetch fresh permissions or roles directly from cache (Redis) or database when executing authorization checks.

---

## 6. ## Commercial License & Attribution Summary

### **Proprietary Turnkey Client License (MicroCorp AI)**

*   **Copyright (c) 2026 MicroCorp AI. All Rights Reserved.**
*   **Grant of Rights:** Upon full execution and clearance of associated milestone payments on platforms such as Fiverr, Upwork, or direct B2B invoicing, the client is granted a perpetual, non-exclusive, worldwide, royalty-free commercial license to modify, deploy, scale, and distribute this codebase within proprietary software products.
*   **Restrictions:** Redistribution of this specific boilerplate as an independent commercial template, framework, or open-source competing product without explicit written authorization from MicroCorp AI is strictly prohibited.
*   **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.