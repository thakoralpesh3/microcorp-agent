# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Backend Architecture*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready Asynchronous Backend with JWT Authentication, PostgreSQL, and Docker**

Stop spending 40+ hours setting up boilerplate architecture, database migrations, security layers, and containerization for every new client project. This production-grade turnkey solution provides a fully asynchronous, highly scalable backend designed for high-performance SaaS applications and enterprise APIs.

#### **Core Value Proposition**
* **Time-to-Market Acceleration:** Deploy a fully secure, database-backed API with authentication in under 10 minutes.
* **Modern Tech Stack:** Built on Python 3.11+, FastAPI (ASGI), SQLAlchemy 2.0 (Async), Alembic, Pydantic v2, and PostgreSQL 15, containerized via Docker Compose.
* **Enterprise Security:** Implements stateless JWT (JSON Web Tokens) with access/refresh token rotation, password hashing via `passlib[bcrypt]`, CORS middleware, and environment-based secret management.
* **Developer Experience:** Fully typed codebase with strict Pydantic v2 validation, automated database migrations, and clean architectural separation of concerns.

---

## 2. ## Quick Start & Core Concepts

### **Architecture Core Concepts & Syntax Reference**

| Component | Technology Choice | Architectural Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous API routing, auto-generated OpenAPI/Swagger docs. |
| **Database Driver** | `asyncpg` + SQLAlchemy 2.0 | Non-blocking database I/O for maximum concurrency and throughput. |
| **Migration Engine** | Alembic | Version-controlled, deterministic database schema migrations. |
| **Authentication** | OAuth2 with Password (JWT) | Stateless, cryptographically signed tokens (`HS256` / `RS256`). |
| **Validation** | Pydantic v2 | Strict runtime data parsing, serialization, and settings management. |
| **Containerization** | Docker & Docker Compose | Isolated, reproducible development and production environments. |

### **5-Minute Quick Start**

```bash
# 1. Clone or extract the boilerplate repository
cd fastapi-enterprise-boilerplate

# 2. Configure environment variables
cp .env.example .env
# Edit .env and set your secure POSTGRES_PASSWORD and SECRET_KEY

# 3. Spin up services using Docker Compose
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head

# 5. Access interactive API documentation
open http://localhost:8000/docs
```

---

## 3. ## Production Code Patterns & Architecture Examples

This boilerplate uses a modular, domain-driven structure:

```text
fastapi-enterprise-boilerplate/
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
└── .env.example
```

### **1. Configuration Management (`app/core/config.py`)**

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

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

### **2. Asynchronous Database Engine (`app/core/database.py`)**

```python
from typing import AsyncGenerator
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

### **3. Cryptography & JWT Security (`app/core/security.py`)**

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

### **4. SQLAlchemy User Model (`app/models/user.py`)**

```python
import uuid
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import engine
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

### **5. FastAPI Authentication Dependencies (`app/api/deps.py`)**

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
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
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

### **6. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**

```python
from datetime import timedelta
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
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
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
```

### **7. Main Application Entrypoint (`app/main.py`)**

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
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

### **8. Multi-Stage Production Dockerfile (`Dockerfile`)**

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

# Stage 2: Runtime Image
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

### **9. Orchestration Configuration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
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
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Paths:**
   * *Anti-Pattern:* Using standard `requests` library or synchronous database queries inside an `async def` path operation without `run_in_threadpool`. This freezes the entire event loop.
   * *Correction:* Use `asyncpg` and SQLAlchemy's async session. For third-party blocking HTTP calls, use `httpx.AsyncClient`.

2. **Hardcoding Environment Secrets:**
   * *Anti-Pattern:* Storing database credentials or JWT `SECRET_KEY` directly inside Python files.
   * *Correction:* Always validate configuration via Pydantic `BaseSettings` reading from explicit `.env` files or secure container secret stores (AWS Secrets Manager, Vault).

3. **Missing Database Session Context Management:**
   * *Anti-Pattern:* Instantiating database sessions manually in endpoints without `try/except/finally` blocks, leading to connection leaks and uncommitted transactions.
   * *Correction:* Use FastAPI's dependency injection system (`Depends(get_db)`) to guarantee connection cleanup and automatic rollback on failure.

4. **N+1 Database Query Traps:**
   * *Anti-Pattern:* Accessing related models in a loop (e.g., `user.posts`) without preloading relationships using `selectinload` or `joinedload`.
   * *Correction:* Explicitly leverage SQLAlchemy 2.0 loader options for eager loading.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, run Uvicorn behind an ASGI manager or scale worker processes according to your CPU core count (Formula: `2 * $CPU_CORES + 1`).
* **Connection Pooling:** Configure optimal `pool_size` and `max_overflow` parameters in `create_async_engine` to match database maximum connection limits.
* **Database Indexing:** Ensure foreign keys and high-cardinality search columns (such as user email addresses and tokens) have explicit database indices (`index=True`).
* **Response Serialization:** For large datasets, leverage Pydantic's `.model_dump()` performance tuning or return raw dicts when maximum throughput is required over schema validation.

---

## 6. ## Commercial License & Attribution Summary

### **Commercial Distribution License**
* **Single-Developer / Freelancer Commercial License:** Granted to the purchasing entity for deployment across unlimited client projects, SaaS products, and internal applications.
* **Restrictions:** Redistribution of this codebase as a standalone boilerplate template, open-source framework, or commercial code competitor is strictly prohibited.
* **Warranty:** Provided *as-is* without warranty of any kind. MicroCorp AI Engineering Division disclaims all liability for direct or indirect damages resulting from the deployment of this architecture.

*© 2024 MicroCorp AI. All Engineering Rights Reserved.*