# Full-Stack FastAPI Backend with JWT Auth and Docker Setup
*The Agency Engineering Division | Turnkey Solution Architecture*

---

## 1. # Product Title & Value Proposition

### **FastAPI Enterprise Boilerplate: Production-Ready JWT Auth & Dockerized PostgreSQL Architecture**

#### **Value Proposition**
Building secure, scalable, and production-ready APIs from scratch costs dozens of engineering hours. This turnkey backend solution provides a battle-tested, asynchronous FastAPI foundation complete with secure JSON Web Token (JWT) authentication, role-based access control, SQLAlchemy 2.0 async ORM, Alembic database migrations, and a fully orchestrated Docker Compose environment. 

Designed for high-throughput microservices and rapid client delivery, this architecture eliminates boilerplate configuration debt, ensuring your engineering team ships secure, maintainable endpoints on day one.

#### **Key Deliverables**
* **Async-First Performance:** Built on Uvicorn and FastAPI utilizing Python 3.11+ `async/await` paradigms.
* **Cryptographic Security:** Stateless authentication via RS256/HS256 JWTs, secure password hashing using bcrypt, and HTTP-only cookie strategies.
* **Database Agnostic Migrations:** Fully configured Alembic migration pipeline integrated with asynchronous PostgreSQL drivers (`asyncpg`).
* **Containerized Development & Deployment:** Multi-stage Dockerfiles and optimized Docker Compose configurations for instant local setup and production parity.

---

## 2. ## Quick Start & Core Concepts

### **Core Stack Architecture**

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Web Framework** | FastAPI (0.110+) | High-performance asynchronous API routing, validation, and auto-docs. |
| **ASGI Server** | Uvicorn | Lightning-fast async server implementation. |
| **Database ORM** | SQLAlchemy 2.0 (Async) | Type-safe database interactions using modern Python typing. |
| **Migrations** | Alembic | Version control for database schema changes. |
| **Authentication** | PyJWT & Passlib | Token generation, validation, and cryptographic password hashing. |
| **Containerization** | Docker & Compose | Isolated, reproducible development and production runtimes. |

### **5-Minute Quick Start**

Clone the repository, configure your environment variables, and spin up the entire stack using Docker Compose:

```bash
# 1. Clone and navigate to the project root
git clone https://github.com/microcorp-ai/fastapi-jwt-docker-boilerplate.git
cd fastapi-jwt-docker-boilerplate

# 2. Configure environment variables
cp .env.example .env

# 3. Spin up PostgreSQL and the FastAPI application containers
docker compose up --build -d

# 4. Run database migrations inside the container
docker compose exec api alembic upgrade head

# 5. Verify service health
curl -X GET "http://localhost:8000/health"
```

---

## 3. ## Production Code Patterns & Architecture Examples

### **Project Directory Structure**
```text
app/
├── alembic/                 # Database migrations
├── core/                    # App configuration, security, database session
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/                  # SQLAlchemy ORM models
│   └── user.py
├── schemas/                 # Pydantic data validation schemas
│   └── user.py
├── api/                     # API Route controllers
│   ├── v1/
│   │   ├── api.py
│   │   └── endpoints/
│   │       ├── auth.py
│   │       └── users.py
│   └── deps.py              # Dependency injection (Auth, DB Session)
├── main.hpp                 # Application entry point
├── Dockerfile
└── docker-compose.yml
```

---

### **1. Configuration Management (`app/core/config.py`)**
Using `pydantic-settings` to guarantee environment variable safety and strict typing at startup.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Enterprise Backend"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

---

### **2. Asynchronous Database Session (`app/core/database.py`)**
Configuring SQLAlchemy 2.0 with an async session factory.

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

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

### **3. Cryptographic Security & JWT Management (`app/core/security.py`)**
Handles token creation, expiration management, and secure password hashing.

```python
from datetime import datetime, timedelta, timezone
import jwt
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
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
```

---

### **4. Authentication Dependencies (`app/api/deps.py`)**
Secures endpoints by parsing bearer tokens and resolving the current database user.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
        
    result = await db.execute(select(User).filter(User.id == int(user_id)))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user
```

---

### **5. API Router & Endpoints (`app/api/v1/endpoints/auth.py`)**
Token generation and user authentication endpoint.

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
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Incorrect email or password"
        )
    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
```

---

### **6. Docker Orchestration (`docker-compose.yml`)**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: postgres_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: securepassword123
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
    container_name: fastapi_backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=securepassword123
      - POSTGRES_DB=enterprise_db
      - JWT_SECRET_KEY=super_secret_jwt_key_change_in_production
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

* **❌ Anti-Pattern:** Using synchronous database drivers (`psycopg2`) with asynchronous FastAPI route handlers.
  * **✅ Correct Approach:** Always leverage asynchronous database drivers (`asyncpg`) and SQLAlchemy's `AsyncSession` to prevent thread-pool starvation under concurrent load.
* **❌ Anti-Pattern:** Hardcoding configuration variables directly inside application files.
  * **✅ Correct Approach:** Centralize configuration using `pydantic-settings` to enforce type safety, validate environment parameters upon application startup, and avoid runtime `KeyError` exceptions.
* **❌ Anti-Pattern:** Committing unencrypted passwords or raw JWT secrets into version control.
  * **✅ Correct Approach:** Maintain strict separation of environment settings via `.env` files (excluded via `.gitignore`) and use secret managers (AWS Secrets Manager, Doppler, Vault) in production deployments.
* **❌ Anti-Pattern:** Forgetting to handle database session teardowns during unexpected exceptions, leading to unclosed client connections and connection pool exhaustion.
  * **✅ Correct Approach:** Utilize robust dependency injection generators with `try/finally` blocks ensuring session closures (`await session.close()`) on every request lifecycle.

---

## 5. ## Performance & Optimization Tips

1. **Uvicorn Worker Scaling:** In production environments behind reverse proxies (like Nginx), scale Uvicorn workers based on available CPU cores using the Gunicorn process manager:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
2. **Connection Pooling Tuning:** Fine-tune database connection pool limits inside `create_async_engine` to handle high concurrency without overwhelming the PostgreSQL instance:
   ```python
   engine = create_async_engine(
       settings.DATABASE_URL,
       pool_size=20,
       max_overflow=10,
       pool_timeout=30,
   )
   ```
3. **Response Compression:** Integrate Starlette's `GZipMiddleware` to reduce network payload sizes for large JSON responses:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

---

## 6. ## Commercial License & Attribution Summary

* **Product Identification:** Full-Stack FastAPI Backend with JWT Auth and Docker Setup (MicroCorp AI Turnkey Solutions)
* **License Grant:** Purchased under the **MicroCorp AI Commercial Engineering License**. You are granted a worldwide, non-exclusive, perpetual license to modify, deploy, and distribute this codebase within internal and client-facing commercial applications.
* **Restrictions:** Reselling or redistributing this raw boilerplate as a standalone template, library, or digital product on marketplaces (Gumroad, GitHub Sponsors, Envato, etc.) is strictly prohibited.
* **Warranty Disclaimer:** Provided *as is*, without warranty of any kind, express or implied. The Agency Engineering Division disclaims all liability for direct or indirect damages resulting from the deployment of this architecture.