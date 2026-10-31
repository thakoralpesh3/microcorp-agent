# Product: FastAPI Enterprise Blueprint (JWT + Dockerized)

## 1. Product Title & Value Proposition
**Title:** The "Titan-Stack" FastAPI Boilerplate  
**Value Proposition:** Stop spending days configuring boilerplate. This turnkey architecture provides a hardened, production-ready FastAPI foundation featuring industry-standard JWT authentication, SQLAlchemy 2.0 async ORM, and a containerized deployment strategy. Designed to take your backend from "localhost" to "Production" in minutes, not hours.

---

## 2. Quick Start & Core Concepts

| Component | Technology | Why it's chosen |
| :--- | :--- | :--- |
| **API Framework** | FastAPI | High-performance, async-native, auto-docs. |
| **Authentication** | PyJWT | Standardized, stateless, secure claims. |
| **Database** | PostgreSQL + Asyncpg | Robust ACID compliance with non-blocking I/O. |
| **Container** | Docker + Alpine | Minimal attack surface, rapid deployments. |
| **Environment** | Pydantic Settings | Type-safe configuration management. |

---

## 3. Production Code Patterns & Architecture

### A. The JWT Security Dependency (`security.py`)
This snippet secures your endpoints using standard OAuth2 Bearer tokens.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return {"user_id": user_id}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")
```

### B. Dockerfile (Optimized for Multi-Stage Build)
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking I/O:** Using standard `requests` or `time.sleep()` in FastAPI `async def` routes. **Fix:** Use `httpx` and `asyncio.sleep()`.
*   **Hardcoded Secrets:** Storing API keys in your `.py` files. **Fix:** Always use a `.env` file handled by `pydantic-settings`.
*   **The "N+1" Query Problem:** Fetching related database objects inside a loop. **Fix:** Use `selectinload` or `joinedload` from SQLAlchemy to fetch relations in a single query.
*   **Ignoring Token Expiry:** Not setting an `exp` claim in your JWT. **Fix:** Always include `exp` and `iat` (issued at) to limit the damage if a token is intercepted.

---

## 5. Performance & Optimization Tips

1.  **Gunicorn + Uvicorn Workers:** Never use raw Uvicorn for production. Use Gunicorn as a process manager to fork multiple worker processes based on your CPU cores:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
2.  **Connection Pooling:** Ensure your SQLAlchemy engine is configured with a pool size appropriate for your DB tier (e.g., `pool_size=20, max_overflow=10`).
3.  **Dependency Injection Caching:** Use `lru_cache` for database session functions to prevent redundant object instantiation across requests.
4.  **Response Model Validation:** Always define a `response_model` in your decorators. It speeds up serialization by explicitly telling FastAPI what to include/exclude.

---

## 6. Commercial License & Attribution Summary

**License:** MIT License (Attribution required)
*   **Usage:** This codebase may be used for personal, educational, and commercial client projects. 
*   **Restriction:** You may not redistribute the boilerplate as a standalone competitive product.
*   **Support:** This is provided "as-is". The Agency recommends periodic security audits of the `requirements.txt` via `pip-audit`.

---
*Engineering Note: Keep your dependencies updated. Run `pip list --outdated` weekly to ensure no critical CVEs are lurking in your production stack.*