# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Guide*

---

## 1. Product Title & Value Proposition

### **Enterprise FastAPI Boilerplate: Production-Ready Asynchronous Backend with JWT Authentication, PostgreSQL, SQLAlchemy 2.0, Alembic, and Docker Multi-Stage Builds.**

#### **Value Proposition**
Building a modern production-ready backend requires stitching together dozens of disparate tools: validation via Pydantic, ORM modeling, database migrations, security hashing, JWT token rotation, CORS policies, and containerization. 

This turnkey solution eliminates weeks of boilerplate setup. It delivers an opinionated, highly scalable, and fully asynchronous architecture designed specifically for high-throughput microservices and enterprise client deliverables. Every component—from the dependency-injection security layer to the Docker multi-stage build—is optimized for zero-downtime deployments and strict type safety.

#### **What’s Included**
* **Asynchronous Core:** Built on FastAPI and `asyncpg` for high-performance non-blocking I/O.
* **Modern ORM Layer:** SQLAlchemy 2.0 with native async support and type-hinted models.
* **Database Migrations:** Pre-configured Alembic environment with auto-generation support.
* **Secure Authentication:** OAuth2 with Password Flow, Bearer tokens, and secure JWT generation/verification via `python-jose` and `passlib`.
* **Containerization:** Production-grade `Dockerfile` using multi-stage builds for minimal image size, paired with `docker-compose` for local development.
* **Environment Validation:** Strict startup configuration validation using Pydantic `BaseSettings`.

---

## 2. Quick Start & Core Concepts

### **Architecture Topology**
```
[ Client / Frontend ] 
         │ (HTTPS / Bearer Token)
         ▼
[ Nginx / Reverse Proxy ] (Optional)
         │
         ▼
[ FastAPI Application Container (Uvicorn Workers) ]
   ├── /api/v1/auth (JWT Issuance & Refresh)
   ├── /api/v1/users (User Management & RBAC)
   └── Dependency Injection (get_db, get_current_user)
         │
         ├──► [ PostgreSQL Container (asyncpg) ]
         └──► [ Redis Container (Caching / Celery - Optional) ]
```

### **Core Components Syntax Reference**

| Component | Technology | Purpose | Key Benefit |
| :--- | :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | Request handling & routing | Automatic OpenAPI docs, sub-dependency injection |
| **Data Validation** | Pydantic v2 | Payload validation & serialization | Rust-powered performance, strict type enforcement |
| **Database ORM** | SQLAlchemy 2.0 | Relational database mapping | Full async support (`AsyncSession`), declarative mapping |
| **Migrations** | Alembic | Schema version control | Reproducible DB state transitions across environments |
| **Authentication** | JWT (JSON Web Tokens) | Stateless authorization | Cryptographically signed user claims, zero session overhead |
| **Containerization** | Docker & Compose | Environment parity | Isolated runtime, repeatable deployments |

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```
fastapi-enterprise-boilerplate/
├── alembic/                  # Database migration scripts
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/    # Route handlers (auth, users)
│   │   │   └── router.api    # API router aggregator
│   │   └── deps.py           # Shared FastAPI dependencies (DB, Auth)
│   ├── core/
│   │   ├── config.py         # Pydantic BaseSettings configuration
│   │   ├── database.py       # Async engine & sessionmaker setup
│   │   └── security.py       # Password hashing & JWT token utils
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic Request/Response DTOs
│   └── main.py               # Application entrypoint
├── .env.example              # Environment variable template
├── Dockerfile                # Multi-stage production container
├── docker-compose.yml        # Local development stack
├── requirements.txt          # Python dependencies
└── alembic.ini               # Alembic configuration
```

---

### **1. Configuration Management (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Service"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Security / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

---

### **2. Database Connection & Session (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    pass


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

### **3. Security & JWT Utilities (`app/core/security.py`)**
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


def create_access_token(
    subject: str | int, expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt
```

---

### **4. SQLAlchemy User Model (`app/models/user.py`)**
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

---

### **5. FastAPI Authentication Dependencies (`app/api/deps.py`)**
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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception

    user = await db.get(User, token_data.sub)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
        )
    return user
```

---

### **6. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### **7. Production Dockerfile (Multi-Stage Build)**
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

### **8. Docker Compose Stack (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretjwtkeychangeinproduction123!
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous Operations in Async Routes:**
   * **Anti-Pattern:** Using standard `requests` library or synchronous database queries (`psycopg2`) inside `async def` route handlers. This blocks the main event loop, destroying throughput.
   * **Fix:** Use fully asynchronous libraries (`httpx`, `asyncpg`, SQLAlchemy `AsyncSession`). For unavoidable blocking CPU tasks, offload them via `run_in_threadpool`.

2. **Database Session Leaks:**
   * **Anti-Pattern:** Manually opening sessions without proper `try/finally` context management, leading to unclosed connection pool exhaustion.
   * **Fix:** Always utilize FastAPI dependency injection with `yield` combined with context managers (`async with AsyncSessionLocal() as session:`).

3. **Hardcoding Secrets & Configuration:**
   * **Anti-Pattern:** Embedding JWT secrets, database credentials, or API keys directly in source code files.
   * **Fix:** Use Pydantic `BaseSettings` reading explicitly from validated `.env` files or orchestration secrets stores.

4. **Catching Generic Exceptions Silently:**
   * **Anti-Pattern:** `except Exception: pass` inside database transaction blocks, masking critical failures and failing to roll back active transactions.
   * **Fix:** Always explicitly rollback sessions on failure before propagating the exception or raising an appropriate HTTP HTTPException.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production, run Uvicorn behind a process manager or orchestrator (such as Kubernetes) with workers set to `(2 * CPU_cores) + 1`, or deploy behind an Nginx reverse proxy.
* **Connection Pooling:** Tune SQLAlchemy `pool_size` and `max_overflow` parameters to match your maximum expected concurrent database load without saturating PostgreSQL's `max_connections` limit.
* **Response Serialization Tuning:** For endpoints returning thousands of complex records, use Pydantic's `.model_dump()` optimizations or bypass ORM overhead entirely using SQLAlchemy Core execution statements when rendering read-only analytical tables.
* **ASGI Middleware Optimization:** Keep custom middleware lightweight. Avoid performing synchronous disk or network I/O inside custom ASGI middleware layers.

---

## 6. Commercial License & Attribution Summary

### **Commercial Use Grant**
* **Licensed To:** The purchasing client / Fiverr customer.
* **Permissions:** This template is licensed for commercial deployment, modification, and integration into proprietary client software solutions.
* **Restrictions:** Reselling, sub-licensing, or redistributing this raw boilerplate code package as a standalone developer template on marketplaces (e.g., GitHub Marketplace, Gumroad, ThemeForest) is strictly prohibited.

### **Attribution & Engineering Support**
* **Engineered By:** Backend Architect 🏗️ — The Agency (Engineering Division).
* **Warranty:** Provided *as-is* without warranty of any kind. MicroCorp AI and The Agency disclaim all liability for direct or indirect damages resulting from misconfigured production deployments.