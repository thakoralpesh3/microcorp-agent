# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Enterprise Delivery Kit*

---

## 1. # Product Title & Value Proposition

### 🚀 Enterprise FastAPI Turnkey Boilerplate
This commercial-grade, production-ready backend template is engineered for rapid deployment. It bridges the gap between rapid prototyping and enterprise-grade scale, providing a hardened foundation for modern web applications, microservices, and AI-driven APIs.

### 💼 Commercial Value Proposition
* **Time-to-Market Acceleration:** Save 40+ hours of boilerplate setup, security hardening, and containerization configuration.
* **Security First:** Implements robust OAuth2 with JWT (JSON Web Tokens), secure password hashing via `passlib[bcrypt]`, and strict CORS/middleware policies out of the box.
* **Modern Developer Experience:** Fully typed with Python 3.11+ type hints, Pydantic v2 data validation, and asynchronous database operations using SQLAlchemy 2.0.
* **Production Containerization:** Optimized multi-stage Dockerfiles and a complete `docker-compose.yml` stack incorporating PostgreSQL and Redis caching.

---

## 2. ## Quick Start & Core Concepts

### System Architecture Overview
```
[ Client / Frontend ]
        │
        ▼ (HTTPS / Bearer Token)
[ Nginx / Reverse Proxy ] (Optional)
        │
        ▼
[ FastAPI Application Core ] ── (Async) ──► [ PostgreSQL Database ]
        │
        ├──► [ Redis (Rate Limiting / Caching) ]
        └──► [ Pydantic v2 (Validation Layer) ]
```

### Core Technology Matrix

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous REST API routing and auto-docs. |
| **Data Validation** | Pydantic v2 | Runtime data parsing, serialization, and settings management. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Enterprise-grade Object-Relational Mapping with async support. |
| **Database Engine** | PostgreSQL 15 | ACID-compliant relational data store. |
| **Authentication** | `python-jose` & `passlib` | Stateless JWT issuance, verification, and bcrypt password hashing. |
| **Containerization** | Docker & Compose | Isolated, reproducible multi-container runtime environments. |

---

## 3. ## Production Code Patterns & Architecture Examples

### 📁 Project Directory Structure
```text
fastapi-enterprise-backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py
│   └── api/
│       ├── __init__.py
│       ├── deps.py
│       └── v1/
│           ├── __init__.py
│           ├── api.py
│           └── endpoints/
│               ├── auth.py
│               └── users.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

### 📄 Configuration Management (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise FastAPI Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    SQLALCHEMY_DATABASE_URI: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

---

### 📄 Database Session Manager (`app/core/database.py`)
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
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

### 📄 Security & JWT Utilities (`app/core/security.py`)
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
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### 📄 SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

---

### 📄 Pydantic Validation Schemas (`app/schemas/user.py`)
```python
import uuid
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserRead(UserBase):
    id: uuid.UUID
    is_superuser: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str | None = None
```

---

### 📄 API Dependencies (`app/api/deps.py`)
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
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(sub=payload.get("sub"))
        if token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalar_one_or_none()
    
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

### 📄 Authentication Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter()

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
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
        
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### 📄 Main Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### 🐳 Docker Configuration

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: postgres_user
      POSTGRES_PASSWORD: secure_password_here
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    restart: always

  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=secure_password_here
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=super_secret_jwt_key_change_in_production
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. **Blocking Synchronous I/O in Async Routes**
   * *The Antipattern:* Using synchronous database drivers (`psycopg2`) or blocking CPU-bound tasks (like heavy JSON parsing or cryptography) directly inside an `async def` route path. This starves the Uvicorn event loop.
   * *The Fix:* Always use asynchronous drivers (`asyncpg`) and offload CPU-intensive operations via `starlette.concurrency.run_in_threadpool`.

2. **Hardcoding Application Secrets**
   * *The Antipattern:* Committing database connection strings, API keys, or JWT secrets directly into codebase version control.
   * *The Fix:* Use Pydantic BaseSettings coupled with a strictly local `.env` file excluded via `.gitignore`.

3. **Insecure Session Management / Missing Token Expiry**
   * *The Antipattern:* Creating JWT tokens without explicit expiration timestamps (`exp`), allowing compromised tokens to remain valid indefinitely.
   * *The Fix:* Always set deterministic expiration windows using datetime delta offsets.

4. **Ignoring Database Connection Pool Exhaustion**
   * *The Antipattern:* Instantiating unmanaged database connections per request without pooling constraints.
   * *The Fix:* Configure SQLAlchemy engine parameters (`pool_size`, `max_overflow`) appropriately for concurrent traffic.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production environments behind a reverse proxy (Nginx), deploy multiple Uvicorn worker processes using Gunicorn as a process manager:
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
* **Database Indexing Strategy:** Ensure high-cardinality lookup fields (`email`, foreign keys) include explicit index definitions (`index=True`) to prevent sequential table scans.
* **Response Serialization Optimization:** For high-throughput endpoints returning massive payloads, leverage ORM streaming or configure Pydantic model configurations for high-speed serialization.
* **Caching Layer Integration:** Integrate Redis for caching read-heavy endpoints and enforcing distributed rate limiting via middleware.

---

## 6. ## Commercial License & Attribution Summary

### 📄 MIT Commercial License Terms
Copyright © 2024 MicroCorp AI & The Agency Engineering Division.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.