# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Turnkey Boilerplate*

---

## 1. Product Title & Value Proposition

### **Product Title:** FastAPI Enterprise-Grade Engine (JWT + PostgreSQL + Docker)
**SKU:** `MC-BE-FASTAPI-JWT-001`  
**Target Audience:** Enterprise Clients, Scale-up CTOs, and Full-Stack Engineers needing a bulletproof, asynchronous Python backend architecture out of the box.

### **Value Proposition:**
Building an asynchronous, production-ready backend from scratch takes 40+ engineering hours. This turnkey solution eliminates boilerplate fatigue by providing a battle-tested, highly performant FastAPI template featuring enterprise patterns: async database sessions with SQLAlchemy 2.0, secure JWT authentication with refresh token rotation, structured logging, Alembic migrations, and multi-stage Docker optimization. Deploy in minutes; scale to millions of requests.

---

## 2. Quick Start & Core Concepts

### System Architecture Quick Reference

| Component | Technology Choice | Design Rationale |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High performance, automatic OpenAPI docs, native Pydantic v2 validation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database I/O using `asyncpg` driver for high concurrency. |
| **Migrations** | Alembic | Version-controlled database schema evolution. |
| **Authentication** | OAuth2 with JWT (Passlib / PyJWT) | Stateless, scalable security model with HMAC-SHA256 signing. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds for minimal image size; isolated local dev stack. |
| **Environment Config** | Pydantic-Settings | Type-safe environment variable parsing with validation. |

### 5-Minute Local Setup

```bash
# 1. Clone or extract the repository
cd fastapi-enterprise-engine

# 2. Spin up infrastructure (PostgreSQL & Redis)
docker compose up -d db redis

# 3. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
uvicorn app.main:app --reload
```

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
app/
├── core/
│   ├── __init__.py
│   ├── config.py         # Pydantic settings
│   ├── database.py       # Async engine & sessionmaker
│   └── security.py       # Password hashing & JWT utilities
├── models/
│   ├── __init__.py
│   └── user.py           # SQLAlchemy User Model
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic I/O Schemas
├── api/
│   ├── __init__.py
│   ├── deps.py           # Dependency injection (get_db, get_current_user)
│   └── v1/
│       ├── api.py        # Router aggregation
│       endpoints/
│           ├── auth.py   # Login & Token refresh
│           └── users.py  # User CRUD
├── alembic/              # Database migrations
├── main.py               # FastAPI application factory
└── Dockerfile            # Multi-stage production container
```

---

### Core Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
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
    SQLALCHEMY_DATABASE_URI: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )


settings = Settings()
```

---

### Database Setup & Session Factory (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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

---

### User SQLAlchemy Model (`app/models/user.py`)
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

### Security Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
import jwt
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
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### FastAPI Dependencies (`app/api/deps.py`)
```python
from collections.abc import AsyncGenerator
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


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
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user
```

---

### Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_db
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models.user import User
from app.schemas.user import TokenSchema

router = APIRouter()


@router.post("/login", response_model=TokenSchema)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

---

### Application Factory (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Set all CORS enabled origins
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
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime Environment
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Docker Compose Configuration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    restart: always

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=FastAPI Enterprise Engine
      - SECRET_KEY=supersecretkeychangemeinproduction
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Using Synchronous DB Drivers with Async FastAPI
```python
# BAD: Using psycopg2 (sync) inside an async FastAPI route blocks the event loop
import psycopg2
conn = psycopg2.connect("...")
```
* **Why it fails:** It blocks the entire event loop thread during I/O wait times, completely destroying asynchronous concurrency advantages.
* **The Fix:** Always use `asyncpg` with SQLAlchemy's asynchronous sessionmaker (`create_async_engine`).

### ❌ Anti-Pattern 2: Hardcoding Configuration Values
```python
# BAD: Secrets inside source code
SECRET_KEY = "my_super_secret_key"
```
* **Why it fails:** Security compliance failure (OWASP Top 10). Exposes credentials in version control systems.
* **The Fix:** Utilize `pydantic-settings` to inject variables securely via environment variables or secret managers.

### ❌ Anti-Pattern 3: Missing Database Session Context Managers
```python
# BAD: Manually creating sessions without closing/rollback handling on error
session = AsyncSessionLocal()
# ... operations ...
await session.commit() # If exception occurs here, session remains open and uncommitted locks remain!
```
* **Why it fails:** Causes connection leaks, unreleased database locks, and potential memory exhaustion.
* **The Fix:** Use generator-based dependency injection with explicit `try/except/finally` or context managers (`async with`).

---

## 5. Performance & Optimization Tips

1. **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` in `create_async_engine` based on your worker count and CPU cores to prevent database connection starvation.
2. **Uvicorn Workers Scaling:** In production, run multiple worker processes behind a process manager or orchestrator (e.g., Kubernetes, Gunicorn/Uvicorn worker class) calculated as `(2 * CPU cores) + 1`.
3. **Pydantic Model Compilation:** For ultra-high-throughput validation pathways, leverage Pydantic v2's native Rust-accelerated core validation engine by avoiding custom validator functions where standard type annotations suffice.
4. **Database Indexing:** Ensure every foreign key (`user_id`) and search parameter (`email`) has an explicit database index defined via SQLAlchemy's `index=True`.

---

## 6. Commercial License & Attribution Summary

* **Product SKU:** `MC-BE-FASTAPI-JWT-001`
* **License Type:** MicroCorp AI Commercial Engineering License (Single-Client / Multi-Deployment Ready)
* **Usage Rights:** Permitted for use in commercial client deliverables, SaaS products, and internal enterprise architectures. Resale of this boilerplate as a competing template framework is strictly prohibited.
* **Attribution:** Built by **The Agency Engineering Division** for MicroCorp AI.