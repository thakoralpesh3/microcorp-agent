# Product: The "Solid-State" FastAPI Boilerplate
**Target:** High-Performance REST APIs with JWT Security & Docker Orchestration.

---

## 1. Product Title & Value Proposition
**Title:** *FastAPI Enterprise Blueprint: JWT Auth, PostgreSQL, and Docker-Ready.*

**Value Proposition:** Stop rewriting the auth layer and directory structure for every project. This boilerplate provides a production-hardened, modular FastAPI architecture designed to scale from MVP to enterprise-grade deployments. Save 20+ hours of setup time and avoid common security pitfalls.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation Tool | Why? |
| :--- | :--- | :--- |
| **Framework** | FastAPI | Asynchronous performance with Pydantic type safety. |
| **Auth** | PyJWT | Standardized, stateless authentication. |
| **Database** | SQLAlchemy 2.0 + AsyncPG | High-concurrency ORM performance. |
| **Validation** | Pydantic v2 | Strict schema enforcement. |
| **Container** | Docker + Alpine | Minimal footprint, consistent environment. |

**Quick Commands:**
```bash
# Initialize
docker-compose up --build

# Run migrations (Alembic)
docker-compose exec app alembic upgrade head
```

---

## 3. Production Code Patterns & Architecture

### Directory Structure
```text
/app
  /api          # Endpoint definitions
  /core         # JWT logic, config, security
  /db           # Database connection & models
  /schemas      # Pydantic models
  /services     # Business logic layer
main.py         # Entry point
```

### The JWT Dependency (core/security.py)
Copy this pattern to protect any endpoint with OAuth2 scopes.
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, "SECRET_KEY", algorithms=["HS256"])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Dockerfile (Production Optimized)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking I/O:** Using standard `requests` or blocking DB drivers inside `async def` routes. **Fix:** Always use `httpx` and `asyncpg`.
*   **Hardcoding Secrets:** Storing JWT keys in code. **Fix:** Use Pydantic Settings (`BaseSettings`) and environment variables.
*   **N+1 Query Problem:** Fetching related database objects inside a loop. **Fix:** Use `joinedload` in SQLAlchemy to fetch related data in a single query.
*   **Exposing Tracebacks:** Letting the server return raw error traces to the client. **Fix:** Use custom Exception Handlers to log errors internally and return sanitized JSON.

---

## 5. Performance & Optimization Tips

1.  **Dependency Injection Caching:** Use `lru_cache` for configuration objects.
2.  **Gunicorn Workers:** In production, wrap Uvicorn with Gunicorn (`gunicorn -k uvicorn.workers.UvicornWorker`). It handles process management better than raw Uvicorn.
3.  **Connection Pooling:** Always configure your SQLAlchemy engine with `pool_size=20` and `max_overflow=10` to prevent DB exhaustion.
4.  **Schema Offloading:** Use `response_model_exclude_unset=True` to reduce payload size on large JSON objects.

---

## 6. Commercial License & Attribution Summary

**License:** MIT License (Commercial Use Permitted).

*   **You may:** Modify, distribute, and sell systems built using this code.
*   **Attribution:** While not strictly required, a link back to *The Agency Engineering Division* in your project's `README.md` is appreciated.
*   **Warranty:** This code is provided "as-is." Always perform an independent security audit before handling production user data.

---
*Architect Note: This blueprint is optimized for "Clean Architecture" principles. If you need to add Redis caching or S3 storage in the future, the `/services` layer is already decoupled to support them.*