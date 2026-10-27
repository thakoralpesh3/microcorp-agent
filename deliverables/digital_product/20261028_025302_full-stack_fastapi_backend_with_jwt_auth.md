# Full-Stack FastAPI Enterprise Boilerplate: JWT & Docker-Ready

## 1. Product Title & Value Proposition
**Title:** The "Titan-Stack" FastAPI Starter Kit
**Value Proposition:** Stop spending 20+ hours configuring dependency injection, JWT middleware, and Docker multi-stage builds. This turnkey solution provides a production-hardened foundation for high-concurrency REST APIs, featuring native OAuth2 scope handling, SQLAlchemy 2.0 async integration, and a standardized Docker-Compose pipeline.

---

## 2. Quick Start & Core Concepts
Get your environment spinning in under 60 seconds with this modular structure.

### Core Syntax Reference
| Concept | Implementation Library | Purpose |
| :--- | :--- | :--- |
| **Async ORM** | `SQLAlchemy` + `aiosqlite`/`asyncpg` | Non-blocking database I/O |
| **Auth** | `PyJWT` + `PassLib` | Industry-standard token handling |
| **Validation** | `Pydantic v2` | Strict schema enforcement |
| **Dependency Injection** | `FastAPI.Depends` | Decoupled business logic |
| **Containerization** | `Docker Multi-stage` | Minimized image footprint |

---

## 3. Production Code Patterns & Architecture
### The JWT Auth Dependency Pattern
*File: `app/core/security.py`*
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, "SECRET_KEY", algorithm="HS256")
```

### Clean Architecture Router
*File: `app/api/endpoints/users.py`*
```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user

router = APIRouter()

@router.get("/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return {"user": current_user.email}
```

### Multi-Stage Dockerfile
*File: `Dockerfile`*
```dockerfile
# Build Stage
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry && poetry export -f requirements.txt > requirements.txt

# Final Stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas
*   **The "Fat Router" Syndrome:** Avoid putting business logic inside your route functions. Use a `Service` or `Repository` layer to keep routers thin (Routing -> Service -> DB).
*   **Hardcoded Secrets:** Never inject environment variables via the source code. Always use `pydantic-settings` to load from a `.env` file or Secret Manager.
*   **Blocking I/O:** Using `time.sleep()` or synchronous database drivers will hang your entire event loop. Always use `await`.
*   **Insecure Token Refresh:** Implementing JWT without a rotation strategy or a blacklist in Redis makes your API vulnerable to stolen tokens.

---

## 5. Performance & Optimization Tips
1.  **Gunicorn Workers:** Deploy with `gunicorn -k uvicorn.workers.UvicornWorker` to utilize multi-core architecture effectively.
2.  **Connection Pooling:** Configure SQLAlchemy pool size based on your database instance limits (e.g., `pool_size=20, max_overflow=10`).
3.  **Caching Strategy:** Wrap expensive DB queries in `fastapi-cache` with an internal Redis backend to reduce latency by 80%.
4.  **UJSON/Orjson:** Swap the default `json` library for `orjson` to achieve up to 5x faster serialization speeds.

---

## 6. Commercial License & Attribution Summary

*   **Usage Rights:** This boilerplate is licensed under the **MIT License**. You are free to use it for personal, commercial, or white-labeled client projects.
*   **Attribution:** No attribution is required, though linking back to the *MicroCorp AI GitHub* is appreciated.
*   **Warranty:** This code is provided "as-is." Always perform an independent security audit (e.g., `bandit` or `snyk`) before deploying to production environments handling PII or sensitive financial data.

***
*Architect's Note: Keep your logs structured and your database migrations versioned. Good luck with the deployment.*