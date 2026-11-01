# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division — Turnkey Deliverable*

---

## 1. Product Title & Value Proposition

### **Enterprise FastAPI Turnkey Engine**
A production-ready, highly scalable, asynchronous backend boiler-plate featuring robust JWT authentication, SQLAlchemy 2.0 async engine, Pydantic v2 data validation, Alembic database migrations, and a fully containerized Docker & Docker Compose orchestration setup.

#### **Value Proposition**
* **Save 60+ Development Hours:** Skip the tedious boilerplate setup. Get straight to writing business logic with a pre-configured, battle-tested architecture.
* **Security First:** Implements industry-standard OAuth2 with Password (and hashing via `passlib[bcrypt]`), HTTP-only cookie or Bearer JWT token strategy, and strict CORS configuration out of the box.
* **Modern Async Stack:** Leverages Python 3.11+, FastAPI, and AsyncPG for maximum throughput and low-latency database queries.
* **Zero-Friction Deployment:** Spin up your entire local development and production stack (API, PostgreSQL, Redis) with a single `docker compose up --build` command.

---

## 2. Quick Start & Core Concepts

### **Architecture Stack Overview**

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance, automatic interactive docs (Swagger/ReDoc). |
| **Data Validation** | Pydantic v2 | Strict serialization, deserialization, and settings management. |
| **ORM & Migrations**| SQLAlchemy 2.0 (Async) + Alembic | Database mapping and version-controlled schema migrations. |
| **Database** | PostgreSQL 16 + AsyncPG | Relational data persistence with native async driver. |
| **Caching/Broker** | Redis 7 | Rate limiting, background task queues (Celery ready). |
| **Containerization**| Docker & Docker Compose | Multi-stage builds for minimal image size and secure deployment. |

### **5-Minute Quick Start**

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-engine.git
   cd fastapi-jwt-docker-engine
   cp .env.example .env
   ```

2. **Spin Up with Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify the Installation:**
   * API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   * Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
.
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1)
│   │   ├── endpoints/       # Auth, Users, Health
│   │   └── deps.py          # Dependency injections (DB, Current User)
│   ├── core/                # Config, Security, Database setup
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   └── main.py              # Application entrypoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

### **Core Configuration (`app/core/config.py`)**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
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

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True, 
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### **Database Engine & Session (`app/core/database.py`)**
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True
)

SessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
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

### **JWT & Password Security (`app/core/security.py`)**
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

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **FastAPI Authentication Dependencies (`app/api/deps.py`)**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalars().first()
    
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
```

---

### **Authentication Endpoints (`app/api/endpoints/auth.py`)**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import Token

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
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### **Application Entrypoint (`app/main.py`)**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, users, health
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production to exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])

@app.get("/")
async def root():
    return {"message": "Welcome to MicroCorp FastAPI Engine. Visit /docs for API documentation."}
```

---

### **Dockerized Architecture Configuration**

#### **Dockerfile (Multi-Stage Production Build)**
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production runtime image
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

#### **docker-compose.yml**
```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: microcorp_fastapi
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=microcorp_prod
      - SECRET_KEY=supersecretjwtkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy
    networks:
      - microcorp-net

  db:
    image: postgres:16-alpine
    container_name: microcorp_postgres
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=microcorp_prod
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d microcorp_prod"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - microcorp-net

volumes:
  postgres_data:

networks:
  microcorp-net:
    driver: bridge
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Synchronous Operations in Async Endpoints**
   * *Anti-Pattern:* Calling blocking I/O libraries (like standard `requests` or blocking DB calls like standard `psycopg2`) inside an `async def` path operation function. This freezes the entire event loop thread.
   * *Solution:* Use async-native drivers (`asyncpg`, `httpx`) or offload blocking CPU-heavy operations via `run_in_threadpool`.

2. **Hardcoding Secrets or Settings Configuration**
   * *Anti-Pattern:* Keeping JWT secret keys or database passwords hardcoded in python source code files.
   * *Solution:* Always use Pydantic `BaseSettings` reading environment variables through a securely guarded `.env` file excluded from version control via `.gitignore`.

3. **Not Using Connection Pool Ping (`pool_pre_ping=True`)**
   * *Anti-Pattern:* Creating database engines without connection health checks, leading to dropped connection exceptions after periods of database inactivity (`OperationalError: server closed the connection unexpectedly`).
   * *Solution:* Always instantiate SQLAlchemy engines with `pool_pre_ping=True` to automatically validate connections before query execution.

4. **Exposing ORM Models Directly as Responses**
   * *Anti-Pattern:* Returning raw SQLAlchemy database models directly from FastAPI endpoints. This can inadvertently expose sensitive internal attributes (such as `hashed_password`) or trigger lazy-loading recursion errors.
   * *Solution:* Always map your database models to explicitly declared Pydantic response schemas (`response_model=UserResponse`).

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling via Gunicorn:** In production environments, run Uvicorn with multiple worker processes using Gunicorn as a process manager to utilize all CPU cores:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Response Compression:** Add Starlette's `GZipMiddleware` to compress large JSON responses automatically and reduce network payload overhead:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure frequently queried relational fields (e.g., `email`, foreign key IDs) have explicit database indices defined in your SQLAlchemy models (`index=True`).
* **Dependency Caching (`lru_cache`):** Cache configuration settings instantiation using `@lru_cache()` so that environment checks do not repeatedly re-read the `.env` disk storage on every request cycle.

---

## 6. Commercial License & Attribution Summary

### **MicroCorp Commercial License Agreement**
* **Copyright (c) 2026 MicroCorp AI. All Rights Reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, copy, and distribute this codebase for commercial and non-commercial client projects, software-as-a-service (SaaS) applications, and enterprise internal infrastructure.
* **Restrictions:** This digital asset cannot be resold, sub-licensed, or repackaged as a competing standalone boiler-plate template, boilerplate generator, or SaaS kit on digital marketplaces (e.g., GitHub Marketplace, Gumroad, Envato) without explicit prior written authorization from MicroCorp AI.
* **No Warranty:** This product is provided "as is" without warranty of any kind, express or implied. MicroCorp AI and The Agency Engineering Division shall not be held liable for any direct, indirect, incidental, or consequential damages arising out of the use or inability to use this software package.