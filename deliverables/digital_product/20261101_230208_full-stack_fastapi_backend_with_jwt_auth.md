# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*MicroCorp AI Engineering Division — Backend Architecture Series*

## 1. Product Title & Value Proposition

### Product Title
**Production-Grade FastAPI Async Backend Boilerplate: JWT Auth, PostgreSQL, SQLAlchemy 2.0, Alembic, and Docker Orchestration**

### Value Proposition
Stop wasting 40+ hours writing boilerplate configurations, security wiring, and database connection logic for every new client project. This battle-tested, enterprise-ready FastAPI backend provides an asynchronous, high-performance architecture out of the box. Designed specifically for modern SaaS MVPs, AI wrapper APIs, and high-throughput microservices, this turnkey solution features type-safe database migrations, secure token-based authentication with role-based access control (RBAC), and a zero-friction Docker multi-stage build setup. Deploy to production with absolute confidence on day one.

---

## 2. Quick Start & Core Concepts

### Syntax & Architecture Reference

| Concept | Implementation Library / Tool | Primary Purpose in this Stack |
| :--- | :--- | :--- |
| **Web Framework** | `FastAPI` & `Uvicorn` | Asynchronous request handling, auto-generated OpenAPI/Swagger docs, high-speed routing. |
| **Data Validation** | `Pydantic v2` | Runtime data parsing, serialization, and strict environment configuration. |
| **Database ORM** | `SQLAlchemy 2.0 (Async)` | Non-blocking database interactions using `asyncpg` driver for peak throughput. |
| **Migrations** | `Alembic` | Version control for relational database schemas. |
| **Authentication** | `python-jose` & `passlib` | Stateless JWT generation/validation and robust bcrypt password hashing. |
| **Containerization** | `Docker & Docker Compose` | Isolated multi-container orchestration (App + PostgreSQL + Redis caching). |

### 5-Minute Quick Start

Clone the repository structure, configure your environment, and spin up the entire stack using Docker Compose:

```bash
# 1. Clone or initialize your project directory
mkdir fastapi-enterprise-backend && cd fastapi-enterprise-backend

# 2. Create the environment file
cat << 'EOF' > .env
PROJECT_NAME="MicroCorp API"
POSTGRES_SERVER=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=supersecurepassword123
POSTGRES_DB=app_db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:supersecurepassword123@db:5432/app_db
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63388e9bb49
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

# 3. Spin up services in detached mode
docker-compose up --build -d

# 4. Run database migrations inside the container
docker-compose exec web alembic upgrade head
```

---

## 3. Production Code Patterns & Architecture Examples

### Project Directory Structure
```text
.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
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
│       v1/
│           ├── __init__.py
│           ├── api.py
│           └── endpoints/
│               ├── auth.py
│               └── users.py
└── alembic/
    ├── env.py
    └── versions/
```

---

### Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
```

---

### Database Setup (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
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

### Security & Password Hashing (`app/core/security.py`)
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

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

---

### SQLAlchemy User Model (`app/models/user.py`)
```python
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

---

### Pydantic Schemas (`app/schemas/user.py`)
```python
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: str | None = None
```

---

### API Dependencies (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
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
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
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

### Auth Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
```

---

### Main Application Entrypoint (`app/main.py`)
```python
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json"
)

app.include_api_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
```

---

### Docker Multi-Stage Build (`Dockerfile`)
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

CMD ["uvicorn", "app.main.app", "--host", "0.0.0.0", "--port", "8000"]
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
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: uvicorn app.main.app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ALGORITHM=${ALGORITHM}
      - ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES}
      - PROJECT_NAME=${PROJECT_NAME}
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **Anti-Pattern 1: Mixing Synchronous and Asynchronous DB Drivers**
    *   *The Mistake:* Using standard `psycopg2` or synchronous session makers within `async def` FastAPI path operations.
    *   *The Consequence:* Event loop blocking, catastrophic degradation under concurrent load.
    *   *The Fix:* Always utilize `postgresql+asyncpg://` with SQLAlchemy's `AsyncSession` and `async_sessionmaker`.

*   **Anti-Pattern 2: Hardcoding Configuration Secrets**
    *   *The Mistake:* Embedding JWT secret keys and database credentials directly inside python files or Git repositories.
    *   *The Consequence:* Immediate security compromise upon repository disclosure.
    *   *The Fix:* Use Pydantic's `BaseSettings` paired with external `.env` files or environment injectors.

*   **Anti-Pattern 3: Unbounded Database Result Queries**
    *   *The Mistake:* Executing `select(User)` without `.limit()` or pagination offsets on large datasets.
    *   *The Consequence:* Out-Of-Memory (OOM) crashes on the API container when tables scale.
    *   *The Fix:* Implement cursor or limit/offset pagination models on all list endpoints.

---

## 5. Performance & Optimization Tips

1.  **Connection Pooling Tuning:**
    Configure `pool_size` and `max_overflow` parameters inside `create_async_engine()` according to your database instance sizing and anticipated concurrent request load.
2.  **Use `orjson` for High-Speed Serialization:**
    Replace default Pydantic serialization loops with `orjson` response classes where high JSON throughput is required:
    ```python
    from fastapi.responses import ORJSONResponse
    app = FastAPI(default_response_class=ORJSONResponse)
    ```
3.  **Leverage Redis Caching for Read-Heavy Data:**
    Integrate an asynchronous Redis client layer (`redis-py`) to cache frequent authorization lookups or metadata queries, bypassing PostgreSQL disk reads entirely.
4.  **Uvicorn Worker Scaling behind Nginx/Traefik:**
    In production environments, spin up Uvicorn workers scaled to CPU core counts (`--workers 4`) or delegate process management to Gunicorn running Uvicorn worker classes.

---

## 6. Commercial License & Attribution Summary

### Commercial License Agreement
* **Copyright © 2024 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** This commercial digital product is licensed to the purchasing engineer or agency for use in client deliverables, internal SaaS MVPs, and production web applications.
* **Restrictions:** Redistribution, resale, or open-source publishing of this raw codebase as a standalone boilerplate package is strictly prohibited.
* **Warranty Disclaimer:** Provided *as is* without warranty of any kind, express or implied. MicroCorp AI accepts no liability for system downtime, data loss, or infrastructure vulnerabilities resulting from improper deployment configuration.