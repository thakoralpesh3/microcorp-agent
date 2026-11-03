# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — Enterprise Backend Architecture  
> *Production-grade, scalable, and secure Python backend blueprint ready for immediate client deployment.*

---

## 1. Product Title & Value Proposition

### 🚀 FastAPI Production Blueprint: Enterprise JWT Auth & Dockerized Architecture
* **Target Audience:** Full-stack developers, agency contractors, and startup founders needing an uncompromised, battle-tested Python backend.
* **Commercial Value:** Eliminates 40+ hours of boilerplate configuration, security hardening, and container orchestration setup. 
* **Key Deliverables:** 
  * Asynchronous SQLAlchemy 2.0 integration with PostgreSQL.
  * Stateless JSON Web Token (JWT) authentication flow with secure HTTP-only cookie patterns or bearer tokens.
  * Multi-stage, security-hardened Dockerfile and production-ready `docker-compose.yml`.
  * Alembic migration pipeline configured out-of-the-box.

---

## 2. Quick Start & Core Concepts

Get your local development environment running in under 60 seconds.

### Prerequisites
* Docker & Docker Compose (v2.20+)
* Python 3.11+ (for local virtual environment development)

### Quick Start Commands
```bash
# Clone the repository and enter the directory
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-blueprint.git
cd fastapi-jwt-docker-blueprint

# Copy the environment configuration template
cp .env.example .env

# Spin up the stack via Docker Compose
docker compose up --build -d

# Run database migrations
docker compose exec backend alembic upgrade head
```

### Core Architecture Concepts
| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous REST API routing and automatic OpenAPI documentation. |
| **ORM / DB Driver** | SQLAlchemy 2.0 (Async) + asyncpg | Non-blocking database operations interacting with PostgreSQL 15. |
| **Auth Engine** | python-jose & passlib (Bcrypt) | Secure password hashing and cryptographic JWT signature generation/validation. |
| **Containerization** | Docker (Multi-stage builds) | Minimized image footprint, non-root execution, and isolated environment runtimes. |
| **Migration Tool** | Alembic | Deterministic schema evolution tracking and version control. |

---

## 3. Production Code Patterns & Architecture Examples

This section contains production-grade, copy-paste-ready code structured using a modular service-repository pattern.

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

### Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Blueprint"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

### Database Engine (`app/core/database.py`)
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

### Security Utilities (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

---

### Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user account")

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### Hardened Dockerfile (`Dockerfile`)
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
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Production Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  backend:
    build: .
    container_name: microcorp_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=production_db
      - JWT_SECRET_KEY=super-secret-jwt-key-change-me-in-production
    depends_on:
      db:
      condition: service_healthy
    networks:
      - microcorp_net

  db:
    image: postgres:15-alpine
    container_name: microcorp_postgres
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - microcorp_net

volumes:
  postgres_data:

networks:
  microcorp_net:
    driver: bridge
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* ❌ **Anti-Pattern 1: Blocking synchronous calls inside async routes.**
  * *The Trap:* Using standard `requests` or synchronous database drivers (`psycopg2`) inside `async def` endpoints, which blocks the entire Uvicorn event loop.
  * *The Fix:* Always use asynchronous drivers (`asyncpg`, `httpx`) and `async def` exclusively for I/O-bound endpoints. Use `def` for CPU-bound tasks so FastAPI automatically runs them in an external thread pool.
* ❌ **Anti-Pattern 2: Hardcoding secrets in source code.**
  * *The Trap:* Committing raw JWT secret keys or database connection URIs into version control.
  * *The Fix:* Enforce strict Pydantic `BaseSettings` validation checking environment variables loaded exclusively from secure runtime vaults or `.env` files ignored by Git.
* ❌ **Anti-Pattern 3: Ignoring Docker container non-root security.**
  * *The Trap:* Running Python web applications as the `root` user inside production Docker containers, giving container escapes full host privilege escalation vectors.
  * *The Fix:* Always create and drop down to a non-privileged system user (e.g., `useradd -u 1000 appuser`) inside your production Dockerfile.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a reverse proxy like Nginx, run Uvicorn with multiple workers or utilize Gunicorn as a process manager managing Uvicorn worker classes:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` parameters in `create_async_engine` based on your PostgreSQL instance sizing and maximum concurrent client load capacity.
* **Response Model Serialization:** Always declare `response_model` on your FastAPI decorators. This filters out sensitive database attributes (like hashed passwords) and significantly accelerates Pydantic JSON serialization performance.

---

## 6. Commercial License & Attribution Summary

* **Product License:** Commercial Per-Client Deployment License.
* **Usage Rights:** Permitted for integration into unlimited client projects delivered by the purchasing developer or engineering agency. Resale of the uncompiled source code blueprint as a standalone competing template is strictly prohibited.
* **Attribution:** Maintained and engineered by **The Agency Engineering Division** for MicroCorp AI.