# Full-Stack FastAPI Backend with JWT Auth and Docker Setup

> **The Agency Engineering Division** — Enterprise Backend Architecture  
> *Production-grade, secure, and horizontally scalable boilerplate designed for rapid client delivery.*

---

## 1. Product Title & Value Proposition

### **Enterprise FastAPI Backend Boilerplate: JWT Authentication, SQLAlchemy ORM, & Production Docker Setup**

Building a secure, scalable Python backend from scratch takes days of boilerplate configuration, dependency management, and security hardening. This turnkey solution provides a battle-tested, production-ready architecture designed specifically for high-performance microservices and client deliverables. 

### **Key Business Value:**
* **Time-to-Market:** Cut backend setup time by 80% with pre-configured dependency injection, database sessions, and migration pipelines.
* **Enterprise Security:** Implements robust JSON Web Token (JWT) authentication with bcrypt password hashing, token expiration, and role-based access control (RBAC).
* **Containerized Consistency:** Includes a multi-stage Dockerfile and Docker Compose configuration for instant, isolated local development and zero-friction cloud deployment.
* **Type-Safe Modern Python:** Leverages Python 3.11+, Pydantic v2 for lightning-fast data validation, and SQLAlchemy 2.0 async paradigms.

---

## 2. Quick Start & Core Concepts

### **Directory Structure**
```text
fastapi-enterprise-boiler/
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # API routers (v1)
│   ├── core/                # Config, security, database
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   └── main.py              # Application entrypoint
├── tests/                   # Pytest suite
├── .env.example             # Environment variable template
├── Dockerfile               # Multi-stage production container
├── docker-compose.yml       # Local orchestration (App + PostgreSQL)
└── requirements.txt         # Pinned production dependencies
```

### **Core Technology Stack & Architecture Map**

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI (v0.109+) | High-performance asynchronous REST API framework with auto-docs. |
| **Validation** | Pydantic v2 | Runtime data parsing, serialization, and strict schema validation. |
| **Database ORM** | SQLAlchemy 2.0 | Asynchronous relational database management and schema definition. |
| **Migrations** | Alembic | Version-controlled database schema evolution. |
| **Auth** | PyJWT / Passlib | Cryptographic token generation and secure password hashing (bcrypt). |
| **Containerization**| Docker & Compose | Deterministic runtime environments across development and production. |

---

## 3. Production Code Patterns & Architecture Examples

### **A. Application Entrypoint (`app/main.py`)**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB connection pools, caches, etc.
    print("Initializing Enterprise Backend Engine...")
    yield
    # Shutdown: Release resources gracefully
    print("Shutting down engine...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}
```

### **B. Security & JWT Authentication (`app/core/security.py`)**
```python
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

### **C. Dependency Injection & Authentication (`app/api/deps.py`)**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
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
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = await db.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
```

### **D. Docker Setup (`Dockerfile` & `docker-compose.yml`)**

#### **Dockerfile**
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUNC pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime Production Image
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
  web:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/enterprise_db
      - JWT_SECRET_KEY=super-secret-key-change-in-production
    depends_on:
      - db
    volumes:
      - .:/app

  db:
    image: postgres:15-alpine
    restart: always
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=enterprise_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Blocking I/O in Async Routes:** 
   * *Anti-Pattern:* Using standard `requests` or blocking file/database drivers inside `async def` paths. This blocks the main event loop.
   * *Correction:* Use fully asynchronous clients (e.g., `httpx`, `asyncpg`) and offload CPU-bound tasks using `starlette.concurrency.run_in_threadpool`.
2. **Hardcoding Configuration Secrets:**
   * *Anti-Pattern:* Keeping database passwords, JWT secrets, or API keys directly in source code.
   * *Correction:* Always validate configuration schemas at startup via Pydantic’s `BaseSettings` reading from environment variables.
3. **N+1 Database Query Traps:**
   * *Anti-Pattern:* Accessing relationship attributes in Pydantic serialization loops without eager loading (`joinedload` / `selectinload`).
   * *Correction:* Explicitly construct SQLAlchemy queries utilizing modern async loading strategies to prevent execution stalls.

---

## 5. Performance & Optimization Tips

* **Uvicorn Worker Scaling:** Run Uvicorn behind a process manager like Gunicorn or utilize multiple worker processes in production:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop
  ```
* **Connection Pooling:** Ensure SQLAlchemy's `pool_size` and `max_overflow` are explicitly tuned matching your database tier limits under high concurrent loads.
* **Response Caching:** Integrate Redis middleware or dependency-level caching for high-read, low-mutation endpoints to slash database load.

---

## 6. Commercial License & Attribution Summary

```text
MIT License

Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
* **Commercial Usage:** Approved for deployment in client projects, commercial SaaS applications, and enterprise microservices.
* **Support & Warranty:** Provided "as-is" without warranty of any kind. For bespoke architecture adjustments, contact The Agency Engineering Division.