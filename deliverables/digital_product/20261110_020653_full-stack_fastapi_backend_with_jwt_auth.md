# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — *Production-Ready Turnkey Architecture*

---

## 1. Product Title & Value Proposition

### 🚀 FastAPI Enterprise Engine: Production-Ready Asynchronous Backend
This turnkey architecture package provides a battle-tested, highly scalable, and secure backend template built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **PostgreSQL**, **Pydantic v2**, and **JWT Authentication**. Pre-configured with a complete **Docker Compose** development and production pipeline, this product eliminates weeks of boilerplate setup, security hardening, and structural refactoring.

### Why Buy / Use This Solution:
* **Time-to-Market:** Skip 40+ hours of initial configuration, dependency mapping, and security boilerplate.
* **Modern Stack:** Built on FastAPI (async by default), Pydantic v2 (blazing-fast data validation), and SQLAlchemy 2.0 async ORM.
* **Enterprise Security:** Implements stateless JSON Web Tokens (JWT) with secure password hashing via `passlib[bcrypt]` and strict role-based access control (RBAC).
* **Containerized Infrastructure:** Zero-friction local development and staging deployment using Docker and Docker Compose with health checks and volume persistence.

---

## 2. Quick Start & Core Concepts

### Architectural Syntax & Dependency Map

| Component | Technology | Core Purpose | Best Practice Rule |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI (0.110+) | Asynchronous REST API routing & validation | Always use `async def` for I/O-bound endpoint handlers. |
| **Data Validation** | Pydantic v2 | Request/Response payload parsing | Separate `Base`, `Create`, `Update`, and `Response` schemas. |
| **ORM / DB** | SQLAlchemy 2.0 + asyncpg | Type-safe asynchronous database access | Use session dependency injection per request (`yield`). |
| **Auth** | python-jose / passlib | Stateless token generation & verification | Keep secret keys out of code; inject via environment variables. |
| **Containerization**| Docker & Compose | Environment parity & orchestration | Use multi-stage builds to minimize image footprint. |

### 3-Step Local Initialization

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-template.git
   cd fastapi-jwt-docker-template
   cp .env.example .env
   ```

2. **Spin Up Infrastructure via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify API Health:**
   Navigate to `http://localhost:8000/docs` to interact with the auto-generated Swagger UI.

---

## 3. Production Code Patterns & Architecture Examples

### Directory Structure
```text
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   └── users.py
│   │   └── api.py
│   └── deps.py
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/
│   └── user.py
├── schemas/
│   └── user.py
└── main.py
Dockerfile
docker-compose.yml
requirements.txt
```

---

### `app/core/config.py` — Environment & Settings Management
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

---

### `app/core/database.py` — Async SQLAlchemy Engine & Session
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

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

### `app/core/security.py` — Password Hashing & JWT Encoding
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
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

---

### `app/api/deps.py` — Authentication & Session Dependencies
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenPayload(sub=username)
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == token_data.sub))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### `Dockerfile` — Multi-Stage Production Container
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `docker-compose.yml` — Local Orchestration
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
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
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking I/O in Async Routes (`async def`):**
   * *Anti-Pattern:* Performing synchronous database operations (like legacy SQLAlchemy queries) or blocking file reads inside an `async def` route. This starves the event loop.
   * *Correction:* Use `def` for synchronous CPU-bound/blocking functions (FastAPI runs them in an external threadpool) or use full async libraries (`asyncpg`, `SQLAlchemy 2.0` async sessions).

2. **Sharing DB Sessions Globally:**
   * *Anti-Pattern:* Instantiating a single global session object and importing it everywhere.
   * *Correction:* Always use FastAPI's dependency injection system (`Depends(get_db)`) to scope sessions strictly to the request lifecycle.

3. **Hardcoding Configuration Secrets:**
   * *Anti-Pattern:* Storing JWT keys, database passwords, and API credentials directly in source files.
   * *Correction:* Enforce strict Pydantic-based environment parsing (`BaseSettings`) mapped to `.env` files and environment variables.

4. **Ignoring Database Connection Pool Exhaustion:**
   * *Anti-Pattern:* Not properly closing or releasing async sessions, leading to unreleased connection leaks in PostgreSQL.
   * *Correction:* Always use context managers (`async with AsyncSessionLocal() as session:`) or explicit `try/finally` blocks in dependency providers.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a load balancer (like Nginx or AWS ALB), run multiple worker processes instead of relying on a single Uvicorn instance:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Connection Pooling tuning:** Tune SQLAlchemy engine pool parameters according to your database tier limits:
  ```python
  engine = create_async_engine(
      settings.DATABASE_URL,
      pool_size=20,
      max_overflow=10,
      pool_recycle=3600,
  )
  ```
* **Payload Compression:** Implement GZip middleware in `app/main.py` for large JSON payloads:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```

---

## 6. Commercial License & Attribution Summary

* **Product Identifier:** `MICROCORP-FAAST-JWT-DOC-V1`
* **License Type:** Commercial Developer / Enterprise Client License.
* **Permissions:** You are licensed to use, modify, adapt, and deploy this codebase for commercial client deliverables (e.g., Fiverr, Upwork, internal enterprise projects).
* **Restrictions:** Redistribution, resale, or publishing of this exact template as a competing standalone boilerplate product on marketplaces (Gumroad, GitHub Marketplace, etc.) is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI assumes no liability for database failures, security misconfigurations, or production outages resulting from improper deployment.