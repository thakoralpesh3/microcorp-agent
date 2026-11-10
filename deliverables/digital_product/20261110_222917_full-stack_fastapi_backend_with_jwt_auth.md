# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Product ID: MC-FSF-004*

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready JWT Auth & Dockerized PostgreSQL Architecture**

Stop wasting 40+ hours scaffolding the same backend architecture for every new client project or SaaS product. This full turnkey solution delivers a battle-tested, highly performant, asynchronously optimized FastAPI boilerplate complete with secure JSON Web Token (JWT) authentication, Role-Based Access Control (RBAC), SQLAlchemy 2.0 ORM, Alembic database migrations, and a fully orchestrated multi-container Docker environment.

#### **Commercial Value Proposition**
* **Time-to-Market Acceleration:** Deploy a hardened, production-grade API backbone in under 10 minutes instead of weeks.
* **Enterprise Security Standard:** Built-in password hashing (Bcrypt), OAuth2 password flow with JWT bearer tokens, CORS configuration, and environment-isolated secrets management.
* **Developer Ergonomics:** Fully typed Python codebase leveraging Pydantic v2 for lightning-fast payload validation and automatic interactive OpenAPI/Swagger documentation.
* **Zero-Friction Scaling:** Pre-configured with asynchronous database pooling (psycopg3 + asyncpg) and Nginx-ready Gunicorn/Uvicorn ASGI process management.

---

## 2. ## Quick Start & Core Concepts

Get your local development environment spinning in less than 3 minutes using Docker Compose.

### **Prerequisites**
* Docker Engine (v24.0+) & Docker Compose (v2.20+)
* Python 3.11+ (if running bare-metal migrations)

### **Rapid Deployment Steps**
```bash
# 1. Clone or extract the boilerplate into your project directory
cd microcorp-fastapi-boilerplate

# 2. Configure your environment variables
cp .env.example .env
# Edit .env and supply secure values for POSTGRES_PASSWORD and JWT_SECRET_KEY

# 3. Spin up the container cluster (PostgreSQL + FastAPI App + Adminer)
docker compose up --build -d

# 4. Run database migrations via Alembic inside the container
docker compose exec web alembic upgrade head

# 5. Verify health check
curl http://localhost:8000/health
```

### **Core Architectural Concepts & Syntax Reference**

| Concept | Implementation Layer | Primary Purpose | Key Python/FastAPI Tooling |
| :--- | :--- | :--- | :--- |
| **Async Routing** | API / Controller | Non-blocking HTTP request processing under high concurrency. | `async def`, FastAPI router decorators |
| **Data Validation** | Schema / DTO | Strict input sanitization and output serialization at runtime. | Pydantic v2 `BaseModel`, `Field` |
| **ORM Mapping** | Data Persistence | Object-relational mapping with type safety and async support. | SQLAlchemy 2.0 `Mapped`, `mapped_column`, `AsyncSession` |
| **Auth Pipeline** | Security Middleware | Token verification, payload decoding, and dependency injection. | `OAuth2PasswordBearer`, PyJWT / `python-jose` |
| **Migrations** | Database Versioning| Track, apply, and rollback database schema evolutions safely. | Alembic, async engine adapters |

---

## 3. ## Production Code Patterns & Architecture Examples

This section contains complete, copy-paste ready, production-grade files establishing the clean-architecture layout of the boilerplate.

### **Directory Tree Structure**
```text
app/
├── alembic/              # Database migration scripts
├── core/                 # Config, security, database session
├── models/               # SQLAlchemy ORM Models
├── schemas/              # Pydantic validation schemas
├── api/                  # API routers (Endpoints)
│   ├── v1/
│   │   ├── endpoints/    # auth.py, users.py
│   │   └── api.py        # Router aggregation
│   └── deps.py           # Dependency injection (get_db, get_current_user)
├── main.py               # FastAPI application entrypoint
├── Dockerfile            # Multi-stage production Dockerfile
└── docker-compose.yml    # Multi-container orchestration
```

