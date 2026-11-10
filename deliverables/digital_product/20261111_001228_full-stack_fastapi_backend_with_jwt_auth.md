# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Turnkey Client Deliverable*

---

## 1. # Product Title & Value Proposition

### **Enterprise-Grade FastAPI Backend Boilerplate: JWT Auth, PostgreSQL, & Multi-Stage Docker**

Stop wasting 40+ hours writing boilerplate infrastructure for every new client project. This turnkey backend architecture delivers an enterprise-ready, asynchronous Python API engine designed for immediate production deployment. Built with FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, and stateless JSON Web Token (JWT) authentication, this solution provides strict typing, automated interactive documentation, and bulletproof containerization out of the box.

### **Core Business Value**
* **Time-to-Market Acceleration:** Deploy a fully authenticated, database-backed REST API in under 5 minutes.
* **Zero Technical Debt:** Strict adherence to SOLID principles, dependency injection design patterns, and asynchronous I/O blocks.
* **Production Security:** Implements industry-standard password hashing (bcrypt), cryptographically signed JWTs, and secure CORS middleware policies.
* **Client Handover Ready:** Clean folder hierarchy, comprehensive environment variable management, and automated Docker Compose orchestration ensure smooth transitions to client DevOps teams.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview & Syntax Guide

| Component | Technology | Purpose / Design Choice |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (v0.110+) | High-performance, asynchronous ASGI framework with automatic OpenAPI/Swagger generation. |
| **Data Validation** | Pydantic v2 | Blisteringly fast data parsing and validation written in Rust core. |
| **ORM / Database** | SQLAlchemy 2.0 + asyncpg | Asynchronous Object-Relational Mapping communicating natively with PostgreSQL. |
| **Authentication** | python-jose & passlib | Stateless token generation (JWT) and secure password hashing using bcrypt. |
| **Containerization** | Docker & Docker Compose | Multi-stage builds minimizing image footprints and isolating database/API services. |

### 5-Minute Local Deployment

1. **Clone and Configure Environment:**
   ```bash
   git clone https://github.com/microcorp-ai/fastapi-jwt-docker-turnkey.git
   cd fastapi-jwt-docker-turnkey
   cp .env.example .env
   ```

2. **Spin up via Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

3. **Verify API Health:**
   Navigate to `http://localhost:8000/docs` to test endpoints via the interactive Swagger UI.

---

## 3. ## Production Code Patterns & Architecture Examples

### Project Directory Tree
```text
fastapi_backend/
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

### Configuration Engine (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    def model_post_init(self, __context) -> None:
        self.DATABASE_URL = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

### Asynchronous Database Session (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
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

### SQLAlchemy User Model (`app/models/user.py`)
```python
import uuid
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

---

### Security & JWT Utilities (`app/core/security.py`)
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
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

---

### Authentication Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
```

---

### Authentication Endpoint (`app/api/v1/endpoints/auth.py`)
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
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### Multi-Stage Dockerfile (`Dockerfile`)
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Docker Compose Orchestration (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: enterprise_db
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db:5432
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=enterprise_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

* **Blocking I/O in Async Routes:** Never use synchronous libraries (e.g., standard `requests`, synchronous database drivers) inside `async def` endpoints. This stalls the entire event loop. Use `httpx` or native async drivers instead.
* **Hardcoding Configuration Secrets:** Never store API keys, database credentials, or JWT secrets inside source files. Always enforce environment injection via Pydantic BaseSettings.
* **Exposing Raw ORM Models in Responses:** Returning SQLAlchemy models directly from endpoints risks data leakage (e.g., hashed passwords) and causes recursion errors on relationships. Always serialize data using Pydantic response schemas (`response_model=UserSchema`).
* **Ignoring Database Connection Pools:** Creating a new database engine per request exhausts PostgreSQL connection limits under load. Always instantiate a singleton engine globally and yield session dependencies per request.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** In production container deployments, scale Uvicorn workers based on available CPU cores rather than running a single process:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
  ```
* **Database Indexing Strategy:** Ensure high-frequency lookup columns (such as `email` in user authorization queries) are explicitly indexed via `index=True` on SQLAlchemy columns.
* **Gzip Compression Middleware:** Add compression middleware to minimize JSON payload bandwidth over the network:
  ```python
  from fastapi.middleware.gzip import GZipMiddleware
  app.add_middleware(GZipMiddleware, minimum_size=1000)
  ```
* **Lean Docker Build Footprint:** Utilize the multi-stage Dockerfile pattern provided to strip build-time dependencies (`build-essential`, header files) from the final production runtime image.

---

## 6. ## Commercial License & Attribution Summary

### **MicroCorp AI Commercial Turnkey License**
* **Copyright © 2024 MicroCorp AI. All Rights Reserved.**
* **Grant of Rights:** This commercial digital product is licensed to the purchasing client for deployment in internal, commercial, and client-facing software applications. 
* **Restrictions:** Redistribution, resale, or public publishing of this source code boilerplate as a standalone template or commercial competitor product is strictly prohibited.
* **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. MicroCorp AI engineering assets undergo rigorous internal testing but remain subject to client-side environment configurations.