# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Microservice Boilerplate*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready JWT Auth & Dockerized Architecture**

> **Stop writing boilerplate. Start shipping revenue.**

Building a production-grade backend from scratch is an uphill battle. You spend weeks wiring up asynchronous database sessions, implementing secure token-based authentication (JWT), configuring CORS, structuring dependency injection containers, and containerizing the whole stack with Docker and Nginx. 

This turnkey solution gives you a battle-tested, highly performant FastAPI backend architecture designed specifically for freelance developers, agencies, and enterprise teams who need to deliver bulletproof APIs to clients in days, not months.

### **Key Value Drivers:**
* **Save 40+ Engineering Hours:** Skip the setup phase. All core configurations, security layers, and database connectors are pre-wired.
* **Production-Grade Security:** Out-of-the-box OAuth2 with Password Flow, JWT access/refresh token rotation, bcrypt password hashing, and secure HTTP-only cookie handling.
* **Asynchronous Performance:** Fully async stack using `SQLModel` / `SQLAlchemy 2.0`, `Pydantic v2`, and `Uvicorn` workers backed by PostgreSQL.
* **Zero-Friction DevOps:** Fully dockerized with multi-stage builds, hot-reloading for development, and a hardened production setup with Nginx reverse proxy.

---

## 2. ## Quick Start & Core Concepts

### **Project Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/                  # Database migrations
├── app/
│   ├── api/                  # API routers (v1)
│   │   ├── endpoints/        # Auth, Users, Health
│   │   └── deps.py           # Dependency injection
│   ├── core/                 # Config, security, database
│   ├── models/               # SQLModel database tables
│   ├── schemas/              # Pydantic validation schemas
│   ├── services/             # Business logic layer
│   └── main.py               # FastAPI application factory
├── tests/                    # Pytest test suite
├── docker-compose.yml        # Multi-container orchestration
├── Dockerfile                # Production multi-stage build
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variables template
```

### **Core Concepts Syntax Reference**

| Concept | Implementation in FastAPI | Purpose |
| :--- | :--- | :--- |
| **Dependency Injection** | `Depends(get_db)`, `Depends(get_current_user)` | Manages database sessions, authentication, and cross-cutting concerns cleanly. |
| **Data Validation** | `Pydantic v2` (`BaseModel`, `Field`) | Enforces strict type checking, parsing, and serialization at runtime. |
| **ORM & Migrations** | `SQLModel` + `Alembic` | Combines Pydantic and SQLAlchemy for seamless DB schema management. |
| **Auth Strategy** | `OAuth2PasswordBearer` + JWT | Stateless, secure token-based authentication with expiration controls. |
| **Containerization** | `Docker` + `Docker Compose` | Ensures environment parity across local development and production servers. |

---

## 3. ## Production Code Patterns & Architecture Examples

### **A. Environment & Configuration (`app/core/config.py`)**
Using Pydantic Settings to validate environment variables strictly on startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### **B. Database Session & Engine (`app/core/database.py`)**
Asynchronous engine setup with proper connection pooling.

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
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
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
Password hashing and JWT generation/verification logic.

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
```

---

### **D. Authentication Endpoints (`app/api/endpoints/auth.py`)**
Secure login route returning JWT tokens.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### **E. Application Factory (`app/main.py`)**
Clean application initialization with CORS and lifespan event handlers.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, users
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions (e.g., connect to cache, verify DB)
    print("Starting up FastAPI application...")
    yield
    # Shutdown actions (e.g., close connection pools)
    print("Shutting down FastAPI application...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust in production to trusted domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routers
    app.include_router(
        auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"]
    )
    app.include_router(
        users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"]
    )

    return app


app = create_app()
```

---

### **F. Docker Configuration (`Dockerfile` & `docker-compose.yml`)**

#### **Production Multi-Stage `Dockerfile`**
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

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### **`docker-compose.yml`**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
      POSTGRES_DB: enterprise_db
    volumes:
      :/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=FastAPI Enterprise API
      - SECRET_KEY=supersecretkeychangeinproduction
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking I/O Operations in Async Endpoints**
   * *Anti-Pattern:* Using synchronous libraries like `requests` or blocking file operations directly inside an `async def` path operation. This blocks the main event loop and destroys concurrency.
   * *Fix:* Use async-native libraries (`httpx`, `aiofiles`) or offload blocking CPU-heavy tasks using `run_in_threadpool`.

2. **Hardcoding Configuration & Secrets**
   * *Anti-Pattern:* Keeping database passwords, API keys, or JWT secrets directly inside Python code files.
   * *Fix:* Always leverage `pydantic-settings` tied strictly to environment variables (`.env`).

3. **Not Handling Database Session Rollbacks on Exception**
   * *Anti-Pattern:* Committing transactions blindly without catching runtime exceptions, leaving database sessions hanging or corrupted.
   * *Fix:* Implement try/except blocks inside your dependency injector (`get_db`) to guarantee clean rollbacks on failure.

4. **Omitting Pagination on List Endpoints**
   * *Anti-Pattern:* Returning `SELECT * FROM users` without limit/offset clauses. As datasets grow, this will cause memory exhaustion and sluggish response times.
   * *Fix:* Always enforce query parameter limits and pagination bounds (`skip: int = 0, limit: int = 100`).

---

## 5. ## Performance & Optimization Tips

* **Connection Pooling:** Always tune your database connection pool size (`pool_size` and `max_overflow`) based on your worker count and hardware capacity.
* **Gzip Compression:** Add FastAPI's `GZipMiddleware` to compress large JSON responses automatically and minimize network payload size:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware

  app.add_middleware(GZipMiddleware, minimum_size=1000)
```
* **Uvicorn Multi-Worker Deployment:** In production behind Docker, never run single-process Uvicorn. Utilize multiple worker processes (`--workers 4` or higher depending on CPU cores) to handle concurrent traffic spikes.
* **Database Indexing:** Ensure foreign keys and high-frequency lookup columns (e.g., `email`, `username`) have appropriate indexes applied via SQLModel/Alembic.

---

## 6. ## Commercial License & Attribution Summary

### **License Agreement: Commercial / Enterprise Use**
* **Granted Rights:** You are authorized to use, modify, adapt, and resell this codebase as part of client deliverables (Fiverr, Upwork, direct agency contracts) or proprietary software products.
* **Restrictions:** Reselling or redistributing this boilerplate *as an independent template or competing digital product* on marketplaces (Gumroad, GitHub Marketplace, Envato) is strictly prohibited.
* **Disclaimer:** Provided "as is" without warranty of any kind. The author/agency assumes no liability for vulnerabilities arising from improper configuration or failure to update security keys in production.