# Full-Stack FastAPI Enterprise Blueprint: JWT Auth & Dockerized Scale

## 1. Product Title & Value Proposition
**Title:** The "Titan" FastAPI Boilerplate: Production-Ready Auth & Containerization  
**Value Proposition:** Eliminate 40+ hours of boilerplate setup. This kit provides a battle-tested, security-hardened FastAPI architecture featuring OAuth2/JWT authentication, PostgreSQL integration, and a production-ready Docker/Docker-Compose orchestration layer. Designed for engineers who need to ship to production *today*.

---

## 2. Quick Start & Core Concepts
Get your development environment running in under 5 minutes.

| Concept | Implementation Strategy | Why? |
| :--- | :--- | :--- |
| **Auth** | OAuth2 + JWT (Bearer) | Stateless, scalable session management. |
| **Database** | SQLAlchemy + Alembic | Schema migrations without downtime. |
| **Container** | Multi-stage Dockerfile | Minimized image size/Security. |
| **Validation** | Pydantic v2 | High-speed data parsing & coercion. |

**Quick Setup Command:**
```bash
docker-compose up --build -d
# Access Swagger UI at http://localhost:8000/docs
```

---

## 3. Production Code Patterns & Architecture
### A. The JWT Dependency Pattern (`security.py`)
Centralizing security prevents "identity leakage."

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None: raise HTTPException(status_code=401)
        return {"user_id": user_id}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Credentials")
```

### B. The Production-Grade Dockerfile
Multi-stage build to reduce attack surface and deployment size.

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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. Common Anti-Patterns & Gotchas
*   **Hardcoding Secrets:** Never store `SECRET_KEY` in `settings.py`. Use Pydantic's `BaseSettings` to load from `.env` or AWS Secrets Manager.
*   **Blocking I/O:** Using `time.sleep()` or synchronous database drivers in FastAPI endpoints. Always use `async` drivers (`asyncpg`) and `await` calls.
*   **Global Exception Handling:** Avoid putting try-except in every endpoint. Use `app.add_exception_handler` to create a standard, clean error JSON response.
*   **Ignoring Alembic:** Modifying DB tables manually in PGAdmin. Use Alembic migrations to ensure your cloud staging matches your local environment.

---

## 5. Performance & Optimization Tips
1.  **Gunicorn Workers:** In production, wrap Uvicorn with Gunicorn (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`) to manage worker lifecycle.
2.  **Connection Pooling:** Use `databases` or SQLAlchemy 2.0's `AsyncEngine` with `pool_size` set to your DB capacity.
3.  **Background Tasks:** Offload heavy CPU/Network tasks (e.g., sending emails/processing PDFs) to `FastAPI.BackgroundTasks` or Celery/Redis workers.
4.  **JSON Caching:** For high-traffic read endpoints, utilize `Redis` to cache serialized Pydantic responses.

---

## 6. Commercial License & Attribution Summary

**License: Commercial Use Enterprise License**
*   **Permitted:** You may use this codebase as the foundation for your client projects, internal tools, or SaaS products.
*   **Restrictions:** You may not redistribute, sub-license, or sell this boilerplate as your own "template" or "kit" on marketplaces (Gumroad, ThemeForest, etc.).
*   **Attribution:** "Built upon the Titan FastAPI Architecture by MicroCorp AI."
*   **Disclaimer:** This code is provided as-is. MicroCorp AI is not liable for security breaches resulting from improper configuration of deployed infrastructure.

---
*Architect's Note: Keep your `.env` files out of Git. Use a `.gitignore` immediately upon initialization.*