# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Backend Architecture Series*

## 1. Product Title & Value Proposition

### Product Title
**Production-Grade FastAPI Async Backend Boilerplate: JWT Auth, PostgreSQL, SQLModel, & Dockerized CI/CD**

### Value Proposition
Stop wasting 40+ hours configuring boilerplate architecture, database migrations, security middleware, and containerization for every new client project. This battle-tested, asynchronous FastAPI backend template gives you an enterprise-grade foundation out of the box. 

Designed specifically for agency developers and freelancers building high-throughput APIs for Fiverr or direct clients, this turnkey solution includes secure HttpOnly cookie/Bearer JWT authentication, structured logging, dependency injection patterns, automated Alembic migrations, and multi-stage Docker builds. Deploy with confidence, scale seamlessly, and deliver projects 5x faster.

---

## 2. Quick Start & Core Concepts

### System Requirements & Prerequisites
* **Python**: `3.11+`
* **Docker & Docker Compose**: `v2.20+`
* **PostgreSQL**: `15+` (managed automatically via Docker)

### 5-Minute Quick Start
```bash
# 1. Clone or extract the repository
cd microcorp-fastapi-boilerplate

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your secure SECRET_KEY and database credentials

# 3. Spin up the infrastructure via Docker Compose
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec web alembic upgrade head

# 5. Access interactive API documentation
open http://localhost:8000/docs
```

### Core Architecture & Tech Stack Matrix

| Layer | Technology | Purpose & Design Decision |
| :--- | :--- | :--- |
| **Web Framework** | **FastAPI (v0.110+)** | High-performance asynchronous execution, automatic OpenAPI generation, strict Pydantic v2 validation. |
| **Database ORM** | **SQLModel** | Built on top of SQLAlchemy 2.0 and Pydantic; provides unified models for database tables and API validation. |
| **Database Migrations** | **Alembic** | Deterministic, version-controlled schema transformations mapped directly to SQLModel metadata. |
| **Authentication** | **PyJWT + Passlib** | Industry-standard stateless JSON Web Tokens with bcrypt password hashing and optional secure cookie transport. |
| **Containerization** | **Docker (Multi-stage)** | Optimized non-root production images minimizing attack surface area and final image size. |
| **Task Queue (Optional)**| **Celery + Redis** | Asynchronous background worker processing for heavy I/O tasks, emails, and webhooks. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-boilerplate/
├── alembic/                 # Database migration scripts
├── app/
│   ├── api/                 # API routers (v1)
│   │   ├── v1/
│   │   │   ├── endpoints/   # Auth, Users, Health
│   │   │   └── router.js    # Router aggregator (or api.py)
│   ├── core/                # Configuration, security, DB session
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/              # SQLModel database models
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   └── main.py              # Application entrypoint
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Local development orchestration
├── requirements.txt         # Pinned Python dependencies
└── .env.example             # Template environment variables
```

---

### Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    def model_post_init(self, __context) -> None:
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### Database Session & Dependency Injection (`app/core/database.py`)
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
    """Dependency yielding an async database session per request lifecycle."""
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
from datetime import datetime, timedelta, timezone
import jwt
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
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

---

### SQLModel Database Schema (`app/models/user.py`)
```python
from datetime import datetime, timezone
import uuid
from sqlmodel import Field, SQLModel

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False
    )
```

---

### Authentication API Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.token import Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, getting an access token for future requests."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(user.id, expires_delta=access_token_expires)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
```

---

### Application Entrypoint (`app/main.py`)
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections, cache pools, etc.
    print(f"Starting {settings.PROJECT_NAME}...")
    yield
    # Shutdown: Release resources
    print(f"Shutting down {settings.PROJECT_NAME}...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production for domain locking
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### Production Dockerfile (`Dockerfile`)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim-bookworm

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### Docker Compose Configuration (`docker-compose.yml`)
```yaml
version: "3.8"

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
      - POSTGRES_DB=production_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
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

1. **Blocking Synchronous I/O in Async Routes**
   * *Anti-Pattern*: Using standard libraries like `requests` or blocking ORM operations directly inside an `async def` path operation without `run_in_threadpool`. This halts the entire event loop.
   * *Correction*: Always use asynchronous drivers (`asyncpg`) and async database operations, or wrap blocking calls properly.

2. **Hardcoding Configuration & Secrets**
   * *Anti-Pattern*: Putting database passwords, JWT secret keys, or third-party API keys directly into Python files.
   * *Correction*: Always enforce environment-based configuration via Pydantic `BaseSettings`.

3. **Global Database Engine Instantiation without Connection Pooling Management**
   * *Anti-Pattern*: Creating a brand-new SQLAlchemy engine instance inside dependency functions or API endpoints, causing socket exhaustion.
   * *Correction*: Instantiate a single global engine with configured `pool_size` and `max_overflow`, yielding session instances per request.

4. **Ignoring Database Migration Rollbacks**
   * *Anti-Pattern*: Committing transactions manually without try/except/finally blocks, which risks leaving database sessions open and locking row access during runtime exceptions.
   * *Correction*: Utilize context managers or dependency generators that guarantee safe rollbacks and session closures.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling**: Run Uvicorn behind a process manager or specify multiple workers (`--workers 4`) scaled to available CPU cores inside containerized environments.
* **Database Query Optimization**: Leverage SQLAlchemy/SQLModel eager loading (`selectinload`) to eliminate N+1 query performance bottlenecks when fetching relational models.
* **Response Serialization Caching**: For read-heavy endpoints with static or semi-static data, implement Redis-based caching layers using FastAPI-Cache.
* **Gzip Compression**: Add FastAPI's built-in `GZipMiddleware` to automatically compress large JSON payloads and accelerate client response times over high-latency networks.

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 6. Commercial License & Attribution Summary

### MicroCorp Commercial Developer License (MCDL-v1.0)
* **Granted Rights**: You are authorized to use, modify, adapt, and rebrand this codebase for unlimited client projects, commercial software deliverables, and freelance platforms (e.g., Fiverr, Upwork).
* **Restrictions**: You **may not** resell, redistribute, or package this specific boilerplate template as a standalone competing template, course material, or open-source boilerplates library without prior written consent from MicroCorp AI.
* **Warranty Disclaimer**: Provided *"as is"* without warranty of any kind, express or implied. MicroCorp AI accepts no liability for direct or indirect damages resulting from the deployment of this code in production environments.

*© 2026 MicroCorp AI Engineering Division. All Rights Reserved.*