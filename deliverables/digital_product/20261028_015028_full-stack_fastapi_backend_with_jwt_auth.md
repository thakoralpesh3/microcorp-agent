# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Turnkey Boilerplate*

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, PostgreSQL, & Docker**

Stop burning 40+ hours writing repetitive boilerplate code for your clients. This production-ready, highly optimized FastAPI backend template comes pre-configured with industry-standard security, robust asynchronous database operations via SQLModel/SQLAlchemy, comprehensive JWT authentication, structured logging, and full containerization out of the box.

#### **Key Business & Technical Benefits:**
* **Time-to-Market Acceleration:** Deploy a secure, tested, and scalable API architecture in under 10 minutes.
* **Enterprise Security Standard:** Implements OAuth2 with Password (and hashing via `passlib[bcrypt]`), HTTP-only cookie or Bearer JWT token strategy, CORS middleware, and role-based access control (RBAC).
* **Asynchronous Performance:** Built entirely on `async/await` paradigms leveraging Uvicorn and async PostgreSQL drivers (`asyncpg`).
* **Zero-Configuration Infrastructure:** Fully dockerized with multi-stage builds, isolated volumes, and automated health checks.

---

## 2. ## Quick Start & Core Concepts

### **Directory Structure**
```text
fastapi-enterprise-starter/
├── app/
│   ├── api/              # API routers (v1 endpoints)
│   ├── core/             # Config, security, database sessions
│   ├── models/           # SQLModel database schemas
│   ├── schemas/          # Pydantic validation schemas
│   ├── services/         # Business logic layer
│   └── main.py           # Application entrypoint
├── alembic/              # Database migration version control
├── tests/                # Pytest asynchronous test suite
├── Dockerfile            # Multi-stage production container
├── docker-compose.yml    # Local development orchestration
├── requirements.txt      # Pinned dependency manifest
└── .env.example          # Environment variable template
```

### **Core Stack & Syntax Reference**

| Component | Technology | Purpose | Key Syntax Example |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI | High-performance API routing | `@app.get("/items/")` |
| **Data Validation** | Pydantic v2 | Request/Response payload parsing | `class UserCreate(BaseModel):` |
| **ORM / Migrations**| SQLModel / Alembic| Type-safe database mapping & migrations | `class User(SQLModel, table=True):` |
| **Authentication**| PyJWT / Passlib | Token encoding, decoding, & hashing | `jwt.encode(payload, SECRET_KEY)` |
| **Containerization**| Docker & Compose | Production environment parity | `docker compose up --build` |

---

## 3. ## Production Code Patterns & Architecture Examples

### **A. Environment & Configuration (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    def model_post_init(self, __context) -> None:
        object.__setattr__(
            self,
            "DATABASE_URL",
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}",
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

### **B. Asynchronous Database Session (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
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

### **C. JWT Authentication & Security Dependencies (`app/core/security.py`)**
```python
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from passlib.context import CryptContext
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    result = await db.exec(select(User).where(User.email == user_email))
    user = result.first()
    if user is None:
        raise credentials_exception
    return user
```

### **D. Enterprise Docker Setup (`Dockerfile`)**
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
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **E. Local Orchestration (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_db
      - SECRET_KEY=supersecretdevkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=fastapi_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d fastapi_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Endpoints**
   * *Anti-Pattern:* Using standard `requests` library or synchronous database operations inside `async def` routes, blocking the event loop.
   * *Correction:* Use `httpx` for async HTTP requests and `SQLModel` async drivers (`asyncpg`) for database queries. For CPU-bound operations, run them in a threadpool via `run_in_threadpool`.

2. **Hardcoding Secrets & Configuration**
   * *Anti-Pattern:* Placing database credentials and JWT secret keys directly inside Python files.
   * *Correction:* Use Pydantic's `BaseSettings` combined with environment variables loaded securely from an `.env` file or orchestrator secret manager.

3. **Skipping Connection Pool Management**
   * *Anti-Pattern:* Opening and closing new database engine instances per incoming HTTP request.
   * *Correction:* Instantiate a single global engine instance at startup and use dependency injection generators (`get_db`) to manage scoped session lifecycles.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container environments, run Uvicorn with multiple worker processes mapped to CPU cores via Gunicorn or Gunicorn managed workers: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`.
* **Response Caching:** Leverage Redis caching layers for read-heavy, low-mutation endpoints to offload queries from PostgreSQL.
* **Database Indexing:** Ensure foreign keys and high-cardinality lookup columns (`email`, `username`) include explicit database indexes within your SQLModel definitions (`index=True`).

---

## 6. ## Commercial License & Attribution Summary

* **License Type:** Commercial Developer License (Single-Org / Freelancer Delivery).
* **Permissions:** You are explicitly authorized to use this source code structure, boilerplate configurations, and patterns inside client deliverables, proprietary products, and commercial software projects built on Fiverr or independent contracts.
* **Restrictions:** Reselling or redistributing this exact codebase as an isolated standalone template on open-market digital storefronts without modification is strictly prohibited.
* **Attribution:** Maintained by MicroCorp AI Architecture Team. Built for elite execution.