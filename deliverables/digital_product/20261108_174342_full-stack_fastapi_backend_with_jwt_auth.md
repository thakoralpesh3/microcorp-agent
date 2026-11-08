# 🚀 FastAPI Enterprise Blueprint: JWT Auth & Dockerized Turnkey Solution
*Engineered by MicroCorp AI Backend Architecture Division*

---

## 1. # Product Title & Value Proposition

### **Product Name:** 
`FastAPI-Enterprise-Core: Production-Grade Async Backend with JWT Auth, SQLAlchemy 2.0, and Docker Compose`

### **Value Proposition:**
Building a production-ready, secure, and performant backend from scratch takes days of boilerplate configuration, security hardening, and structural planning. **FastAPI-Enterprise-Core** is a battle-tested, fully decoupled turnkey template built for engineers, fractional CTOs, and agencies delivering high-end microservices or client MVPs. 

Eliminate technical debt before writing your first business logic feature. This package delivers an asynchronous SQLAlchemy 2.0 ORM layer, robust stateless JWT Authentication with automatic token expiration/refresh flows, environment-driven configuration via Pydantic v2, and a multi-stage Docker containerization pipeline optimized for immediate production deployment.

```
+-----------------------------------------------------------------------+
|                        FASTAPI ENTERPRISE CORE                        |
|                                                                       |
|  [ Nginx / Reverse Proxy ]                                            |
|            │                                                          |
|            ▼                                                          |
|  [ Docker Container: Uvicorn / FastAPI (Async) ]                      |
|       ├── Pydantic v2 Settings (Type Safe)                            |
|       ├── FastAPI Dependency Injection (Auth / DB Sessions)           |
|       └── SQLAlchemy 2.0 Async Session Factory                        |
|            │                                                          |
|            ▼                                                          |
|  [ External Services: PostgreSQL 16 (Pool) + Redis (Optional) ]      |
+-----------------------------------------------------------------------+
```

---

## 2. ## Quick Start & Core Concepts

### **Directory Structure**
```text
fastapi-enterprise-core/
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
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### **Core Architecture Syntax Table**

| Component | Technology | Architectural Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | High-performance ASGI framework with automatic OpenAPI documentation and strict Pydantic validation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database operations using `asyncio` and `greenlet` for maximum concurrent throughput. |
| **Migrations** | Alembic | Version-controlled database schema migrations tied directly to SQLAlchemy declarative models. |
| **Authentication** | OAuth2 with Password (Bearer) | Stateless JWT (JSON Web Tokens) with cryptographically secure hashing via `passlib[bcrypt]`. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds separating build tools from lightweight runtime images, complete with healthchecks. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **A. Configuration Management (`app/core/config.py`)**
Uses Pydantic BaseSettings to enforce strict runtime type-checking against environmental variables.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Core"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
```

### **B. Async Database Session Engine (`app/core/database.py`)**
Configures the asynchronous engine and sessionmaker for SQLAlchemy 2.0.

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URI,
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

async def get_db() -> AsyncSession:
    """Dependency function that yields db sessions per request."""
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

### **C. Security & JWT Utility (`app/core/security.py`)**
Handles password hashing and token generation.

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
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

### **D. Authentication Dependency (`app/api/deps.py`)**
Extracts and validates the bearer token, returning the current active user.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
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
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

### **E. Application Entrypoint (`app/main.py`)**
Assembles the FastAPI application instance and middleware stack.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production to specify domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

### **F. Multi-Stage Dockerfile (`Dockerfile`)**
Optimized for minimal image size and maximum caching performance.

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# If using requirements.txt, swap accordingly
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **G. Service Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  web:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangethis123456789
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16-alpine
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations inside Async Endpoints (`def` vs `async def`)**
   * *The Anti-Pattern:* Using standard synchronous libraries (like standard `requests` or blocking ORM patterns) directly inside an `async def` route path. This halts the entire event loop thread, defeating the purpose of asynchronous frameworks.
   * *The Fix:* Use `httpx` for async HTTP requests and SQLAlchemy 2.0 AsyncSessions. If you must use a blocking library, declare the endpoint with standard `def` so FastAPI runs it inside an external threadpool.

2. **Hardcoding Secrets and Configuration Values**
   * *The Anti-Pattern:* Keeping database passwords or JWT secret keys inside code files or committed `.env` files.
   * *The Fix:* Always use Pydantic `BaseSettings` populated entirely by runtime environment variables injected through Docker orchestrators or secret managers.

3. **Global Engine Instantiation Issues without Pool Configuration**
   * *The Anti-Pattern:* Instantiating database engines haphazardly without sizing `pool_size` and `max_overflow`, leading to connection starvation under sudden traffic surges.
   * *The Fix:* Always explicitly tune connection pools based on your hosting infrastructure's container memory limits.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling Behind Nginx:** In production environments, run Uvicorn behind an Nginx reverse proxy or leverage Gunicorn with Uvicorn worker classes (`gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`) to scale worker processes across available multi-core CPU architectures.
* **Database Indexing Strategy:** Ensure foreign keys and high-frequency search columns (such as `email` fields used during authentication lookups) are indexed explicitly at the SQLAlchemy model definition level:
  ```python
  email = Column(String, unique=True, index=True, nullable=False)
  ```
* **Response Serialization Optimization:** For endpoints returning high-volume lists of relational objects, utilize Pydantic's `model_validate` alongside lazy-loading strategies carefully to avoid N+1 query performance degradation.

---

## 6. ## Commercial License & Attribution Summary

```
====================================================================
MICROCORP AI COMMERCIAL SOFTWARE LICENSE AGREEMENT (MCSLA v1.0)
====================================================================
Copyright (c) 2026 MicroCorp AI. All rights reserved.

1. GRANT OF LICENSE: MicroCorp AI grants the purchaser (Client/Engineer) 
a perpetual, non-exclusive, worldwide, royalty-free commercial license 
to use, modify, adapt, and deploy this software template ("FastAPI-Enterprise-Core") 
within internal applications, client deliverables, and commercial SaaS products.

2. RESTRICTIONS: You may not resell, sub-license, or redistribute this 
codebase as a standalone template, boilerplate generator, or competing 
digital product on platforms like GitHub, Gumroad, or template marketplaces 
without explicit written authorization from MicroCorp AI.

3. WARRANTY DISCLAIMER: This software is provided "as is", without warranty 
of any kind, express or implied. MicroCorp AI shall not be held liable 
for any direct, indirect, incidental, or consequential damages arising 
out of the deployment or utilization of this code.
====================================================================
```