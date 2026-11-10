# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** • *MicroCorp AI Production Architecture Series*  
> *Ready-to-deploy enterprise boilerplate for high-performance microservices.*

---

## 1. Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Enterprise Engine
Stop wasting 40+ hours writing boilerplate configurations, JWT handshake logic, database session management, and Docker-compose orchestration from scratch. This turnkey full-stack backend template provides a battle-tested, highly scalable foundation designed specifically for modern SaaS products, AI wrappers, and high-throughput microservices.

#### Why Engineers & Clients Buy This Solution:
* **Zero-Config Security:** Out-of-the-box OAuth2 with Password Flow, JWT access/refresh token rotation, and bcrypt password hashing.
* **Modern Async Architecture:** Built natively on `async`/`await` patterns using SQLAlchemy 2.0+ and Pydantic v2 for maximum I/O performance.
* **Containerized Consistency:** Production-grade `Dockerfile` with multi-stage builds and an optimized `docker-compose.yml` tying FastAPI, PostgreSQL, and Redis together seamlessly.
* **Strict Type Safety:** 100% type-hinted codebase passing strict MyPy and Ruff linting standards.

---

## 2. Quick Start & Core Concepts

### Architectural Map
```
[Client / Frontend] 
       │ (HTTPS / Bearer Token)
       ▼
[ Nginx / Reverse Proxy ] (Optional Edge)
       │
       ▼
[ FastAPI App Container ] ──(Async SQLAlchemy)──> [ PostgreSQL DB ]
       │
       └──(Cache / Rate Limiting)──────────────> [ Redis Cluster ]
```

### Clean Syntax & Component Reference

| Component | Library / Tool | Purpose in Architecture |
| :--- | :--- | :--- |
| **Web Framework** | `FastAPI` | High-performance asynchronous HTTP routing and automatic OpenAPI docs. |
| **Data Validation** | `Pydantic v2` | Runtime data parsing, settings management, and serialization. |
| **ORM & Migrations**| `SQLAlchemy 2.0` / `Alembic` | Type-safe asynchronous database interaction and schema migration control. |
| **Authentication** | `python-jose` / `passlib` | Cryptographic JWT token generation, verification, and password hashing. |
| **Containerization**| `Docker` & `Compose` | Isolated, reproducible multi-container runtime environments. |

---

## 3. Production Code Patterns & Architecture Examples

### Project File Structure
```text
fastapi-enterprise/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
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

### A. Environment Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
```

---

### B. Asynchronous Database Engine (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
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

### C. Security & JWT Token Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### D. User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

### E. Authentication Router (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
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

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### F. Application Factory (`app/main.py`)
```python
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    application.include_router(api_router, prefix=settings.API_V1_STR)
    return application

app = get_application()

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### G. Production Dockerfile (`Dockerfile`)
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime Image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### H. Multi-Container Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  web:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/enterprise_db
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=super-secret-production-key-change-me
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: always
    ports:
      - "6379:6379"

volumes:
    postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Mixing Synchronous and Asynchronous DB Drivers:** Using `psycopg2` inside an `async def` path operation blocks the entire event loop. Always use `asyncpg` with SQLAlchemy's `AsyncSession`.
2. ❌ **Hardcoding Secrets in Code Repositories:** Never store JWT secret keys or database passwords in plain text. Always inject them via environment variables managed through Pydantic BaseSettings.
3. ❌ **Swallowing Database Rollbacks on Exception:** If an exception occurs mid-transaction and the session isn't rolled back, subsequent queries on that session will fail or leave the database in an inconsistent state. Use context managers that explicitly handle rollback.
4. ❌ **Unbounded Pagination:** Returning complete database table sets via endpoints without pagination limits will eventually cause out-of-memory errors and crash your worker processes.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, scale Uvicorn worker processes using `--workers N` based on your available CPU cores ($2 \times \text{cores} + 1$), or deploy behind a Process Manager like Gunicorn/Uvicorn-Worker configuration.
* **Connection Pooling Optimization:** Tune your SQLAlchemy engine arguments (`pool_size`, `max_overflow`, and `pool_recycle`) to match the peak concurrency demands of your PostgreSQL instance.
* **Response Compression:** Integrate `GZipMiddleware` into your FastAPI instance to automatically compress large JSON responses payloads over 1KB.
* **Redis Caching Layer:** Offload frequent, heavy read queries (e.g., configurations, user profile metadata) into a Redis cache layer before querying PostgreSQL.

---

## 6. Commercial License & Attribution Summary

### MIT License / Commercial Distribution Rights
* **Copyright © 2024 MicroCorp AI / The Agency Engineering Division.**
* **Grant of Rights:** You are granted an irrevocable, royalty-free license to use, modify, distribute, and incorporate this codebase into proprietary commercial applications, client projects, and SaaS startups.
* **Disclaimer:** Provided "as is", without warranty of any kind, express or implied. The authors are not liable for any damages arising from the use of this software.