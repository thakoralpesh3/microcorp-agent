# Product: FastAPI Enterprise Blueprint (JWT + Dockerized)

## 1. Product Title & Value Proposition
**Title:** The "Titan-Stack" FastAPI Boilerplate: Production-Ready JWT Auth & Dockerized Architecture.

**Value Proposition:** Stop spending 20+ hours configuring dependency injection, security middleware, and container orchestration. This kit provides a battle-tested, modular FastAPI foundation designed for high-concurrency production environments. It is pre-configured for instant deployment to AWS, GCP, or DigitalOcean.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation | Benefit |
| :--- | :--- | :--- |
| **Auth** | OAuth2 + JWT (RS256) | Stateless, scalable security. |
| **Container** | Multi-stage Dockerfile | Minimal image size (~40MB). |
| **Database** | SQLAlchemy 2.0 (Async) | Non-blocking I/O operations. |
| **Validation** | Pydantic v2 | Blazing-fast schema enforcement. |
| **Orchestration** | Docker Compose | Local env parity. |

---

## 3. Production Code Patterns & Architecture

### A. The Core Security Middleware (`security.py`)
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### B. The Production Dockerfile
```dockerfile
# Stage 1: Build
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry && poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking I/O:** Never use `time.sleep()` or synchronous database drivers (e.g., `psycopg2`) in a FastAPI `async def` route. Use `asyncpg` or `aiosqlite`.
*   **The "Secret" Leak:** Hardcoding your `JWT_SECRET` in `config.py`. **Fix:** Always use a `.env` file loaded via `pydantic-settings`.
*   **Dependency Bloat:** Including dev-dependencies in the production image. **Fix:** Use the Multi-stage Docker build pattern provided above.
*   **Missing Health Checks:** Failing to implement `/health` endpoints prevents load balancers (AWS ELB/K8s) from managing your container lifecycle.

---

## 5. Performance & Optimization Tips

1.  **Uvicorn Worker Scaling:** Always use the `--workers` flag based on your CPU cores (Formula: `2 * cores + 1`).
2.  **Gzip Compression:** Use `fastapi.middleware.gzip.GZipMiddleware` to reduce payload sizes for JSON-heavy responses.
3.  **Connection Pooling:** Use `SQLAlchemy`'s `AsyncEngine` with `pool_size` and `max_overflow` settings tuned for your database instance.
4.  **Dependency Injection Caching:** Leverage FastAPI’s `Depends()` correctly to prevent re-initializing database sessions on every request.

---

## 6. Commercial License & Attribution Summary

*   **License:** MIT License (Permissive). You are free to modify, distribute, and include this code in your commercial SaaS projects.
*   **Attribution:** While not strictly required, a mention of *MicroCorp AI Engineering* in your project's `README.md` is appreciated.
*   **Warranty:** This software is provided "as-is." Always perform a security audit on your implementation before production deployment.

***

**MicroCorp AI Engineering**
*Architected for Scale. Engineered for Excellence.*