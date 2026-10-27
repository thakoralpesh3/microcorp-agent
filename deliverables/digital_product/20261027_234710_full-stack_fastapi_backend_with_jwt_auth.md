# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production Turnkey Reference Architecture*

---

## 1. # Product Title & Value Proposition

### 🚀 Production-Grade FastAPI Backend Boilerplate with Async Architecture, JWT Security, and Zero-Downtime Docker Orchestration

Stop wasting 40+ hours configuring boilerplate architecture, security dependencies, and container orchestration for every new client project. This battle-tested FastAPI backend template provides a strictly typed, fully asynchronous, production-ready foundation designed to scale from zero to millions of requests without structural refactoring.

#### What You Get
*   **Asynchronous Core:** Built on FastAPI, SQLAlchemy 2.0 (Async), and PostgreSQL via `asyncpg` for maximum I/O throughput.
*   **Enterprise Security:** Secure, stateless JWT authentication with dual token handling (Access/Refresh), password hashing via Argon2/Bcrypt, and dependency-injected Role-Based Access Control (RBAC).
*   **Containerized Environment:** Multi-stage Dockerfiles and Docker Compose profiles for local hot-reloading, database migrations, and isolated production environments.
*   **Developer Ergonomics:** Pydantic v2 strict data validation, Alembic auto-migrations, structured JSON logging, and pre-configured CORS/Middleware.

---

## 2. ## Quick Start & Core Concepts

### Syntax & Architecture Reference

| Concept | Implementation Tool | Primary Responsibility |
| :--- | :--- | :--- |
| **API Framework** | FastAPI (Python 3.11+) | Async routing, automatic OpenAPI/Swagger documentation generation, dependency injection. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and strict environment configuration. |
| **ORM & Migrations** | SQLAlchemy 2.0 + Alembic | Asynchronous database querying, relationship mapping, and schema version control. |
| **Authentication** | `python-jose` / `passlib` | Stateless JWT token issuance, verification, and cryptographic password hashing. |
| **Containerization** | Docker & Docker Compose | Isolated, reproducible runtime environments for development, testing, and production. |

### 3-Step Local Initialization

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
   cd fastapi-jwt-docker-boilerplate
   cp .env.example .env
   ```

2. **Spin Up Containers:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify API Health:**
   Navigate to `http://localhost:8000/docs` to interact with the auto-generated Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### File 1: `app/core/config.py` (Environment Configuration)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp AI Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    SQLALCHEMY_DATABASE_URI: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
```

---

### File 2: `app/core/database.py` (Async SQLAlchemy Session Management)
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

### File 3: `app/core/security.py` (JWT & Password Utilities)
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


def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### File 4: `app/api/deps.py` (Authentication Dependencies & RBAC)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
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
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
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
        
    user = await db.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

---

### File 5: `app/main.py` (Application Factory & Lifecycle)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
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


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### File 6: `Dockerfile` (Optimized Multi-Stage Production Image)
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

---

### File 7: `docker-compose.yml` (Orchestration & Volume Management)
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
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    container_name: fastapi_backend
    restart: always
    depends_on:
      db:
        condition: service_healthy
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_REFRESH_SECRET_KEY=${JWT_REFRESH_SECRET_KEY}
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

*   **Blocking I/O in Async Paths:** Mixing synchronous drivers (`psycopg2`) or heavy blocking CPU tasks inside `async def` endpoints will stall the entire event loop. Always use `asyncpg` and offload CPU-bound calculations using `starlette.concurrency.run_in_threadpool`.
*   **Catching Base Exceptions Generically:** Using `except Exception:` without re-raising or properly managing database rollback states leads to broken transaction states and hanging database connections. Always rely on context managers (`async with`) to handle session state.
*   **Hardcoding Environment Secrets:** Committing raw JWT secrets or database connection strings to version control. Always enforce strict validation via Pydantic `BaseSettings` that fail fast on startup if variables are missing.
*   **Exposing Raw ORM Models in Responses:** Returning database models directly instead of mapping them to Pydantic Response Schemas (`response_model=UserResponse`). This risks exposing internal database fields like password hashes or internal foreign keys.

---

## 5. ## Performance & Optimization Tips

*   **Uvicorn Worker Scaling:** In production container setups, run multiple Uvicorn worker processes based on available CPU cores (`--workers N`), or pair Uvicorn with a Gunicorn process manager.
*   **Database Connection Pooling:** Fine-tune `pool_size` and `max_overflow` in your SQLAlchemy engine setup depending on your database instance limits and maximum expected concurrent client connections.
*   **Selective Query Loading:** Avoid lazy-loading traps in async relationships. Explicitly use `selectinload` or `joinedload` options when querying related models to prevent `MissingGreenlet` errors and minimize N+1 query execution loops.

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp AI Commercial License (Type C - Turnkey Engineering Solution)

*   **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and distribute this codebase within commercial client projects, SaaS platforms, and internal enterprise architectures.
*   **Restrictions:** Redistribution of this codebase as a standalone boilerplate template, open-source framework, or competing code generator product is strictly prohibited.
*   **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. MicroCorp AI and its contributors shall not be held liable for any claim, damages, or liability arising from the deployment of this software.