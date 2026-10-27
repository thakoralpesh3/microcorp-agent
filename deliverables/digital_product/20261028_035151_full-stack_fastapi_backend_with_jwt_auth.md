# Product: NexusFastAPI – The Enterprise Blueprint

## 1. Product Title & Value Proposition
**Title:** NexusFastAPI: Production-Ready Auth & Dockerized Boilerplate
**Value Proposition:** Stop spending 20+ hours configuring JWT security flows, dependency injection, and container orchestration. NexusFastAPI provides a battle-tested, modular architecture designed for high-concurrency SaaS backends. This is a "Copy-Paste-Deploy" solution built for engineers who value type safety and rapid time-to-market.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation Strategy | Benefit |
| :--- | :--- | :--- |
| **Auth** | OAuth2 + JWT (RS256) | Stateless, scalable, industry standard. |
| **Data** | SQLAlchemy 2.0 (Async) | Non-blocking database I/O. |
| **Validation** | Pydantic v2 | High-performance schema enforcement. |
| **Container** | Multi-stage Dockerfile | Minimized image footprint (security). |
| **Orchestration** | Docker Compose | Local dev environments in seconds. |

**Quick Start:**
1. Clone the repo: `git clone nexus-fastapi-template .`
2. Configure `.env`: `cp .env.example .env`
3. Spin up infrastructure: `docker-compose up --build`

---

## 3. Production Code Patterns & Architecture

### A. JWT Security Dependency
Use this pattern to protect routes via FastAPI's `Depends`.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise HTTPException(status_code=401)
        return {"user_id": user_id}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### B. Multi-Stage Dockerfile (Optimization)
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install poetry
COPY pyproject.toml .
RUN poetry export -f requirements.txt > requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking I/O in Async Routes:** Never use `time.sleep()` or synchronous database drivers (e.g., standard `psycopg2`) inside `async def`. Use `asyncpg`.
*   **Hardcoded Secrets:** Never commit `.env` files. Use environment variable injection exclusively via Pydantic Settings.
*   **Flat Architecture:** Avoid a single `main.py` file. Use the **Domain-Driven Directory** structure:
    *   `/app/api` (Routes)
    *   `/app/core` (Security/Config)
    *   `/app/models` (DB Schemas)
    *   `/app/services` (Business logic)

---

## 5. Performance & Optimization Tips

1.  **Gunicorn Workers:** In production, use `gunicorn` with `uvicorn` workers:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
2.  **Connection Pooling:** Always use `AsyncSession` with a pooled engine to avoid the overhead of opening new connections per request.
3.  **Schema Filtering:** Utilize Pydantic’s `response_model_exclude_unset=True` to reduce JSON payload sizes sent to clients.
4.  **Caching:** Implement `Redis` for JWT blacklisting and expensive read operations.

---

## 6. Commercial License & Attribution Summary

*   **License:** MIT License. You are free to modify, distribute, and sell this code within your own commercial projects.
*   **Attribution:** While not strictly required, attribution to *MicroCorp AI Engineering* is encouraged for enterprise support reference.
*   **Warranty:** This boilerplate is provided "as-is." Always perform a security audit (e.g., `bandit`) before deploying to production environments.

***

**Need custom implementation help?** Reach out to the MicroCorp Architecture team via the private Slack channel provided in your purchase confirmation.