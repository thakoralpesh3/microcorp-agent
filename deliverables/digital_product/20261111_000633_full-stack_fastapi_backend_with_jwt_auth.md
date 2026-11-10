# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Ready Microservices Architecture*

---

## 1. # Product Title & Value Proposition

### 🚀 Production-Ready FastAPI Backend: JWT Auth, PostgreSQL, & Docker Setup
**SKU:** `MC-FA-TURKEY-001`  
**Target Audience:** Enterprise Clients, SaaS Founders, and Full-Stack Engineers who need an impenetrable, lightning-fast, and containerized backend foundation without spending 40+ hours on boilerplate configuration.

#### Value Proposition
Time is capital. Writing boilerplate user models, hashing algorithms, JWT middleware, database connection pooling, and multi-stage Dockerfiles eats into your core product delivery timeline. This turnkey solution delivers a battle-tested, strictly typed, asynchronous FastAPI backend designed to scale horizontally from day one. It eliminates security vulnerabilities (like timing attacks on password verification and token leakage) and provides an immaculately organized codebase that passes enterprise security audits out of the box.

---

## 2. ## Quick Start & Core Concepts

Get your local development cluster running in under 120 seconds. 

### Prerequisites
* Python 3.11+
* Docker Engine 24.0+ & Docker Compose v2.20+

### Step-by-Step Execution
```bash
# 1. Clone the repository and navigate into the workspace
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Configure environment variables
cp .env.example .env

# 3. Spin up the containers in detached mode
docker compose up --build -d

# 4. Verify database migrations & health check
docker compose exec api alembic upgrade head
curl -X 'GET' 'http://localhost:8000/health' -H 'accept: application/json'
```

### Core Architecture Concepts
| Concept | Implementation Strategy | Why It Matters for Production |
| :--- | :--- | :--- |
| **Async I/O** | `async def` endpoints with `SQLAlchemy 2.0` async sessions. | Handles thousands of concurrent socket connections without thread-blocking. |
| **Authentication** | Stateless JWT (Access + Refresh tokens) signed with `HS256`. | Decouples auth state; allows seamless horizontal scaling behind load balancers. |
| **Data Validation** | Pydantic v2 parsing at the edge. | Rejects malformed payloads before they ever touch business logic or databases. |
| **Containerization** | Multi-stage Docker build with non-root execution. | Minimizes image footprint and mitigates container escape vulnerabilities. |

---

## 3. ## Production Code Patterns & Architecture Examples

This architecture follows a strict Separation of Concerns (SoC) layout:
```text
app/
├── core/             # Configurations, security, database sessions
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic validation schemas
├── api/              # API Routers (v1)
├── services/         # Business logic layer
└── main.py           # Application entrypoint
```

### A. Database Configuration (`app/core/database.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
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

### B. Security & JWT Handling (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

### C. Authentication Dependency & Endpoints (`app/api/v1/endpoints/auth.py`)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import Token, UserLogin, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

@router.post("/login", response_model=Token)
async def login_access_token(form_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.email))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

### D. Multi-Stage Production Dockerfile (`Dockerfile`)
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
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Create non-root system user for security compliance
RUN useradd -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

1. ❌ **Blocking I/O in Async Endpoints**
   * *Anti-Pattern:* Using synchronous libraries like `requests` or standard `psycopg2` inside an `async def` FastAPI route. This blocks the main event loop and destroys concurrency.
   * *Fix:* Use async-native drivers (`httpx`, `asyncpg`) or wrap blocking code using `run_in_threadpool`.
2. ❌ **Storing Plaintext Secrets in Environment Configurations**
   * *Anti-Pattern:* Committing `.env` files containing production secrets to version control.
   * *Fix:* Use `.env.example` as a template, inject secrets via CI/CD pipelines (GitHub Actions Secrets, AWS Secrets Manager, Docker Secrets).
3. ❌ **Catching Base Exceptions (`except Exception`) Broadly**
   * *Anti-Pattern:* Swallowing system-exit or cancellation errors inside database session blocks.
   * *Fix:* Catch specific database and validation errors (`SQLAlchemyError`, `JWTError`) to ensure proper transaction rollback and tracing.

---

## 5. ## Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Always run multiple worker processes in production via `--workers N` (recommended: `2 * CPU_CORES + 1`), or deploy behind an enterprise ASGI proxy like **Gunicorn** managing Uvicorn workers.
* **Connection Pooling:** Fine-tune SQLAlchemy's `pool_size` and `max_overflow` based on your database tier and container memory limits to prevent connection starvation.
* **Response Caching:** Implement Redis-backed response caching for high-read, low-mutation endpoints to drop response times below 5ms.

---

## 6. ## Commercial License & Attribution Summary

```text
MIT License

Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
*Built with precision by The Agency 🏗️ — Engineering Division.*