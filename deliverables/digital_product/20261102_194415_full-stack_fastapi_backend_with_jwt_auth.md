# FastAPI Production Blueprint: Full-Stack JWT Auth & Docker Setup
*MicroCorp AI Engineering Division | Backend Architecture Spec-Kit v4.2*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: JWT Auth, PostgreSQL, & Dockerized CI/CD**
*The turnkey, battle-tested backend architecture designed to save 40+ hours of boilerplate setup for enterprise clients and high-scale production systems.*

---

### **The Business Value**
- **Zero-to-Deployed in Minutes:** Fully containerized via Docker Compose with hot-reloading for development and multi-stage builds for production.
- **Enterprise Security Out-of-the-Box:** Implements OAuth2 with Password (and hashing via `passlib[bcrypt]`), stateless JSON Web Tokens (JWT) with expiration handling, and granular Role-Based Access Control (RBAC).
- **Asynchronous Scalability:** Built entirely on `async`/`await` paradigms, utilizing SQLAlchemy 2.0 asynchronous sessions paired with asyncpg for high-throughput database operations.
- **Strict Data Validation:** Leverages Pydantic v2 for lightning-fast runtime type checking, request deserialization, and automated OpenAPI (Swagger/ReDoc) documentation generation.

---

## 2. ## Quick Start & Core Concepts

### **Directory Architecture**
```text
fastapi-enterprise/
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
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### **Core Stack Syntax & Architectural Mapping**

| Component | Technology | Architectural Role | Production Consideration |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | Routing, validation, OpenAPI generation | Run via Uvicorn with Gunicorn worker management. |
| **ORM & Driver** | SQLAlchemy 2.0 + Asyncpg | Non-blocking database interactions | Always use `AsyncSession` context managers. |
| **Database** | PostgreSQL 15 | Relational persistence layer | Configure connection pooling (`pool_size`, `max_overflow`). |
| **Auth Engine** | PyJWT & Passlib | Token encoding/decryption & hashing | Rotate `SECRET_KEY` periodically via secret managers. |
| **Containerization**| Docker & Compose | Environment parity & isolation | Use multi-stage builds to minimize image footprint. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **A. Environment & Configuration (`app/core/config.py`)**
Using Pydantic Settings v2 for robust, validated environment variable parsing.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

settings = Settings()
```

---

### **B. Database Session Management (`app/core/database.py`)**
Asynchronous engine setup with proper connection lifecycle control.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
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

### **C. Security & JWT Utilities (`app/core/security.py`)**
Password hashing and token creation using standard cryptographic libraries.

```python
from datetime import datetime, timedelta, timezone
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### **D. Authentication Dependencies (`app/api/deps.py`)**
Extracting current user context from incoming bearer tokens.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
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
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
```

---

### **E. API Endpoints (`app/api/v1/endpoints/auth.py`)**
Login endpoint returning standardized JWT payloads.

```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
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
            detail="Inactive user"
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
```

---

### **F. Docker Configuration (`Dockerfile`)**
Multi-stage production-ready container definition.

```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

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

### **G. Service Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes:**
   * *Anti-Pattern:* Utilizing standard `requests` or blocking ORM queries inside an `async def` path operation. This starves the event loop.
   * *Correction:* Use `httpx` for asynchronous HTTP requests and SQLAlchemy's async session extensions for database calls.
2. **Hardcoding Application Secrets:**
   * *Anti-Pattern:* Keeping database passwords, API keys, or JWT secrets in plain text within code files.
   * *Correction:* Use Pydantic BaseSettings coupled with environment variables and secret injection managers (AWS Secrets Manager, HashiCorp Vault, or Docker Secrets).
3. **Improper Session Lifecycle Management:**
   * *Anti-Pattern:* Instantiating global database sessions that never close, leading to connection pool exhaustion.
   * *Correction:* Always use FastAPI's dependency injection system with `yield` context managers (`get_db`) to ensure automatic connection teardown.
4. **Neglecting Migration Version Control:**
   * *Anti-Pattern:* Altering database tables directly via raw SQL scripts or relying entirely on `Base.metadata.create_all()` in production.
   * *Correction:* Always use Alembic for version-controlled, rollback-capable schema migrations.

---

## 5. ## Performance & Optimization Tips

- **Uvicorn Worker Scaling:** In production environments behind a reverse proxy (like Nginx), scale Uvicorn workers using Gunicorn as a process manager:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
- **Database Connection Pooling:** Tune your SQLAlchemy connection pool parameters based on your server capacity and load profiles to avoid connection bottlenecks under high load:
  ```python
  engine = create_async_engine(
      settings.SQLALCHEMY_DATABASE_URI,
      pool_size=20,
      max_overflow=10,
      pool_timeout=30,
      pool_recycle=1800,
  )
  ```
- **Response Serialization Optimization:** For performance-critical read endpoints returning massive arrays, bypass standard Pydantic validation overhead when data structures are guaranteed safe, or use `orjson` as a drop-in high-performance JSON response replacement.

---

## 6. ## Commercial License & Attribution Summary

```text
====================================================================
MICROCORP AI COMMERCIAL SOFTWARE LICENSE AGREEMENT
====================================================================
Copyright (c) 2026 MicroCorp AI & Engineering Division. 
All rights reserved.

1. GRANT OF LICENSE: MicroCorp AI grants the purchaser (Client) a 
perpetual, non-exclusive, worldwide, commercial license to use, 
modify, adapt, and deploy this software boilerplate in internal and 
client-facing production applications.

2. RESTRICTIONS: Redistribution of this codebase as a standalone 
competing template, boilerplate generator, or commercial software 
kit is strictly prohibited without explicit written authorization.

3. DISCLAIMER: THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY 
OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE 
AND NONINFRINGEMENT.
====================================================================
```