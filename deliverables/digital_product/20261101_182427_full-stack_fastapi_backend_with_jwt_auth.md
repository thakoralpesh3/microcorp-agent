# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Packet*

---

## 1. Product Title & Value Proposition

### **Product Name**
`FastAPI-Enterprise-Boilerplate: Production-Ready Asynchronous Backend with JWT Authentication, PostgreSQL, Alembic Migrations, and Multi-Stage Dockerization`

### **Value Proposition**
Building a modern, secure, and production-ready Python backend from scratch takes an average of **40 to 60 engineering hours**. This turnkey solution cuts that down to zero. 

Designed specifically for agency clients, freelance deliverables, and enterprise MVPs, this repository provides a bulletproof foundation using **FastAPI**, **SQLAlchemy 2.0 (Async)**, **Pydantic v2**, **PostgreSQL**, **JWT Authentication (OAuth2 Bearer)**, and a fully optimized **Docker Compose** production architecture. It implements industry best practices for security, dependency injection, database connection pooling, and automated environment management out of the box.

---

## 2. Quick Start & Core Concepts

### **Architecture Core Concepts**
| Component | Technology | Purpose in System |
| :--- | :--- | :--- |
| **Framework** | FastAPI (Python 3.11+) | Ultra-fast asynchronous web routing and automatic OpenAPI/Swagger documentation generation. |
| **Data Validation** | Pydantic v2 | Strict payload validation, serialization, and settings management via environment variables. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Non-blocking database queries and relationship management using `asyncpg`. |
| **Migrations** | Alembic | Version-controlled, reproducible database schema migrations. |
| **Authentication** | python-jose & Passlib | Secure token-based authentication using JSON Web Tokens (JWT) and bcrypt password hashing. |
| **Containerization** | Docker & Docker Compose | Multi-container orchestration ensuring zero-drift parity between development, staging, and production. |

### **Zero-to-Running in 3 Minutes**

1. **Clone the repository and navigate to the project root:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-enterprise-boilerplate.git
   cd fastapi-enterprise-boilerplate
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   *Update `.env` with your secure production secrets (e.g., `SECRET_KEY`, database credentials).*

3. **Spin up the stack using Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

