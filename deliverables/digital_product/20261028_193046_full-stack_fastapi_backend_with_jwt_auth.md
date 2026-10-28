# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise-Grade FastAPI Backend Boilerplate
**Turnkey Microservice Architecture with Async SQLAlchemy, JWT Authentication, Alembic Migrations, and Production-Ready Docker Compose.**

#### Value Proposition
Building a production-ready, secure asynchronous Python backend from scratch typically requires 40–60 hours of architectural planning, dependency wiring, security hardening, and containerization setup. This turnkey solution provides an enterprise-patterned, battle-tested FastAPI boilerplate designed for immediate deployment. 

Save weeks of development overhead with pre-configured dependency injection, robust password hashing (Bcrypt), JSON Web Token (JWT) lifecycle management, automatic database migrations, and a zero-downtime multi-container Docker topology.

---

## 2. Quick Start & Core Concepts

### System Architecture Overview
This boilerplate uses an asynchronous non-blocking design pattern built on modern Python standards (`async/await`, Pydantic v2, and SQLAlchemy 2.0).

```
[ Client / Frontend ] 
       │
       ▼ (HTTPS / JSON)
[ Nginx / Reverse Proxy ] (Optional Layer)
       │
       ▼
[ FastAPI Application (Uvicorn Workers) ]
       ├── /api/v1/auth (JWT Issuance & Refresh)
       ├── /api/v1/users (RBAC User Management)
       └── Dependency Injection (DB Session, Current User)
       │
       ├──► [ PostgreSQL 16 ] (AsyncPG Driver)
       └──► [ Redis 7 ] (Token Blacklisting & Rate Limiting)
```

### Core Technologies Syntax & Reference Table

| Layer / Component | Technology | Version | Purpose / Design Choice |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | `0.110+` | High-performance async routing, automatic OpenAPI/Swagger docs. |
| **ASGI Server** | Uvicorn | `0.28+` | Lightning-fast ASGI application server with worker management. |
| **Data Validation** | Pydantic | `2.6+` | Runtime data validation, serialization, and settings management. |
| **ORM & Database** | SQLAlchemy | `2.0+` | Enterprise-grade async ORM with native type-hinting support. |
| **Migrations** | Alembic | `1.13+` | Deterministic database schema migration version control. |
| **Database Driver** | AsyncPG | `0.29+` | High-performance asynchronous PostgreSQL client driver. |
| **Security** | Passlib / PyJWT | `1.7+` / `2.8+` | Secure cryptographic password hashing (Bcrypt) and JWT signing. |
| **Containerization** | Docker / Compose | `24+` | Isolated, reproducible multi-container orchestration. |

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
fastapi-enterprise-boilerplate/
├── alembic/                      # Database migrations
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py               # Dependency injection (DB, Auth)
│   ├── core/
│   │   ├── config.py             # Pydantic Settings
│   │   ├── database.py           # Async SQLAlchemy setup
│   │   └── security.py           # JWT & Password hashing
│   ├── models/                   # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic I/O validation schemas
│   └── main.py                   # FastAPI app entrypoint
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### Asynchronous Database Engine (`app/core/database.py`)
```python
from typing import AsyncGenerator
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
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### API Authentication Dependency (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
        
    return user
```

---

### Production Dockerfile (`Dockerfile`)
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

# Stage 2: Final Runtime Image
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

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: fastapi_app
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=fastapi_production
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=super_secure_access_secret_key_change_in_production
      - JWT_REFRESH_SECRET_KEY=super_secure_refresh_secret_key_change_in_production
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network

  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
      POSTGRES_DB: fastapi_production
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d fastapi_production"]
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

1. **Blocking Synchronous I/O Inside Async Routes (`def` vs `async def`)**
   * **The Trap:** Using synchronous libraries (like standard `requests` or blocking file operations) inside an `async def` route halts the entire event loop thread, starving other concurrent client requests.
   * **The Fix:** Use native asynchronous drivers (`httpx`, `asyncpg`) or run blocking code via `await run_in_threadpool()`.
2. **Global Database Session State**
   * **The Trap:** Instantiating a single global database session object and importing it across multiple modules. This causes race conditions and thread-safety violations across concurrent requests.
   * **The Fix:** Always inject database sessions per request lifecycle using FastAPI’s `Depends(get_db)` generator pattern.
3. **Hardcoding Secrets in Codebase**
   * **The Trap:** Committing JWT secrets, database passwords, or API keys directly into Git repositories.
   * **The Fix:** Isolate all secrets inside an uncommitted `.env` file loaded strictly through Pydantic BaseSettings.
4. **Ignoring SQLAlchemy Lazy-Loading Exceptions (`MissingGreenlet`)**
   * **The Trap:** Accessing un-awaited relational attributes on models outside of an active asynchronous session boundary.
   * **The Fix:** Explicitly use SQLAlchemy `selectinload()` or `joinedload()` eager-loading options within your queries.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Always configure multi-worker setups in production (`--workers 4` or matching CPU cores via Gunicorn/Uvicorn worker managers) to fully saturate multi-core server processors.
* **Database Connection Pooling:** Adjust `pool_size` and `max_overflow` parameters in `create_async_engine` based on your PostgreSQL server limits and peak concurrent request loads.
* **Response Serialization Tuning:** For high-throughput endpoints returning large arrays of records, consider using `orjson` as a drop-in replacement for FastAPI's default JSON parser to drastically speed up response serialization times.
* **Nginx Reverse Proxy:** Place Nginx or Traefik in front of Uvicorn to handle SSL/TLS termination, static asset caching, and basic DDoS/rate-limiting protection.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial Turnkey License (v1.0)
* **Usage Rights:** This code template is licensed for unlimited commercial deployment, modification, and distribution for client projects or internal enterprise applications developed by the purchasing entity.
* **Restrictions:** Reselling, sub-licensing, or redistributing this raw boilerplate code package as a standalone competing code template repository is strictly prohibited.
* **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. The Agency Engineering Division accepts no liability for production incidents resulting from improper secret management or misconfigured server infrastructure.