# Product: FastAPI Enterprise Blueprint (JWT + Dockerized)

## 1. Product Title & Value Proposition
**Title:** The "TitanStack" FastAPI Boilerplate: Production-Ready JWT Auth & Dockerized Architecture.

**Value Proposition:** Stop spending 20+ hours configuring security middleware, database dependency injection, and container orchestration. This turnkey solution provides a scalable, production-hardened foundation for FastAPI applications. It is designed for developers who need to ship a secure, performant backend to production in record time.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation | Benefit |
| :--- | :--- | :--- |
| **Auth** | OAuth2 + JWT (RS256) | Industry standard, stateless scalability. |
| **Container** | Multi-stage Dockerfile | Minimal image size, optimized CI/CD. |
| **Database** | SQLAlchemy 2.0 (Async) | Non-blocking I/O for high throughput. |
| **Validation** | Pydantic v2 | Type-safe data contracts at runtime. |

**Quick Setup Command:**
```bash
# Clone the repository and boot the stack
git clone <repo-url> && cd titanstack
docker-compose up --build
```

---

## 3. Production Code Patterns & Architecture

### A. The Dependency Injection Pattern
This pattern ensures database sessions are correctly closed, even if requests fail.

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@db:5432/main")
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### B. JWT Authentication Middleware
Ensure security by enforcing authentication at the route level.

```python
# app/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_jwt(token) # Custom utility
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return payload
```

---

## 4. Common Anti-Patterns & Gotchas

*   **The "Fat" Dependency:** Avoid putting heavy business logic inside dependency functions. Keep `Depends()` limited to Auth, DB, and Settings.
*   **Sync Calls in Async Context:** Using `requests` or blocking DB drivers inside an async route will stall the entire Event Loop. **Always use `httpx` or `asyncpg`.**
*   **Hardcoded Secrets:** Never bake `.env` files into Docker images. Use Docker Secrets or environment variable injection at runtime.
*   **CORS Bloat:** Avoid `allow_origins=["*"]` in production. Explicitly whitelist your frontend domain.

---

## 5. Performance & Optimization Tips

1.  **Uvicorn/Gunicorn Combo:** In production, run with Gunicorn using Uvicorn workers:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
2.  **Schema Projection:** Use Pydantic `exclude_unset=True` and `response_model_exclude_none=True` to minimize JSON payload sizes.
3.  **Connection Pooling:** Always define `pool_size` and `max_overflow` in your engine configuration to prevent DB connection exhaustion under heavy load.
4.  **Redis Caching:** Offload frequent read-only queries (e.g., config data, global stats) to Redis.

---

## 6. Commercial License & Attribution Summary

*   **License:** Proprietary Commercial License (Licensed to the purchaser for use in unlimited commercial projects).
*   **Permitted Use:** You may modify, white-label, and deploy this code for your clients.
*   **Prohibited Use:** You may *not* redistribute the source code as a standalone boilerplate or educational product without explicit written consent from MicroCorp AI.
*   **Attribution:** No attribution is required in the end product.

---
*Architect’s Note: This boilerplate is built to scale. As you transition from MVP to Enterprise, ensure you monitor the `FastAPI` request-time metrics using Prometheus.*

**[Download Source Code Bundle]** | **[View Documentation Wiki]**