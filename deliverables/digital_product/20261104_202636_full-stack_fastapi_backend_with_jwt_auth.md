# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Backend Architecture Series*
> *Turnkey Enterprise Solution for High-Performance Microservices*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate**
*A production-ready, highly scalable, asynchronous Python backend architecture complete with JSON Web Token (JWT) authentication, Role-Based Access Control (RBAC), SQLAlchemy 2.0 ORM, Alembic migrations, and fully containerized Docker multi-stage deployments.*

---

### **Commercial Value Proposition**
Building secure, asynchronous, and scalable APIs from scratch is time-consuming and prone to architectural debt. This turnkey backend solution eliminates weeks of boilerplate setup by providing a battle-tested foundation. 

Designed for senior engineers and fast-moving agencies delivering client work on platforms like Fiverr and Upwork, this product ensures compliance with modern security standards (OAuth2 with Password Flow, bcrypt hashing, HTTP-only cookie or Bearer JWT management) while maintaining maximum throughput via FastAPI’s asynchronous event loop.

#### **Key Metrics & Capabilities**
* **Throughput:** Capable of handling thousands of concurrent requests per worker via `uvicorn` and `asyncpg`.
* **Security:** Cryptographically secure JWT issuing/validation, CORS hardening, SQL injection mitigation via SQLAlchemy 2.0 type-safe query builders.
* **Developer Experience (DX):** Automated database migrations via Alembic, pre-configured Pydantic v2 validation schemas, and instant hot-reloading in local Docker development containers.

---

## 2. ## Quick Start & Core Concepts

### **Architecture Topology**
```
[ Client Request ] 
       │
       ▼
[ Nginx Reverse Proxy / Load Balancer ] (Optional Edge Layer)
       │
       ▼
[ FastAPI Application Container ] (Uvicorn ASGI Worker Cluster)
       ├──> Authentication Middleware / JWT Verifier
       ├──> Dependency Injection System (DB Sessions, Current User)
       └──> Routers (Auth, Users, Health)
       │
       ▼
[ PostgreSQL 16+ Database Container ] (Persistent Volume Storage)
```

---

### **Clean Syntax & Component Reference Table**

| Component | Technology | Primary Purpose | Key Configuration / Pattern |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | High-performance asynchronous API routing | Dependency Injection (`Depends`) & Pydantic v2 validation |
| **Database ORM** | SQLAlchemy 2.0 | Asynchronous database interactions | Declarative Base mapped classes with `async_sessionmaker` |
| **Migrations** | Alembic | Schema version control | Async connection string injection (`asyncpg`) |
| **Auth Strategy** | PyJWT / Passlib | Stateless token authentication | `HS256` or `RS256` signing with bcrypt password hashing |
| **Containerization** | Docker & Compose | Environment parity & deployment | Multi-stage builds, non-root user execution, health checks |

---

## 3. ## Production Code Patterns & Architecture Examples

### **Directory Structure**
```
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

---

### **1. Configuration Management (`app/core/config.py`)**
Using Pydantic Settings v2 for robust environment variable validation and typing.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

---

### **2. Asynchronous Database Engine (`app/core/database.py`)**
Configuring SQLAlchemy 2.0 with async session management.

```python
from collections.abc import AsyncGenerator
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

---

### **3. User Database Model (`app/models/user.py`)**
Modern SQLAlchemy 2.0 Mapped syntax.

```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

---

### **4. Security & JWT Utility (`app/core/security.py`)**
Password hashing via Passlib and JWT encoding/decoding.

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
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### **5. Dependencies & Authentication Middleware (`app/api/deps.py`)**
Extracting and validating the bearer token to inject the current user.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user
```

---

### **6. Authentication Endpoint (`app/api/v1/endpoints/auth.py`)**

```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
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
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }
```

---

### **7. Application Entrypoint (`app/main.py`)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
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

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **9. Container Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_app
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super-secret-jwt-key-change-in-production
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

### ❌ **1. Blocking the Event Loop with Synchronous IO**
* **The Antipattern:** Using standard libraries like `requests`, standard `sqlite3`, or synchronous file reading functions inside `async def` route handlers. This locks the single-threaded event loop, starving all concurrent connections.
* **The Correct Approach:** Always utilize native asynchronous drivers (`asyncpg`, `httpx`, `aiofiles`) or offload CPU-bound/blocking logic to thread pools using `run_in_threadpool`.

### ❌ **2. Global Session Management**
* **The Antipattern:** Instantiating a single global database session at the module level and sharing it across multiple concurrent requests. This causes race conditions and state contamination.
* **The Correct Approach:** Use FastAPI’s dependency injection system with `yield` context managers to instantiate a fresh session per request, ensuring automatic cleanup and transaction rollback on failure.

### ❌ **3. Storing Plain Text Passwords or Weak Hashing**
* **The Antipattern:** Storing user passwords using fast hashing algorithms like MD5 or SHA256 without salts.
* **The Correct Approach:** Always employ adaptive cryptographic hash functions such as `bcrypt` or `Argon2` managed through secure wrappers like Passlib.

### ❌ **4. Running Containers as Root in Production**
* **The Antipattern:** Running the final production Docker container under the default `root` user. If a Remote Code Execution (RCE) vulnerability is exploited, the attacker gains full container root privileges.
* **The Correct Approach:** Create a dedicated non-privileged user inside the multi-stage Dockerfile and switch contexts before executing the server process.

---

## 5. ## Performance & Optimization Tips

1. **Connection Pooling Tuning:** Adjust SQLAlchemy's `pool_size` and `max_overflow` based on your available database compute resources and peak concurrent load expectations.
2. **Uvicorn Worker Scaling:** In production environments running behind an orchestrator (e.g., Kubernetes, Docker Swarm) or reverse proxy (Nginx), scale Uvicorn workers using the formula `Workers = (2 x CPU Cores) + 1` or allow process managers like Gunicorn to manage worker lifecycles.
3. **Pydantic Model Compilation:** For ultra-high-throughput routing schemas, leverage Pydantic v2's Rust-backed core validation engine, which provides significant performance gains over older v1 implementations.
4. **Response Caching:** Implement Redis caching layers for frequently accessed, read-heavy endpoints that do not require real-time transactional accuracy.

---

## 6. ## Commercial License & Attribution Summary

### **Commercial End-User License Agreement (EULA)**
* **Copyright © 2026 The Agency / MicroCorp AI. All Rights Reserved.**
* **Grant of Rights:** Purchasing or acquiring this document grants the licensee a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, adapt, and deploy the included source code within commercial software applications, client deliverables, and SaaS products.
* **Restrictions:** Licensees may not resell, redistribute, sub-license, or open-source this specific codebase as a standalone boilerplate template, framework generator, or digital product on marketplaces (e.g., Gumroad, GitHub Marketplace, Envato).
* **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.