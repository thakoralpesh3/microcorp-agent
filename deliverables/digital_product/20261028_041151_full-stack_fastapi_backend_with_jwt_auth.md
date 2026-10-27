# Product: FastAPI Enterprise-Grade Skeleton
## Full-Stack FastAPI Backend with JWT Auth & Dockerized Lifecycle

### 1. Product Title & Value Proposition
**Title:** `FastAPI-Secure-Starter: The Production-Ready Boilerplate`

**Value Proposition:** 
Stop wasting hours on boilerplate setup. This kit provides a hardened, production-ready FastAPI foundation featuring integrated OAuth2 JWT flow, SQLModel (ORM) abstraction, and a multi-stage Dockerfile optimized for high-concurrency environments. Perfect for engineers moving from prototyping to scalable, enterprise-grade backends.

---

### 2. Quick Start & Core Concepts
Get your environment running in under 5 minutes.

| Concept | Implementation | Benefit |
| :--- | :--- | :--- |
| **Auth** | OAuth2 + JWT (HS256) | Stateless, scalable security. |
| **ORM** | SQLModel (Pydantic + SQLAlchemy) | Type-safe database interactions. |
| **Validation** | Pydantic V2 | High-performance input serialization. |
| **Deployment** | Multi-stage Docker | Minimal image footprint (distroless). |
| **Tasks** | BackgroundTasks | Offload heavy compute from main event loop. |

**Quick Commands:**
```bash
# Build the container
docker build -t fast-api-app .

# Run with environment variables
docker run -p 8000:8000 --env-file .env fast-api-app
```

---

### 3. Production Code Patterns & Architecture
#### The Auth Dependency (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "SUPER_SECRET_KEY_REPLACE_IN_PROD"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

#### The Docker Multi-Stage Build (`Dockerfile`)
```dockerfile
# Stage 1: Build
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml .
RUN poetry export -f requirements.txt > requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 4. Common Anti-Patterns & Gotchas
*   **Blocking the Event Loop:** Never use `time.sleep()` or synchronous I/O operations directly in an `async def` route. Use `run_in_threadpool` for legacy sync code.
*   **Exposing Sensitive Data:** Always use Pydantic `ResponseModel` to strip `hashed_password` or `internal_id` fields before sending JSON to the client.
*   **Hardcoded Secrets:** Never store `.env` or `config.py` secrets in version control. Use environment variables injected via GitHub Secrets or AWS Secrets Manager.
*   **Circular Imports:** Keep `models.py` (database) and `schemas.py` (Pydantic) separate to avoid cyclic dependency crashes during startup.

---

### 5. Performance & Optimization Tips
1.  **Connection Pooling:** Always configure your SQLAlchemy/SQLModel engine with `pool_size` and `max_overflow` suited to your DB hardware limits.
2.  **Gunicorn Workers:** In production, use `gunicorn` with `uvicorn.workers.UvicornWorker` to manage multiple processes (one per CPU core).
    *   `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
3.  **Redis Caching:** For compute-heavy endpoints, wrap your dependency injection logic in `FastAPI-Cache` to store responses in Redis.
4.  **Minify Schema:** Use `orjson` as a drop-in replacement for `json` to get a 2x-5x performance boost on response serialization.

---

### 6. Commercial License & Attribution Summary

**License: MIT Commercial-Ready**
*   **Usage:** You are granted a perpetual, non-exclusive license to use this codebase for personal, freelance, and commercial internal software projects.
*   **Restriction:** You may **not** resell this specific codebase as a standalone product or template on platforms like Gumroad, ThemeForest, or similar marketplaces.
*   **Attribution:** Attribution is optional but appreciated. Referencing `MicroCorp AI` in your documentation helps us maintain these industry-standard blueprints.

*This product is provided "as-is" without warranty. Ensure you rotate all placeholder keys before production deployment.*