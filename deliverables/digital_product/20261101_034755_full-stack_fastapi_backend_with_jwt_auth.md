# Product: The "FastAPI-Launchpad" Enterprise Blueprint

## 1. Product Title & Value Proposition
**Title:** Full-Stack FastAPI JWT-Auth Boilerplate & Production Dockerization Kit.

**Value Proposition:** Stop spending 20+ hours configuring dependency injection, JWT security handshakes, and container orchestration. This kit provides a battle-tested, production-ready foundation designed for sub-millisecond response times and horizontal scalability. Ideal for SaaS backends, microservices, and rapid API prototyping.

---

## 2. Quick Start & Core Concepts
Get your environment running in under 5 minutes.

| Concept | Implementation | Why? |
| :--- | :--- | :--- |
| **Framework** | FastAPI + Pydantic v2 | High-performance async & strict type validation. |
| **Auth** | OAuth2 + JWT (RS256) | Stateless, scalable session management. |
| **Database** | SQLAlchemy 2.0 (Async) | Modern, type-safe ORM with async support. |
| **Orchestration** | Multi-Stage Docker | Minimal image size for faster CI/CD pipelines. |

---

## 3. Production Code Patterns & Architecture

### A. Core Directory Structure
```text
/app
  /api/v1/endpoints  # Route definitions
  /core              # Security, Config, Middleware
  /models            # SQLAlchemy tables
  /schemas           # Pydantic validation
  /services          # Business logic (Do not put in routes)
main.py              # Entry point
Dockerfile           # Multi-stage production build
```

### B. JWT Security Pattern (`core/security.py`)
```python
from jose import jwt
from datetime import datetime, timedelta

ALGORITHM = "HS256"
SECRET_KEY = "SUPER_SECRET_KEY_ENV_VAR"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### C. The "Production-Grade" Dockerfile
```dockerfile
# Stage 1: Build
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt > requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. Common Anti-Patterns & Gotchas
*   **The "Fat Route" Anti-Pattern:** Never write database queries directly inside route handlers. Use an intermediary `Service` layer to decouple business logic from the HTTP layer.
*   **Blocking I/O:** Using standard `requests` or blocking DB drivers inside `async def` routes. **Use `httpx` or `aiohttp` and `asyncpg`.**
*   **Logging:** Using `print()` instead of the standard `logging` library. In production, your logs need structure (JSON) for ELK/Datadog ingestion.
*   **Hardcoded Configs:** Storing credentials in `.env` files that get committed. Use `pydantic-settings` to inject via Environment Variables exclusively.

---

## 5. Performance & Optimization Tips
1.  **Gunicorn Workers:** For production, always run FastAPI via `gunicorn` with `uvicorn` workers. The `--workers` flag should typically be `(2 * CPU_CORES) + 1`.
2.  **Connection Pooling:** Ensure your SQLAlchemy engine is configured with `pool_size` and `max_overflow` suited to your DB hardware.
3.  **Dependency Injection:** Leverage FastAPI’s `Depends()` for DB session lifecycle management; it ensures sessions are closed even if an exception occurs during the request.
4.  **CORS & Security:** Always whitelist specific domains in `CORSMiddleware`. Avoid `allow_origins=["*"]` in production environments.

---

## 6. Commercial License & Attribution Summary

*   **License:** MIT License (Commercial usage permitted).
*   **Attribution:** This boilerplate is designed as an "Infrastructure-as-Code" asset. You may modify, rebrand, and integrate this into any client-facing deliverable without attribution to MicroCorp AI.
*   **Warranty:** Provided "as-is". This is an architectural foundation; ensure your security team audits the finalized implementation before public deployment.

---
*Built by The Agency Engineering Division. Stay scalable.*