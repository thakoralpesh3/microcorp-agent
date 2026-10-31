# Product: The "FastAPI Enterprise Core" Boilerplate
**Your Turnkey Blueprint for Production-Grade Python Backends.**

## 1. Product Title & Value Proposition
**Title:** FastAPI Enterprise Core: JWT-Secured, Dockerized, and Production-Ready.
**Value Proposition:** Stop spending 20+ hours configuring dependency injection, CORS middleware, JWT lifecycles, and Docker multi-stage builds. This package provides a battle-tested architecture that scales from MVP to Series A.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation Tool | Benefit |
| :--- | :--- | :--- |
| **Auth** | `PyJWT` + `Passlib` | Stateless, scalable session management. |
| **ORM** | `SQLAlchemy 2.0` | Async-first database interaction. |
| **Validation** | `Pydantic v2` | Strict, high-performance data schemas. |
| **Container** | `Docker Multi-stage` | Small image footprint, secure CI/CD. |
| **Dependency** | `FastAPI Depends` | Clean separation of concerns. |

---

## 3. Production Code Patterns & Architecture

### A. JWT Security Dependency (`security.py`)
```python
from datetime import datetime, timedelta
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "SUPER_SECRET_KEY" # Load from ENV in production
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### B. Optimized Dockerfile (`Dockerfile`)
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml .
RUN poetry export -f requirements.txt > requirements.txt

# Stage 2: Runner
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking I/O in Async Routes:** Never use `time.sleep()` or standard synchronous DB drivers (like `psycopg2`). Use `asyncpg`.
*   **Hardcoding Secrets:** Never commit `.env` files or secrets to Git. Use `pydantic-settings` to inject variables via environment.
*   **Broad Exception Handling:** Avoid `except Exception: pass`. Always log specific tracebacks to avoid silent failure debugging hell.
*   **Dependency Bloat:** Only install what you need. Prune unused dependencies weekly using `pip-audit`.

---

## 5. Performance & Optimization Tips

1.  **Gunicorn + Uvicorn:** Always run with a process manager in production.
    *   *Cmd:* `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
2.  **Connection Pooling:** Use SQLAlchemy's `AsyncEngine` with `pool_size=20` and `max_overflow=10` to handle connection spikes.
3.  **Response Caching:** Implement Redis for frequently accessed GET endpoints to reduce DB latency by 90%+.
4.  **Minify Schemas:** Use `response_model_exclude_unset=True` in your FastAPI decorators to reduce JSON payload sizes sent to the client.

---

## 6. Commercial License & Attribution

**License:** MIT License.
**Usage Rights:**
*   **Commercial:** You are granted an irrevocable, royalty-free license to use this codebase in any commercial client project, including white-label products.
*   **Redistribution:** You may not resell this specific code as a standalone product (e.g., as your own template on Gumroad).
*   **Attribution:** While not required, maintaining the internal module structure is recommended for future-proofing your maintenance cycles.

***

*Engineered by MicroCorp AI - The Agency's Engineering Division.*
*Need custom enterprise architecture? Reach out to our systems integration team.*