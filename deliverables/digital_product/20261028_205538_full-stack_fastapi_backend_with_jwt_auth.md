# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend Boilerplate
**An Enterprise-Grade, Async-First API Architecture with JWT Authentication, PostgreSQL/SQLModel, Alembic Migrations, and Fully Containerized Docker Environments.**

---

### Why Buy / Use This Template?
Building modern web applications requires a robust, secure, and scalable backend foundation. Writing this boilerplate from scratch takes **40+ hours** of setup, debugging, security hardening, and structural design. 

This turnkey solution gives you an immediate production-ready architecture, saving your team weeks of engineering overhead. Whether you are delivering a turnkey project for a Fiverr client or bootstrapping your own SaaS, this kit provides enterprise-grade patterns out of the box.

### Key Value Pillars
- **Zero-Config Security:** Stateless JWT authentication utilizing secure cookie/header handling, password hashing via `bcrypt`, and granular role-based access control (RBAC).
- **Asynchronous Performance:** Built entirely on `async/await` paradigms using `SQLModel` and `SQLAlchemy 2.0` over async PostgreSQL drivers (`asyncpg`).
- **Bulletproof Migrations:** Pre-configured `Alembic` setup designed for zero-downtime database schema evolutions.
- **Developer Experience (DX):** Multi-stage Dockerfiles, hot-reloading development environments, and automated testing setups using `pytest`.

---

## 2. Quick Start & Core Concepts

### System Architecture Flow
```
[Client / Frontend] 
       │
       ▼ (HTTPS / Bearer Token)
[Nginx / Reverse Proxy] (Optional Production Layer)
       │
       ▼
[FastAPI Application Container]
 ├── Middleware (CORS, TrustedHost, Rate Limiting)
 ├── API Routers (/api/v1/auth, /api/v1/users, /api/v1/items)
 └── Dependency Injection (get_db, get_current_user)
       │
       ├─────────────────────────┐
       ▼                         ▼
[PostgreSQL Database]    [Redis Cache / Celery]
 (Async SQLAlchemy)       (Background Workers)
```

### Core Architecture Concepts & Syntax Map

| Concept | Implementation Layer | Primary Python / Docker Tool | Purpose & Description |
| :--- | :--- | :--- | :--- |
| **Data Validation** | Request / Response | `Pydantic v2` | Validates incoming payloads and serializes outgoing responses with high performance. |
| **Database ORM** | Data Persistence | `SQLModel` / `SQLAlchemy` | Type-hinted asynchronous object-relational mapping combining Pydantic and SQLAlchemy. |
| **Migrations** | Schema Versioning | `Alembic` | Tracks structural changes to the database and applies incremental updates safely. |
| **Authentication** | Security & Access | `python-jose` / `passlib` | Issues and verifies JSON Web Tokens (JWT) and securely hashes credentials. |
| **Containerization** | Infrastructure | `Docker` & `Docker Compose` | Isolates the application, database, and background workers into repeatable services. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-enterprise-boilerplate/
├── alembic/                      # Database migrations
│   └── versions/
├── app/
│   ├── api/                      # API Route handlers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   ├── core/                     # Configuration, security, database setup
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/                   # SQLModel database tables
│   │   └── user.py
│   ├── schemas/                  # Pydantic validation schemas
│   │   └── user.py
│   └── main.py                   # FastAPI application entrypoint
├── Dockerfile                    # Multi-stage production container
├── docker-compose.yml            # Local orchestration setup
├── requirements.txt              # Pinned Python dependencies
└── alembic.ini                   # Alembic configuration
```

---

### Configuration Engine (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    # Security / JWT
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
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### Asynchronous Database Setup (`app/core/database.py`)
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions per request."""
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

### Database Models (`app/models/user.py`)
```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
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
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
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

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### FastAPI Main Application Entrypoint (`app/main.py`)
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
    allow_origins=["*"],  # Modify in production to match exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Monitoring"])
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

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: fastapi_web
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_production
      - SECRET_KEY=supersecretkeychangethisinfullproduction12345
    depends_on:
      - db
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_production
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ 1. Mixing Synchronous Database Drivers in Async Endpoints
- **The Mistake:** Using standard `psycopg2` or sync session factories inside `async def` route handlers. This blocks the main event loop, causing total application latency spikes under concurrent request load.
- **The Fix:** Always use `asyncpg` combined with `create_async_engine` and `AsyncSession` from SQLAlchemy 2.0 / SQLModel.

### ❌ 2. Hardcoding Environment Secrets
- **The Mistake:** Storing JWT `SECRET_KEY`, database credentials, or API keys directly in `config.py` or version control.
- **The Fix:** Use `pydantic-settings` to enforce environment variable injection via `.env` files or orchestration secrets managers.

### ❌ 3. Failing to Handle DB Connection Lifecycles Properly
- **The Mistake:** Instantiating global database sessions that never close or commit incorrectly, resulting in connection pool exhaustion.
- **The Fix:** Use FastAPI's dependency injection (`Depends(get_db)`) to yield a scoped session per request with automated context managers (`try/except/finally`).

### ❌ 4. Ignoring Database Indexing on Foreign Keys and Lookups
- **The Mistake:** Querying large tables by unindexed fields like `email` or foreign keys without defining `index=True`.
- **The Fix:** Explicitly set `index=True` on frequently filtered columns in your SQLModel definitions.

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling with Gunicorn:** In production, run FastAPI behind Gunicorn utilizing Uvicorn worker classes to leverage multi-core CPUs:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
2. **Database Connection Pooling:** Fine-tune your database connection pool parameters (`pool_size`, `max_overflow`, `pool_timeout`) in `create_async_engine` based on your expected concurrency and database tier limitations.
3. **Response Model Compression:** Integrate standard GZip middleware for payloads exceeding 1KB to optimize network throughput:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```
4. **Caching Layer:** Introduce Redis caching for heavy read endpoints that rarely change to bypass database IO entirely.

---

## 6. Commercial License & Attribution Summary

### 📄 Commercial Terms of Use
- **License Type:** Single Developer / Commercial Client Delivery License.
- **Grant:** You are granted a perpetual, non-exclusive license to use, modify, adapt, and distribute this codebase within custom applications built for yourself or your clients (including Fiverr, Upwork, and direct agency contracts).
- **Restrictions:** You **may not** resell, re-license, or redistribute this template as a standalone boilerplate, open-source template, or digital product on marketplaces (e.g., Gumroad, GitHub, ThemeForest).
- **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The author/architect assumes no liability for security incidents or architectural misuse in production environments.