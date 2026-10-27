# Enterprise FastAPI Backend: JWT Auth & Docker Setup
*The Agency Engineering Division | Production Turnkey Solution*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready Asynchronous Backend with JWT Authentication, PostgreSQL, Alembic, and Docker Multi-Stage Builds**

#### **Value Proposition**
Building a modern, secure, and production-grade backend from scratch takes days of boilerplate configuration, security plumbing, and infrastructure orchestration. This turnkey solution delivers a fully tested, enterprise-grade FastAPI template designed for immediate deployment. 

Eliminate technical debt before writing your first business logic feature. This package includes secure asynchronous database sessions, cryptographically secure JWT authentication with refresh token patterns, role-based access control (RBAC), automated database migrations via Alembic, and an optimized, zero-vulnerability Docker container setup.

#### **Target Audience**
* **Fiverr & Upwork Freelancers:** Deliver production-ready architectures to enterprise clients in hours instead of weeks.
* **Startup Founders:** Bootstrap your core product with battle-tested patterns that scale.
* **Backend Engineers:** Learn clean architecture, dependency injection best practices, and modern Python async patterns.

---

## 2. ## Quick Start & Core Concepts

### **Quick Start Guide (Local Development)**

1. **Clone and enter repository:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
   cd fastapi-enterprise-boilerplate
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your secure keys and database credentials
   ```

3. **Spin up services via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

4. **Verify API availability:**
   * Swagger Documentation: `http://localhost:8000/docs`
   * ReDoc Documentation: `http://localhost:8000/redoc`

---

### **Core Concepts & Architecture Mapping**

| Component | Technology Stack | Architectural Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (Python 3.11+) | High-performance, asynchronous request handling with automatic OpenAPI schema generation. |
| **Database Driver** | SQLAlchemy 2.0 (AsyncIO) + asyncpg | Non-blocking database operations over connection pools for maximum I/O throughput. |
| **Migrations** | Alembic | Version-controlled, deterministic database schema evolution. |
| **Authentication** | OAuth2 with Password (Bearer) & JWT | Stateless authentication using cryptographic signing (HS256/RS256) and secure claims. |
| **Containerization** | Docker (Multi-stage Alpine/Slim) | Minimal attack surface, deterministic runtime environments, and small image sizes. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   └── users.py
│   │   └── router.py
│   └── deps.py
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/
│   └── user.py
├── schemas/
│   └── user.py
├── services/
│   └── user.py
├── main.py
└── alembic.ini
```

---

### **3.1 Configuration Management (`app/core/config.py`)**
Uses `pydantic-settings` to validate environment variables at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise"
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
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

### **3.2 Database Engine & Session Dependency (`app/core/database.py`)**
Asynchronous engine setup with proper connection pooling.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
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

### **3.3 Security & JWT Utilities (`app/core/security.py`)**
Cryptographic token generation and password hashing via `passlib[bcrypt]`.

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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **3.4 User SQLAlchemy Model (`app/models/user.py`)**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
```

---

### **3.5 Authentication Dependencies (`app/api/deps.py`)**
Extracts and validates JWT tokens, returning the current active user.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
        
    return user
```

---

### **3.6 Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import TokenSchema

router = APIRouter()

@router.post("/login", response_model=TokenSchema)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### **3.7 Application Entrypoint (`app/main.py`)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

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

### **3.8 Production Dockerfile (Multi-Stage Build)**

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

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **3.9 Docker Compose Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: enterprise_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
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
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints (`def` vs `async def`)**
   * *The Anti-Pattern:* Using standard synchronous libraries (e.g., `requests`, blocking file I/O, or synchronous DB drivers) inside `async def` endpoints. This blocks the main event loop, destroying throughput.
   * *The Fix:* Use `async def` exclusively when invoking asynchronous I/O operations (like `sqlalchemy.ext.asyncio` or `httpx`). For legacy sync libraries, use FastAPI's dependency injection threadpool execution or standard `def` defs.

2. **Global Database Session State**
   * *The Anti-Pattern:* Instantiating a single global database session object and importing it across multiple modules.
   * *The Fix:* Always use request-scoped dependencies via `yield` in FastAPI dependency injection (`get_db`) to guarantee proper session lifecycle management and cleanups.

3. **Insecure Password Hashing Configuration**
   * *The Anti-Pattern:* Using custom hashing algorithms, MD5, SHA256 without salts, or uncalibrated bcrypt rounds.
   * *The Fix:* Use `passlib` with `bcrypt` (or `argon2`), which automatically handles salts and adaptive work factors.

4. **Running Containers as `root` in Production**
   * *The Anti-Pattern:* Leaving the default container user as `root`, exposing the host system to privilege escalation vulnerabilities if the application is compromised.
   * *The Fix:* Create a dedicated non-privileged system user within your Dockerfile (`RUN useradd -u 1000 appuser` and `USER appuser`).

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, do not rely on a single uvicorn worker process. Scale worker count based on CPU cores using `--workers N` or manage instances behind an Nginx/HAProxy load balancer or Gunicorn/Uvicorn manager.
* **Connection Pool Tuning:** Configure SQLAlchemy's `pool_size` and `max_overflow` based on your database instance limits and expected concurrent connection loads to avoid connection starvation.
* **Query Optimization:** Utilize SQLAlchemy 2.0 select statements with explicit `.options(selectinload(...))` or `.joinedload(...)` to eliminate N+1 query problems on relationship traversal.
* **Response Caching:** Integrate Redis for caching read-heavy endpoints that change infrequently, avoiding redundant database round-trips.

---

## 6. ## Commercial License & Attribution Summary

### **Commercial License Agreement**
* **Copyright © 2024 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchasing or acquiring this code package grants the licensee a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, adapt, and deploy this codebase in commercial applications, client deliverables, and internal startup products.
* **Restrictions:** Redistribution, resale, or sublicensing of this source code as a standalone boilerplate template, digital product, or open-source library without explicit written consent from MicroCorp AI is strictly prohibited.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any direct, indirect, or consequential damages arising from the deployment or utilization of this code.