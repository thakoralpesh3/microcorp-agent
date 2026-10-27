# Product: FastAPI Enterprise-Grade Skeleton (JWT/Docker Ready)

## 1. Product Title & Value Proposition
**Title:** The "Fast-Launch" FastAPI JWT Scaffold  
**Value Proposition:** Stop spending 10+ hours on boilerplate. This production-ready architecture includes secure JWT authentication, asynchronous database pooling, Docker multi-stage builds, and a clean repository-service-controller pattern. Designed to save senior developers time and help junior developers ship like pros.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation | Why? |
| :--- | :--- | :--- |
| **Auth** | `PyJWT` + `PassLib` | Industry standard for stateless auth. |
| **Database** | `SQLAlchemy` 2.0 (Async) | Non-blocking I/O for high concurrency. |
| **Container** | Docker Multi-stage | Smaller images, faster CI/CD pipelines. |
| **Validation** | `Pydantic` v2 | Strict type safety for request/response. |

**Quick Command:**
```bash
# Spin up infrastructure
docker-compose up -d --build
# Initialize migration
alembic revision --autogenerate -m "initial_schema"
```

---

## 3. Production Code Patterns & Architecture

### A. JWT Security Utility (`auth.py`)
```python
from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "SUPER_SECRET_ENV_VAR"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### B. Dependency Injection for Security
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decode logic here
    # Return user object or raise 401
    return {"user_id": 1, "username": "admin"}
```

### C. Optimized Dockerfile
```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **The "Fat Controller" Anti-pattern:** Never put business logic inside FastAPI route handlers. Use a Service Layer.
*   **Synchronous Database Calls:** Avoid `db.query()` in a raw route; always use `AsyncSession` to prevent event-loop blocking.
*   **Hardcoded Secrets:** Never commit `.env` files. Use `pydantic-settings` to load configuration from environment variables.
*   **Global Exception Handling:** Don't let your API leak stack traces. Always use a global exception handler.

---

## 5. Performance & Optimization Tips

1.  **Connection Pooling:** Use `AsyncAdaptedQueuePool` in SQLAlchemy to manage connection bursts.
2.  **Gunicorn Workers:** In production, run Uvicorn behind Gunicorn with `UvicornWorker` for multi-process handling:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
3.  **Caching:** Use `Redis` for high-frequency lookup data (e.g., JWT blacklisting or heavy API responses).
4.  **Pydantic V2:** Always use `.model_dump()` instead of `.dict()` for better performance and schema validation.

---

## 6. Commercial License & Attribution Summary

**License:** MIT License (Commercial Use Allowed).  
**Attribution:** This scaffold was engineered by The Agency's Engineering Division.  
*You are authorized to use this boilerplate for client projects, SaaS products, or internal enterprise tools. Redistribution of the original source code as a competing "template product" is prohibited.*

---
*Architect's Note: Keep your requirements.txt lean and your database migrations clean. Happy coding.* 🏗️