4. **Verify the installation:**
   * **API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
   * **Alternative Docs (ReDoc):** [http://localhost:8000/redoc](http://localhost:8000/redoc)
   * **Health Check Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 3. Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
fastapi-enterprise-boilerplate/
├── alembic/                      # Database migrations
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py       # Login & token generation
│   │   │   │   └── users.py      # User management & profile routes
│   │   │   └── router.py         # Central API v1 router aggregator
│   │   └── deps.py               # FastAPI dependency injection (DB, Current User)
│   ├── core/
│   │   ├── config.py             # Pydantic BaseSettings config management
│   │   ├── database.py           # Async SQLAlchemy sessionmaker & base class
│   │   └── security.py           # JWT generation, verification, & password hashing
│   ├── models/
│   │   └── user.py               # SQLAlchemy User ORM model
│   ├── schemas/
│   │   └── user.py               # Pydantic models for request/response validation
│   └── main.py                   # FastAPI application factory
├── .env.example
├── Dockerfile                    # Multi-stage production Dockerfile
└── docker-compose.yml            # Local orchestration setup
```

---

### **1. Configuration Management (`app/core/config.py`)**
*Handles environment variables safely with strict type validation via Pydantic.*

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )


settings = Settings()
```

---

### **2. Asynchronous Database Engine (`app/core/database.py`)**
*Configures the asynchronous engine and session maker for non-blocking I/O operations.*

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


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

### **3. Security & Token Utilities (`app/core/security.py`)**
*Provides robust password hashing using bcrypt and JWT token generation/decryption.*

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
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### **4. SQLAlchemy User Model (`app/models/user.py`)**
*Standard production-ready relational schema with auditing timestamps.*

```python
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, func
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
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

---

### **5. Pydantic Schemas (`app/schemas/user.py`)**
*Validates incoming data payloads and defines sanitized response contracts.*

```python
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: uuid.UUID
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
```

---

### **6. Dependency Injection (`app/api/deps.py`)**
*Secures endpoints by parsing Authorization headers and verifying tokens against the database.*

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
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
    if user is None:
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
            detail="The user doesn't have enough privileges",
        )
    return current_user
```

---

### **7. Authentication API Endpoint (`app/api/v1/endpoints/auth.py`)**
*Handles user login, validation, and token issuance.*

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.user import Token

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token, token_type="bearer")
```

---

### **8. Application Factory (`app/main.py`)**
*Bootstraps the FastAPI instance with appropriate middleware configuration.*

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/api/v1/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### **9. Multi-Stage Production Dockerfile (`Dockerfile`)**
*Optimized multi-stage build keeping image size lean by separating build tools from production runtime.*

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
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### **10. Local Orchestration (`docker-compose.yml`)**
*Production-ready composition linking the web application to an isolated PostgreSQL instance.*

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
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

  web:
    build: .
    container_name: fastapi_web
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - PROJECT_NAME=FastAPI Enterprise API
      - SECRET_KEY=supersecretkeychangeinproduction12345
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secretpassword
      - POSTGRES_DB=enterprise_db
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Mixing Sync and Async Database Drivers**
   * *The Anti-Pattern:* Using standard `psycopg2` or synchronous SQLAlchemy sessions inside asynchronous FastAPI route handlers (`async def`). This blocks the main event loop and destroys application concurrency.
   * *The Fix:* Always use `asyncpg` combined with `create_async_engine` and `AsyncSession`.

2. **Hardcoding Secrets or Missing Environment Validation**
   * *The Anti-Pattern:* Hardcoding JWT secret keys or database passwords directly into code files.
   * *The Fix:* Use Pydantic's `BaseSettings` to enforce runtime environment variable checks. If a required secret is missing, the application should fail to start immediately rather than failing silently later.

3. **Inappropriate Database Session Handling**
   * *The Anti-Pattern:* Instantiating global database sessions or failing to properly close sessions, leading to connection pool exhaustion.
   * *The Fix:* Always utilize FastAPI's dependency injection system (`Depends(get_db)`) combined with context managers to guarantee clean session tear-down, even when unhandled exceptions occur.

4. **N+1 Query Traps in ORM Relationships**
   * *The Anti-Pattern:* Fetching a list of parent records and subsequently querying related children inside a loop within response serializers.
   * *The Fix:* Utilize explicit SQLAlchemy `selectinload` or `joinedload` options when constructing async queries.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production behind a reverse proxy (like Nginx or Traefik), run Uvicorn with multiple workers or utilize Gunicorn as a process manager with Uvicorn worker classes:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Connection Pooling Optimization:** Tune your SQLAlchemy async engine pool parameters (`pool_size`, `max_overflow`, and `pool_timeout`) based on your database server's capacity and expected traffic spikes.
* **Response Compression:** Integrate `GZipMiddleware` into your FastAPI application initialization to compress large JSON responses automatically and minimize payload transfer times over the network:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Database Indexing:** Ensure foreign keys and high-cardinality lookup columns (such as `email` or search slugs) have appropriate B-Tree indexes created via Alembic migrations.

---

## 6. Commercial License & Attribution Summary

### **Commercial Use Grant**
* **Licensed To:** Client / Purchaser
* **Scope:** This turnkey codebase may be used commercially, modified, rebranded, and deployed as part of internal company projects, client deliverables, or commercial Software-as-a-Service (SaaS) products.
* **Restrictions:** Reselling or redistributing this boilerplate as an independent, standalone template library or competing code-generator product is strictly prohibited.

### **Attribution & Support**
* **Engineered By:** The Agency Engineering Division (MicroCorp AI)
* **Warranty:** Provided *"as-is"* without warranty of any kind, express or implied. The engineering division maintains compliance with standard security best practices at the time of delivery.