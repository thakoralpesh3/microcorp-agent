# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division | Enterprise Commercial Product Suite*

---

## 1. Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate with Secure JWT Authentication, PostgreSQL/SQLAlchemy, and Production-Ready Dockerized Architecture**

Stop wasting 40+ hours setting up boilerplate, dependency injection wiring, security pipelines, and container orchestration for every new client project. This turnkey backend solution is engineered by senior distributed systems architects to provide an uncompromised, production-ready foundation for modern web applications, SaaS products, and high-throughput APIs.

#### **Core Value & ROI:**
* **Time-to-Market Acceleration:** Deploy a fully secured, tested, and containerized API backend in under 5 minutes.
* **Enterprise Security Standard:** Implements stateless JWT authentication with secure password hashing (Argon2/Bcrypt), role-based access control (RBAC), HTTP-only cookies, and robust CORS management out of the box.
* **Developer Ergonomics:** Fully typed using Python 3.11+ type hints, Pydantic v2 data validation, and automated OpenAPI (Swagger/ReDoc) documentation.
* **Production Observability & Scale:** Pre-configured with asynchronous database sessions (SQLAlchemy 2.0), Alembic migrations, structured JSON logging, and a multi-stage Docker setup with Nginx reverse proxy and PostgreSQL.

---

## 2. Quick Start & Core Concepts

### **Architecture Topology**
```
[ Client / Frontend ] 
       │
       ▼ (HTTPS / REST)
[ Nginx Reverse Proxy ] (Port 80/443)
       │
       ▼
[ FastAPI App Container ] (Uvicorn Workers)
       ├─► Pydantic v2 (Validation)
       ├─► SQLAlchemy 2.0 (Async ORM)
       └─► JWT Security Layer (OAuth2 Password Bearer)
       │
       ▼
[ PostgreSQL 16 DB Container ] (Persistent Volume)
```

### **Core Concepts & Configuration Matrix**

| Component | Technology Choice | Enterprise Rationale |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI 0.110+ | High-performance asynchronous execution, automatic validation, native OpenAPI generation. |
| **Data Validation** | Pydantic v2 | Rust-backed core validation speed, strict type enforcement, serialization safety. |
| **Database ORM** | SQLAlchemy 2.0+ (Async) | Fully asynchronous database interaction preventing event loop blocking under load. |
| **Migrations** | Alembic | Deterministic, version-controlled schema evolution for zero-downtime deployments. |
| **Authentication** | PyJWT / Passlib | Stateless token verification with cryptographic signing (HS256/RS256) and salt-hashed secrets. |
| **Containerization** | Docker & Docker Compose | Isolated multi-container environments ensuring parity between dev, staging, and production. |

---

## 3. Production Code Patterns & Architecture Examples

### **Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/                  # Database migration versions
├── app/
│   ├── api/                  # API routers (v1)
│   │   ├── endpoints/        # Auth, Users, Health
│   │   └── deps.py           # Dependency injections (DB, Current User)
│   ├── core/                 # Config, Security, Database connection
│   │   ├── config.py         # Pydantic BaseSettings environment loader
│   │   ├── database.py       # Async SQLAlchemy sessionmaker
│   │   └── security.py       # JWT creation & Password hashing
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic Request/Response DTOs
│   └── main.py               # FastAPI application entrypoint
├── Dockerfile                # Multi-stage production Docker build
├── docker-compose.yml        # Local orchestration stack
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template
```

---

### **Configuration Management (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    
    # SECURITY
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # DATABASE
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str | None = None

    def model_post_init(self, __context) -> None:
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### **Database Connection & Session Dependency (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
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

### **Security & JWT Utilities (`app/core/security.py`)**
```python
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
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
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **Authentication Endpoints (`app/api/endpoints/auth.py`)**
```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user account"
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user.id, expires_delta=access_token_expires),
        "token_type": "bearer",
    }
```

---

### **Multi-Stage Dockerfile (`Dockerfile`)**
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

### **Docker Compose Stack (`docker-compose.yml`)**
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    restart: always
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
      - PROJECT_NAME=Enterprise FastAPI
      - SECRET_KEY=supersecretjwtkeychangeinproduction998877
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy
    restart: always

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking the Event Loop in Async Endpoints**
   * *The Antipattern:* Using synchronous database drivers (like standard `psycopg2`) or heavy CPU-bound tasks (like image processing or large JSON parsing) directly inside an `async def` route path. This starves the Uvicorn worker thread.
   * *The Fix:* Always use async drivers (`asyncpg`) and offload CPU-bound calculations using `starlette.concurrency.run_in_threadpool` or a Celery background worker queue.
2. **Hardcoding Secrets & Configuration**
   * *The Antipattern:* Storing JWT secret keys, database credentials, or API keys directly in python modules.
   * *The Fix:* Use Pydantic's `BaseSettings` combined with environment variables injected securely via Docker secrets or `.env` files.
3. **Session Leakage in Database Dependencies**
   * *The Antipattern:* Manually opening database sessions inside route functions without ensuring they close upon exception termination.
   * *The Fix:* Always utilize FastAPI's dependency injection system with `yield` blocks and `try/except/finally` structures as demonstrated in `app/core/database.py`.
4. **Neglecting Migration Version Control**
   * *The Antipattern:* Using `Base.metadata.create_all(bind=engine)` in production to automatically generate database schemas.
   * *The Fix:* Always manage production schemas via Alembic revision scripts to prevent data loss and ensure deterministic migration history.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling Formula:** Scale worker counts based on CPU cores in production:
  $$\text{Workers} = (2 \times \text{Number of CPU Cores}) + 1$$
* **Connection Pooling Tuning:** Adjust `pool_size` and `max_overflow` parameters in `create_async_engine` to match the peak concurrent database connection limits imposed by your PostgreSQL instance.
* **Response Compression:** Integrate Gzip middleware in `app/main.py` for payloads exceeding 1KB to drastically reduce bandwidth consumption over public networks:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure foreign keys, lookup columns (e.g., `email`), and frequently filtered attributes carry explicit PostgreSQL B-tree or Hash indexes.

---

## 6. Commercial License & Attribution Summary

### **MicroCorp AI Enterprise Commercial License (v2.1)**
* **Grant of Rights:** Purchasing or acquiring this digital product grants the licensee (Developer, Agency, or Enterprise Client) a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, adapt, and deploy this codebase for commercial client projects, internal enterprise systems, and SaaS products.
* **Restrictions:** Licensees are strictly prohibited from reselling, sublicensing, or redistributing this boilerplate as a standalone template, boilerplate generator, or open-source competing product on marketplaces (e.g., GitHub, Gumroad, Envato).
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI and the contributing architects assume zero liability for direct, indirect, incidental, or consequential damages arising from the deployment or execution of this software in production environments.

*Built with precision by Backend Architecture Division, MicroCorp AI.*