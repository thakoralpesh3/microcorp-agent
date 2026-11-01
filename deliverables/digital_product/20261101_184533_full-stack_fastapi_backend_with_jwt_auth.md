# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division // Production-Grade Boilerplate & Client Handover Guide*

---

## 1. Product Title & Value Proposition

### **Enterprise FastAPI Boilerplate: Async Architecture, Secure JWT Auth, & Containerized Deployment**

Stop spending 40+ hours scaffolding boilerplate authentication layers, database connection pooling, and multi-stage Docker builds for every new client project. 

This turnkey solution delivers a battle-tested, production-ready backend foundation built on modern Python standards. Designed specifically for agency engineers and freelance developers delivering high-ticket APIs to clients on Fiverr and Upwork.

### **Key Business & Technical Metrics:**
*   **Time-to-Market Reduction:** Save 3–5 days of initial setup per project.
*   **Security First:** Out-of-the-box OAuth2 with Password (Bearer), Argon2/Bcrypt password hashing, and signed JWTs with expiration/refresh rotation mechanics.
*   **Developer Experience:** Fully typed with Python 3.11+ type hints, Pydantic v2 validation, SQLAlchemy 2.0 async ORM, and Alembic migrations.
*   **Infrastructure Ready:** Fully containerized via Docker and Docker Compose with zero-friction local development and production hot-reloads.

---

## 2. Quick Start & Core Concepts

Get this backend running locally in under 3 minutes. 

### Prerequisites
*   Docker & Docker Compose (v2.20+)
*   Python 3.11+ (if running bare-metal)

### Quick Start Commands
```bash
# 1. Clone the repository and navigate to the project root
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Copy the environment variables template
cp .env.example .env

# 3. Spin up the containers using Docker Compose
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec web alembic upgrade head
```

Access the interactive API documentation at `http://localhost:8000/docs`.

### Architectural Syntax & Module Mapping

| Layer / Component | Technology Stack | Primary Responsibility | File Location |
| :--- | :--- | :--- | :--- |
| **API Routing** | FastAPI / APIRouter | HTTP request handling, dependency injection, status codes | `app/api/v1/endpoints/` |
| **Data Validation** | Pydantic v2 | Payload serialization, deserialization, and strict typing | `app/schemas/` |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Object-relational mapping, async sessions, connection pooling | `app/models/` |
| **Migrations** | Alembic | Database schema version control and migration scripts | `alembic/versions/` |
| **Authentication** | python-jose & passlib | JWT creation, verification, and cryptographic password hashing | `app/core/security.py` |
| **Configuration** | Pydantic-Settings | Environment variable loading with runtime validation | `app/core/config.py` |

---

## 3. Production Code Patterns & Architecture Examples

Here is the clean, copy-paste ready code implementing a modular, production-grade FastAPI service.

### A. Application Factory & Configuration (`app/core/config.py`)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MicroCorp Enterprise API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

settings = Settings()
```

### B. Async Database Session Manager (`app/db/session.py`)
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=False, 
    future=True, 
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
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

### C. JWT Security & Auth Dependency (`app/core/security.py` & `app/api/deps.py`)
```python
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Annotated[AsyncSession, Depends(get_db)]
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
    except JWTError:
        raise credentials_exception
    
    user = await db.get(User, int(user_id))
    if user is None:
        raise credentials_exception
    return user
```

### D. Multi-Stage Dockerfile (`Dockerfile`)
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

### E. Production Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: fastapi_app
    restart: always
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=production_db
      - SECRET_KEY=supersecretkeychangemeinproduction
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    container_name: postgres_db
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgrespassword
      - POSTGRES_DB=production_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d production_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1.  **Blocking I/O in Async Paths:** Using synchronous libraries (like standard `requests` or synchronous database drivers) inside `async def` route handlers blocks the event loop entirely. Use `httpx` for async HTTP requests and `asyncpg` for PostgreSQL.
2.  **Hardcoding Secret Keys:** Never commit production JWT secrets or database passwords into version control. Always utilize Pydantic-Settings (`BaseSettings`) paired with environmental injection.
3.  **Catching Generic Exceptions:** Avoid bare `except:` clauses in endpoints. Catch explicit database or validation exceptions so clients receive structured, informative HTTP 4xx/5xx responses rather than silent failures.
4.  **Mismanaging Session Lifecycle:** Forgetting to close database sessions leads to connection pool exhaustion under load. Always rely on FastAPI's dependency injection `yield` pattern with context managers to guarantee cleanup.

---

## 5. Performance & Optimization Tips

*   **Uvicorn Worker Scaling:** In production environments, run Uvicorn behind a process manager or configure multiple workers using Gunicorn as the process manager:
    ```bash
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    ```
*   **Connection Pooling Tuning:** Adjust SQLAlchemy's pool size parameters (`pool_size`, `max_overflow`) based on your database tier and concurrent request expectations.
*   **Response Caching:** Implement Redis caching layers for heavy read-endpoints that rarely change to bypass database round-trips entirely.

---

## 6. Commercial License & Attribution Summary

### **Commercial Client Delivery License**
*   **Grant:** By purchasing or downloading this boilerplate via MicroCorp AI, you are granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and resell this codebase as part of commercial client deliverables (e.g., Fiverr, Upwork, agency contracts).
*   **Restrictions:** You may **not** repackage, resell, or redistribute this codebase as a standalone template, boilerplate product, or open-source starter kit on marketplaces (e.g., GitHub, Gumroad, ThemeForest) without explicit written authorization from MicroCorp AI.
*   **Warranty:** Provided "as is", without warranty of any kind, express or implied. MicroCorp AI accepts no liability for direct or indirect damages resulting from the deployment of this code.