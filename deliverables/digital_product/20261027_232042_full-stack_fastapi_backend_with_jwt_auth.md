# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Turnkey Solution Architecture*

---

## 1. Product Title & Value Proposition

### 🚀 Enterprise FastAPI Boilerplate: Production-Ready JWT Auth, Async PostgreSQL, & Docker Multi-Stage Pipeline

#### The Value Proposition
Building a modern asynchronous backend from scratch requires stitching together dozens of disparate technologies: database connection pooling, Pydantic v2 data validation, secure password hashing, JWT bearer token lifecycle management, and containerized deployment pipelines. 

This turnkey solution eliminates weeks of boilerplate setup. It provides a battle-tested, highly performant FastAPI architecture designed specifically for high-throughput microservices and SaaS products. Fully typed, meticulously structured, and packaged with a production-grade Docker configuration, this product allows engineering teams and solo founders to bypass infrastructure setup and immediately focus on core business logic.

---

## 2. Quick Start & Core Concepts

Get your local development environment running in under 60 seconds.

### Prerequisites
* Docker Engine 24.0+ & Docker Compose v2.20+
* Python 3.11+ (for local bare-metal execution)

### 3-Step Initialization
```bash
# 1. Clone the repository and navigate into the project directory
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Configure your environment variables
cp .env.example .env

# 3. Spin up the containers in detached mode
docker compose up --build -d
```

Verify the installation by visiting `http://localhost:8000/docs` for the interactive Swagger documentation.

### Architectural Anatomy & Clean Syntax Reference

| Component | Technology | Role in Stack | Core Syntax Pattern |
| :--- | :--- | :--- | :--- |
| **Framework** | FastAPI 0.110+ | Asynchronous REST API routing & validation | `@app.get("/", response_model=UserRead)` |
| **Validation** | Pydantic v2 | Strict serialization & settings management | `model_config = ConfigDict(from_attributes=True)` |
| **ORM** | SQLAlchemy 2.0 | Async database interaction & query building | `result = await session.execute(select(User))` |
| **Database** | PostgreSQL 16 | Relational persistence layer | `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";` |
| **Auth** | python-jose & passlib | JWT generation & bcrypt hashing | `jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)` |
| **Container** | Docker | Multi-stage build & orchestration | `FROM python:3.11-slim AS builder` |

---

## 3. Production Code Patterns & Architecture Examples

This architecture follows a strict separation of concerns: **Routers** handle HTTP delivery, **CRUD/Services** handle business logic, **Models** define persistence, and **Schemas** govern boundaries.

### Project File Structure
```tree
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   └── users.py
│   │   │   └── api.py
│   │   └── deps.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

### File 1: `app/core/config.py` (Environment Configuration)
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
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
```

---

### File 2: `app/core/database.py` (Async SQLAlchemy Session Management)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
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

### File 3: `app/core/security.py` (Cryptographic Utilities & JWT Handling)
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
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### File 4: `app/models/user.py` (SQLAlchemy 2.0 ORM Model)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

---

### File 5: `app/schemas/user.py` (Pydantic v2 Schemas)
```python
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str | None = None
```

---

### File 6: `app/api/deps.py` (Authentication Dependencies)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
```

---

### File 7: `app/api/v1/endpoints/auth.py` (Authentication Router)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }
```

---

### File 8: `app/main.py` (Application Factory)
```python
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### File 9: `Dockerfile` (Production Multi-Stage Build)
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runner
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

---

### File 10: `docker-compose.yml` (Local Orchestration)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: always
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
      - POSTGRES_PASSWORD=password123
      - POSTGRES_DB=enterprise_db
      - POSTGRES_PORT=5432
      - SECRET_KEY=supersecretkeychangeinproduction998877
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Blocking I/O in Async Routes:** Never use synchronous libraries (like standard `requests` or synchronous database drivers like `psycopg2`) inside `async def` endpoints. This blocks the entire event loop. Always use `asyncpg` and asynchronous HTTP clients like `httpx`.
2. ❌ **Hardcoding Secrets:** Never commit `.env` files or hardcode JWT secrets inside application files. Always inject secrets via environment variables or secret managers (AWS Secrets Manager, HashiCorp Vault).
3. ❌ **Not Closing Database Sessions:** Failing to use context managers (`async with`) for database sessions leads to connection leaks, eventually starving the connection pool and causing database lockups under high load.
4. ❌ **Catching Base Exceptions blindly:** Avoid writing `except Exception:` without re-raising or logging appropriately. This masks internal server errors and can accidentally capture system exit signals or validation failures.

---

## 5. Performance & Optimization Tips

* **Enable Uvicorn Workers for Multi-Core CPUs:** In production, run Uvicorn with Gunicorn or leverage multiple workers via command line args (`uvicorn app.main:app --workers 4`) behind a reverse proxy like Nginx to utilize multi-core server architectures.
* **Database Connection Pool Tuning:** Adjust `pool_size` and `max_overflow` in your SQLAlchemy engine config depending on your database hardware limits and peak concurrent thread expectations.
* **Response Compression:** Install and integrate `starlette.middleware.gzip.GZipMiddleware` to automatically compress large JSON payloads, significantly reducing network bandwidth consumption over the wire.
* **Indexing Foreign Keys:** Ensure database indexes are explicitly defined on frequently queried columns, foreign keys, and unique identifiers (e.g., `index=True` on user emails).

---

## 6. Commercial License & Attribution Summary

### 📄 MicroCorp Enterprise Commercial License v1.0
* **Permitted Usage:** You are granted a perpetual, non-exclusive, worldwide license to use, modify, distribute, and deploy this codebase for commercial software products, client deliverables, and internal startup applications.
* **Restrictions:** You may not resell this repository, boilerplate, or derivative works as a standalone software development template or boilerplate kit on marketplaces (e.g., Gumroad, GitHub Marketplace, Envato) without explicit prior written authorization from MicroCorp AI.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. The authors and MicroCorp AI shall not be held liable for any claim, damages, or liabilities arising from the deployment or execution of this code in production environments.