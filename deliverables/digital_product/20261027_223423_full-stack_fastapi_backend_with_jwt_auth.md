# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*A Production-Grade, Turnkey Microservices Boilerplate for Enterprise Clients*

---

## 1. # Product Title & Value Proposition

### **Enterprise FastAPI Turnkey Boilerplate: Async Architecture, Secure JWT Authentication, and Dockerized Production Readiness**

#### **Value Proposition**
Building a modern, secure, and performant backend from scratch takes weeks of boilerplate setup, security hardening, and infrastructure configuration. This commercial turnkey solution provides engineers and agencies with a battle-tested, production-ready FastAPI backend. It features native asynchronous database operations via SQLAlchemy 2.0, robust OAuth2 with JWT Bearer token authentication, role-based access control (RBAC), Alembic database migrations, and a fully orchestrated Docker Compose environment. 

Deploy faster, secure your endpoints out-of-the-box, and scale effortlessly from day one.

---

## 2. ## Quick Start & Core Concepts

### **The Architecture Stack**
| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI | `0.110+` | High-performance asynchronous API routing & validation |
| **Runtime** | Uvicorn / Gunicorn | `0.27+` | ASGI server implementation |
| **Database ORM** | SQLAlchemy | `2.0+` | Async ORM and data modeling |
| **Migrations** | Alembic | `1.13+` | Database schema version control |
| **Database** | PostgreSQL | `15+` | Relational data persistence layer |
| **Authentication** | python-jose & passlib | Latest | JWT generation, validation, and bcrypt hashing |
| **Containerization** | Docker & Docker Compose | Latest | Reproducible multi-container development and production deployment |

---

### **5-Minute Local Setup**

1. **Clone and Configure Environment**
```bash
git clone https://github.com/microcorp/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate
cp .env.example .env
```

2. **Spin Up Services via Docker Compose**
```bash
docker compose up --build -d
```

3. **Verify the Deployment**
* API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
* Interactive Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)
* Health Check Endpoint: [http://localhost:8000/health](http://localhost:8000/health)

---

## 3. ## Production Code Patterns & Architecture Examples

### **Directory Structure**
```text
.
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── router.py
│   │   └── deps.py
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

### **1. Configuration Management (`app/core/config.py`)**
Using `pydantic-settings` to ensure robust type-safe environment variable parsing.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp FastAPI Engine"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    DATABASE_URL: str | None = None

    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def assemble_db_connection(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
if not settings.DATABASE_URL:
    settings.DATABASE_URL = settings.assemble_db_connection()
```

---

### **2. Asynchronous Database Engine (`app/core/database.py`)**
Configuring SQLAlchemy 2.0 with an async session factory.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False, 
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
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

### **3. Database Models (`app/models/user.py`)**
SQLAlchemy 2.0 declarative mapping with explicit typing.

```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

---

### **4. Security & JWT Utility (`app/core/security.py`)**
Bcrypt hashing and secure JSON Web Token generation.

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

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: str | Any) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **5. API Dependencies (`app/api/deps.py`)**
FastAPI dependency injection for database sessions and token verification.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
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

### **6. Authentication Endpoints (`app/api/v1/endpoints/auth.py`)**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, TokenResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False
    )
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=TokenResponse)
async def login(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

---

### **7. Application Entrypoint (`app/main.py`)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production to match client domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

---

### **8. Production Containerization (`Dockerfile` & `docker-compose.yml`)**

#### **`Dockerfile`**
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

#### **`docker-compose.yml`**
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
      POSTGRES_DB: production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_api
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=production_db
      - POSTGRES_PORT=5432
      - JWT_SECRET_KEY=supersecretjwtkeychangeinproduction123!@#
      - JWT_REFRESH_SECRET_KEY=supersecretrefreshkeychangeinproduction456!@#
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async Code in DB Calls**
   * *Anti-Pattern:* Utilizing standard `psycopg2` or synchronous SQLAlchemy Sessions inside `async def` FastAPI endpoints. This blocks the main event loop, causing catastrophic latency drops under concurrency.
   * *Correction:* Always use `asyncpg` driver packages coupled with `AsyncSession` and `create_async_engine`.

2. **Hardcoding Secret Keys & Configurations**
   * *Anti-Pattern:* Defining raw strings for `JWT_SECRET_KEY` inside operational files.
   * *Correction:* Enforce configuration strictly via environmental injections managed by Pydantic's `BaseSettings`.

3. **Exposing Raw Database Exceptions**
   * *Anti-Pattern:* Returning unhandled database integrity errors (like duplicate key exceptions) directly to clients, which leaks internal stack traces or database schema layouts.
   * *Correction:* Catch specific SQLAlchemy exceptions (`IntegrityError`) and throw generic, sanitized `HTTPException` payloads with matching `400` status codes.

---

## 5. ## Performance & Optimization Tips

* **Connection Pooling tuning:** Always configure `pool_size` and `max_overflow` matching your underlying database max connection thresholds to avoid exhaustion under heavy traffic spikes.
* **Uvicorn Worker Scaling:** In production containers, leverage multiple worker threads (`--workers 4` or use Gunicorn as an ASGI process manager) to saturate multi-core cloud instances.
* **Database Indexing:** Ensure frequently filtered columns (e.g., `users.email`) include explicit b-tree index declarations (`index=True`) to maintain $O(\log n)$ lookup performance.
* **Response Serialization:** For large datasets, utilize `orjson` as FastAPI's custom JSON response class to gain up to 10x serialization speed increases over the standard library `json` module.

---

## 6. ## Commercial License & Attribution Summary

### **Commercial End-User License Agreement (EULA)**
* **Copyright © MicroCorp AI. All Rights Reserved.**
* **Grant of Rights:** Purchasing or acquiring this document grants the licensee a non-exclusive, perpetual, worldwide license to use, modify, adapt, and deploy this codebase in commercial software projects, client deliverables, or internal SaaS applications.
* **Restrictions:** You **may not** resell, sublicense, redistribute, or openly publish this codebase as a standalone boilerplate kit on competing digital template marketplaces (e.g., Gumroad, ThemeForest, GitHub Marketplace) without explicit written consent from MicroCorp AI.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any direct, indirect, incidental, or consequential damages arising from the deployment of this code in production environments.