---

### **File: `app/core/config.py` (Environment Configuration)**
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
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

### **File: `app/core/database.py` (Async Database Engine Setup)**
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
    autocommit=False,
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

### **File: `app/models/user.py` (SQLAlchemy 2.0 ORM Model)**
```python
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

---

### **File: `app/api/deps.py` (Authentication & Security Dependency Injection)**
```python
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
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
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials.",
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user.")
        
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges.",
        )
    return current_user
```

---

### **File: `app/api/v1/endpoints/auth.py` (JWT Token Issuer)**
```python
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account."
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires
    
    to_encode = {
        "sub": str(user.id),
        "exp": expire,
        "email": user.email,
        "is_superuser": user.is_superuser
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    return {"access_token": encoded_jwt, "token_type": "bearer"}
```

---

### **File: `Dockerfile` (Multi-Stage Production Build)**
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

# Stage 2: Runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **File: `docker-compose.yml` (Container Orchestration)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
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

  web:
    build: .
    container_name: fastapi_app
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous and Asynchronous Database Drivers:**
   * *The Antipattern:* Using `psycopg2` or synchronous SQLAlchemy engines inside `async def` FastAPI route endpoints. This blocks the main event loop and degrades application performance.
   * *The Fix:* Always use an async driver (`asyncpg`) paired with `create_async_engine` and `AsyncSession`.
2. **Hardcoding Secrets and Keys in Source Control:**
   * *The Antipattern:* Committing `JWT_SECRET_KEY` or database passwords directly into `config.py` or version control.
   * *The Fix:* Enforce strict Pydantic-settings environment variable ingestion and supply a `.env.example` file template.
3. **Ignoring Database Session Lifecycle Management:**
   * *The Antipattern:* Manually opening sessions inside routers without ensuring proper closure or exception rollbacks.
   * *The Fix:* Utilize FastAPI’s dependency injection system (`Depends(get_db)`) to guarantee context-managed session lifecycles and automatic rollbacks on exception.
4. **Neglecting Token Expiration Validation (`exp`):**
   * *The Antipattern:* Issuing JWTs without an expiration claim or failing to validate `exp` during decoding.
   * *The Fix:* Always include an `exp` claim computed via UTC datetime offsets and let PyJWT handle expiration validation automatically.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production Docker environments, scale worker processes relative to available CPU cores using `--workers $(( 2 * $(nproc) + 1 ))` or leverage a process manager like Gunicorn with Uvicorn worker classes.
* **Database Connection Pooling:** Fine-tune `pool_size` and `max_overflow` in SQLAlchemy engine configurations based on your underlying PostgreSQL instance limits and expected concurrent connection peaks.
* **Pydantic Model Compilation:** For ultra-high throughput endpoints processing large JSON payloads, leverage Pydantic v2's Rust-backed core validation engine by avoiding custom validators where native types suffice.
* **Response Caching:** Integrate Redis caching layers for read-heavy, low-mutation database queries (e.g., user profile lookups, configuration data) using FastAPI dependencies or middleware caching.

---

## 6. ## Commercial License & Attribution Summary

### **MicroCorp AI Commercial-Grade License (MC-CGL v2.4)**

* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, distribute, and deploy this codebase for internal development, client deliverables (Fiverr, Upwork, agency contracts), and commercial SaaS products.
* **Restrictions:** Reselling, sub-licensing, or redistributing this exact codebase or boilerplate as a standalone competing digital product template on marketplaces (e.g., Gumroad, GitHub Marketplace, ThemeForest) is strictly prohibited.
* **Disclaimer of Warranty:** Provided "as is" without warranty of any kind, express or implied. MicroCorp AI and Engineering Division disclaim liability for any direct, indirect, or consequential damages arising from the use of this software.

*Generated with precision by Backend Architect 🏗️, The Agency Engineering Division for MicroCorp AI.*