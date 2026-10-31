# Product Title: FastAuth Pro – The Scalable FastAPI Boilerplate

### Value Proposition
Stop wasting 20+ hours configuring dependency injection, JWT lifecycle management, and Docker orchestration. **FastAuth Pro** is a production-ready, enterprise-grade architecture for FastAPI. It features pre-configured OAuth2/JWT workflows, modular project structure, and containerization that is ready for AWS ECS, Google Cloud Run, or DigitalOcean App Platform deployment.

---

## 1. Quick Start & Core Concepts

This boilerplate follows the **Modular Service Pattern**.

| Feature | Technology | Why it’s used |
| :--- | :--- | :--- |
| **Framework** | FastAPI | High-performance async request handling |
| **Auth** | PyJWT | Standardized, stateless security |
| **Database** | SQLAlchemy 2.0 + AsyncPG | Type-safe asynchronous ORM |
| **Container** | Docker + Multi-stage | Minimized image sizes for faster CI/CD |
| **Validation** | Pydantic v2 | Strict request/response modeling |

### Quick Start Guide
```bash
# Clone the repository
git clone https://github.com/microcorp-ai/fastauth-pro
cd fastauth-pro

# Spin up environment
docker-compose up --build
```

---

## 2. Production Code Patterns

### JWT Token Factory (`core/security.py`)
Centralized logic for token generation and lifecycle.

```python
from datetime import datetime, timedelta
from jose import jwt

SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### Dependency Injection Pattern (`api/deps.py`)
Inject `get_current_user` into endpoints to enforce authentication globally.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": payload.get("sub")}
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

### Multi-Stage Dockerfile
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install poetry && poetry export -f requirements.txt > requirements.txt

# Stage 2: Final
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 3. Common Anti-Patterns & Gotchas

*   **Blocking I/O:** Never use `time.sleep()` or standard `requests` in your routes. Always use `asyncio.sleep()` or `httpx`. Blocking the event loop kills FastAPI performance.
*   **Hardcoded Secrets:** Never commit `.env` files. Use `pydantic-settings` to load configuration from environment variables.
*   **Broad Exceptions:** Don't use `except Exception:`. Catch specific database/validation errors to avoid leaking system internals in response headers.
*   **Dependency Bloat:** Only include production dependencies in the base image. Use Docker multi-stage builds to exclude development tools (like `black` or `pytest`).

---

## 4. Performance & Optimization Tips

1.  **Gunicorn Workers:** For production, use `Gunicorn` with `UvicornWorker` to manage multiple workers. This prevents the event loop from bottlenecking on high-concurrency requests.
2.  **Connection Pooling:** Configure SQLAlchemy's `AsyncSession` with a connection pool (`pool_size=20`, `max_overflow=10`).
3.  **Caching:** Implement `Redis` for frequent read-only operations (e.g., getting user profile metadata).
4.  **Compression:** Enable GZip middleware in FastAPI to reduce payload size for mobile clients.

---

## 5. Commercial License & Attribution Summary

**License:** MIT License (Commercial Friendly).
**Usage Rights:** You are permitted to use this boilerplate for your Fiverr clients, agency internal projects, or freelance deliverables.
**Attribution:** MicroCorp AI retains the right to be credited as the structural architect in the `README.md` of any delivered project. 

*Need custom modifications or CI/CD pipelines for this stack? Contact the MicroCorp Engineering Division for enterprise support.*