# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Commercial Product Suite*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate with Secure JWT Authentication & Production Docker Deployment**

> **Turnkey Solution for Professional Engineers & Enterprise Clients**
> Stop wasting 40+ hours writing boilerplate authentication, database migrations, and containerization pipelines. This enterprise-ready FastAPI template gives you a bulletproof, secure, and horizontally scalable backend architecture out of the box.

### **Core Value Proposition**
* **Time-to-Market Acceleration:** Deploy a fully authenticated, database-backed REST API in under 5 minutes.
* **Security First:** Built-in OAuth2 with Password (and hashing), stateless JSON Web Tokens (JWT), refresh token rotation, and robust CORS/CSRF middleware.
* **Production-Ready Containers:** Multi-stage Dockerfiles optimized for minimal image footprint and maximum security (non-root execution).
* **Enterprise Architecture:** Strict adherence to Domain-Driven separation of concerns (Routers, CRUD, Schemas, Models, and Core configuration).

---

## 2. ## Quick Start & Core Concepts

### **System Architecture Syntax & Mapping**

| Component | Technology | Role / Responsibility |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | High-performance asynchronous HTTP routing and automatic OpenAPI doc generation. |
| **Validation** | Pydantic v2 | Runtime data validation, serialization, and settings management via environment variables. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database queries, relationship management, and schema migrations via Alembic. |
| **Database** | PostgreSQL 15 | Robust relational persistence layer with connection pooling. |
| **Auth Engine** | python-jose & passlib | Cryptographic JWT creation/verification and bcrypt password hashing. |
| **Containerization** | Docker & Docker Compose | Isolated, reproducible development and production environments. |

### **5-Minute Quick Start Guide**

#### 1. Clone & Configure Environment
```bash
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate
cp .env.example .env
```

#### 2. Configure `.env`
Ensure your environment variables are set correctly:
```ini
PROJECT_NAME="MicroCorp FastAPI Engine"
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=securepassword123
POSTGRES_DB=app_db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:securepassword123@db:5432/app_db

SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### 3. Spin Up via Docker Compose
```bash
docker compose up --build -d
```

#### 4. Verify API Health
Navigate to `http://localhost:8000/docs` to interact with the Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### **Directory Structure**
```text
app/
├── core/                 # Config, security, database session
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/               # SQLAlchemy ORM Models
│   └── user.py
├── schemas/              # Pydantic Data Contracts
│   └── user.py
├── crud/                 # Data Access Objects (DAO)
│   └── crud_user.py
├── api/                  # API Routers (Endpoints)
│   ├── v1/
│   │   ├── api.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       └── users.py
│   └── deps.py           # Dependency Injection (Auth, DB)
└── main.py               # FastAPI Application Entrypoint
```

---

### **1. Core Database Configuration (`app/core/database.py`)**
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
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
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
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

### **2. Security & JWT Handling (`app/core/security.py`)**
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

---

### **3. Dependency Injection (`app/api/deps.py`)**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = await db.get(User, int(token_data.sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

---

### **4. Authentication Router (`app/api/v1/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.core import security
from app.core.config import settings
from app.crud.crud_user import user_crud
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate
):
    user = await user_crud.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    user = await user_crud.create(db, obj_in=user_in)
    return user

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await user_crud.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = security.create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
```

---

### **5. Production Multi-Stage Dockerfile (`Dockerfile`)**
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

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **6. Docker Compose Configuration (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Patterns & Pitfalls | ❌ The Wrong Way | ✅ The Enterprise Way |
| :--- | :--- | :--- |
| **Sync DB Drivers in Async Framework** | Using standard `psycopg2` inside async FastAPI endpoints, blocking the event loop. | Use `asyncpg` combined with SQLAlchemy's `create_async_engine`. |
| **Hardcoding Config Secrets** | Storing database passwords and JWT secrets directly inside Python code. | Load configuration safely using Pydantic's `BaseSettings` from environment files. |
| **Running Containers as Root** | Executing your Uvicorn server as the `root` user inside Docker, exposing the host to breakout vulnerabilities. | Create a dedicated unprivileged user inside the Dockerfile (`USER appuser`). |
| **Swallowing Database Rollbacks** | Catching exceptions in API routes without rolling back the async session state, corrupting connection pools. | Handle session rollbacks cleanly inside context managers or dependency yields. |
| **Stateless Token Over-Reliance** | Storing sensitive PII inside the JWT payload (e.g., email, roles) which cannot be revoked easily. | Store *only* the user primary ID (`sub`) in the token; fetch state from the DB per request or utilize a Redis blacklist. |

---

## 5. ## Performance & Optimization Tips

1. **Uvicorn Worker Scaling via Gunicorn:**
   For multi-core production servers, run Uvicorn wrapped in Gunicorn using multiple worker processes to saturate CPU capacity:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **Connection Pooling Optimization:**
   Tune your database pool size (`pool_size` and `max_overflow`) based on your server's RAM and expected concurrency limits to prevent database connection exhaustion.

3. **Response Compression:**
   Incorporate FastAPI's `GZipMiddleware` to automatically compress JSON responses larger than 1000 bytes, significantly lowering network payload bandwidth:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

4. **Async Database Indexes:**
   Ensure foreign keys and frequently queried fields (such as `email` on the User model) are indexed (`index=True`) at the database schema level.

---

## 6. ## Commercial License & Attribution Summary

```text
================================================================================
COMMERCIAL LICENSE AGREEMENT - MICROCORP AI ENTERPRISE SUITE
================================================================================
Copyright (c) 2026 MicroCorp AI. All rights reserved.

1. GRANT OF LICENSE: MicroCorp AI grants the purchaser (Client) a perpetual, 
   worldwide, non-exclusive, non-transferable commercial license to use, modify, 
   and deploy this software boilerplate for internal business applications, 
   client deliverables, and SaaS products.
   
2. RESTRICTIONS: Purchaser may NOT resell, sub-license, or redistribute this 
   codebase as a standalone template, boilerplate generator, or open-source 
   repository. 

3. WARRANTY DISCLAIMER: This software is provided "as is", without warranty of 
   any kind, express or implied, including but not limited to the warranties of 
   merchantability, fitness for a particular purpose, and non-infringement.
================================================================================
```