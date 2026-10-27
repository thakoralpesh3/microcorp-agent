# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Delivery Document*

## 1. Product Title & Value Proposition

### Product Title
**Production-Grade FastAPI Enterprise Boilerplate: Async Architecture, JWT Security, & Dockerized CI/CD**

### Value Proposition
Stop wasting 40+ hours bootstrapping boilerplate infrastructure for your clients. This turnkey FastAPI backend template provides a battle-tested, highly performant, and secure foundation designed specifically for production-grade web applications and mobile backends. 

Equipped with asynchronous SQLAlchemy 2.0, Pydantic v2 validation, secure JWT authentication with refresh token rotation, and a fully optimized multi-stage Docker deployment pipeline, this kit allows you to deliver robust APIs to clients on Day One while maintaining enterprise-level security standards.

---

## 2. Quick Start & Core Concepts

### System Requirements
* Python 3.11+
* Docker & Docker Compose v2+
* PostgreSQL 15+

### Rapid Initialization (Under 3 Minutes)

```bash
# 1. Clone or unpack the boilerplate
git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
cd fastapi-enterprise-boilerplate

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your secure SECRET_KEY and database credentials

# 3. Spin up infrastructure via Docker Compose
docker compose up --build -d

# 4. Run database migrations via Alembic
docker compose exec api alembic upgrade head
```

### Core Architecture Concepts & Syntax Reference

| Concept | Implementation in this Boilerplate | Why We Use It |
| :--- | :--- | :--- |
| **Async I/O** | `async def` endpoints with `asyncpg` | Maximizes throughput and concurrent request handling under heavy I/O load. |
| **ORM & Migrations** | SQLAlchemy 2.0 (Mapped) + Alembic | Type-safe database interactions with explicit schema evolution tracking. |
| **Validation** | Pydantic v2 (`BaseModel`, `Field`) | Blisteringly fast, Rust-backed data validation and serialization. |
| **Authentication** | OAuth2 with Password Bearer + JWT | Stateless, cryptographically secure token-based user verification. |
| **Containerization** | Multi-stage Docker + Alpine base | Minimizes attack surface and reduces final production image size. |

---

## 3. Production Code Patterns & Architecture Examples

### A. Project Directory Structure
```text
fastapi_backend/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/                  # API routers (v1)
│   │   ├── endpoints/        # Auth, Users, Health
│   │   └── deps.py           # Dependency injection (Current user, DB session)
│   ├── core/                 # Config, Security, Database connection
│   │   ├── config.py         # Pydantic Settings management
│   │   ├── database.py       # Async engine & sessionmaker
│   │   └── security.py       # JWT creation, verification, password hashing
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic data schemas (Input/Output)
│   └── main.py               # FastAPI application entrypoint
├── Dockerfile                # Multi-stage production container build
├── docker-compose.yml        # Local development orchestrator
├── requirements.txt          # Pinned Python dependencies
└── .env.example              # Environment variables template
```

---

### B. Core Database Configuration (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncSession:
    """Dependency for injecting async database sessions into endpoints."""
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

### C. Security & JWT Handling (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

---

### D. Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ALGORITHM
from app.models.user import User
from app.schemas.auth import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.type != "access":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token type for access.",
            )
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials.",
        )
    
    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user.")
        
    return user
```

---

### E. Production FastAPI Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
```

---

### F. Multi-Stage Production Dockerfile (`Dockerfile`)
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

## 4. Common Anti-Patterns & Gotchas to Avoid

* **Mixing Sync and Async Code Blocks (`def` vs `async def`)**: Never execute blocking I/O operations (like standard `requests` calls or synchronous file operations) inside an `async def` route handler without wrapping them via `run_in_threadpool`. Doing so starves the asyncio event loop and kills performance.
* **Hardcoding Secrets & Configurations**: Never store database credentials, JWT secret keys, or third-party API tokens inside code or Git repositories. Always utilize Pydantic's `BaseSettings` combined with environment variables.
* **Implicit Database Session Commits**: Avoid calling `session.commit()` haphazardly inside your CRUD functions. Let your dependency injection lifecycle manager handle commits cleanly at the edge of the request cycle to maintain clean unit-of-work transactions.
* **Not Setting Pool Pre-Ping in Production**: When connecting to cloud-managed PostgreSQL instances (AWS RDS, Supabase), always enable `pool_pre_ping=True` in your SQLAlchemy engine to automatically handle stale, dropped TCP connections.

---

## 5. Performance & Optimization Tips

1. **Uvicorn Worker Scaling**: Run your production container using multiple workers aligned with your CPU core count (`--workers 4`), or front Uvicorn with an ASGI server supervisor like Gunicorn.
2. **Database Indexing Strategy**: Ensure foreign keys and high-frequency query filters (e.g., `email` on the User table) feature explicit database indexes (`index=True`).
3. **Pydantic Model Compilation**: For extreme serialization speeds under heavy load, ensure Pydantic v2 models utilize compiled Rust validation hooks by avoiding complex, unoptimized custom validators where standard types suffice.
4. **Response Streaming**: For large dataset queries, utilize FastAPI's `StreamingResponse` combined with asynchronous database cursor fetching to prevent memory exhaustion spikes.

---

## 6. Commercial License & Attribution Summary

* **License Type**: MicroCorp AI Commercial Engineering License (Single Client / Enterprise Deployment)
* **Usage Rights**: You are free to deploy, modify, rebrand, and ship this source code as part of client deliverables on Fiverr, Upwork, or direct enterprise contracts.
* **Restrictions**: Reselling this specific boilerplate codebase as an uncompiled standalone software template on marketplaces (Gumroad, ThemeForest) is strictly prohibited.
* **Warranty**: Provided "as-is", without warranty of any kind, express or implied. MicroCorp AI Engineering Division maintains zero liability for production downtime resulting from improper server configuration or credential leakage.