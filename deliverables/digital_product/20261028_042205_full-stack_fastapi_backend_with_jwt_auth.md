# Product Title: FastAuth Pro – The Turnkey FastAPI Production Scaffold

**Value Proposition:** Stop spending 20+ hours configuring JWT middleware, database connection pools, and container orchestration. This turnkey scaffold provides a production-ready, security-hardened FastAPI boilerplate that is battle-tested for high-concurrency environments. Perfect for SaaS founders and enterprise freelancers.

---

## 2. Quick Start & Core Concepts

This boilerplate uses a **Dependency Injection** pattern, ensuring your codebase remains testable and modular.

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Framework** | FastAPI | Async API performance |
| **Auth** | OAuth2 + JWT | Stateless session management |
| **Database** | SQLAlchemy 2.0 | Async ORM mappings |
| **Container** | Docker + Alpine | Lightweight deployment |
| **Validation** | Pydantic v2 | Strict schema enforcement |

**Installation:**
```bash
git clone https://your-repo-link.git
cp .env.example .env
docker-compose up --build
```

---

## 3. Production Code Patterns & Architecture

### A. JWT Security Dependency
Place this in `core/security.py` to handle token validation globally.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None: raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user_id
```

### B. Dockerfile (Optimized Multi-Stage)
Keep your images under 150MB by utilizing multi-stage builds.

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking Operations in Async Routes:** Avoid `time.sleep()` or standard `requests` calls inside `async def` functions. Use `anyio` or `httpx` to prevent blocking the event loop.
*   **Hardcoded Secrets:** Never store `.env` files in git. Always use environment variables or a Secret Manager (AWS Secrets Manager/HashiCorp Vault).
*   **Global DB Sessions:** Never share a single `db_session` globally. Use a `Depends(get_db)` generator to ensure sessions are closed after every request.
*   **Over-fetching:** Avoid `SELECT *`. Always use Pydantic models to define exactly which database fields are returned to the client.

---

## 5. Performance & Optimization Tips

1.  **Connection Pooling:** Configure SQLAlchemy's `AsyncEngine` with `pool_size=20` and `max_overflow=10` to prevent database exhaustion.
2.  **Gunicorn Workers:** For production, use `gunicorn` with `uvicorn.workers.UvicornWorker` to manage process lifecycle and prevent memory leaks.
3.  **Redis Caching:** Implement `@cache` decorators on your heavy read-only endpoints (GET requests) to reduce DB load by up to 80%.
4.  **Schema Caching:** Use `orjson` (FastAPI supports this natively) to speed up JSON serialization/deserialization by 5-10x compared to standard library JSON.

---

## 6. Commercial License & Attribution Summary

**License: Proprietary Commercial Use**
*   **Grant:** This code is licensed to the buyer for use in unlimited personal or commercial projects.
*   **Restrictions:** You may not redistribute, resell, or sub-license this boilerplate as a standalone product.
*   **Attribution:** No attribution required in your final production application, though standard engineering ethics apply.
*   **Support:** Provided "as-is". For custom architectural integration or security auditing, reach out to **The Agency Engineering Division**.

---
*Built for scale. Designed for performance. 🏗️*