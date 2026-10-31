# Product: FastStack Enterprise – The Production-Ready FastAPI Blueprint

## 1. Product Title & Value Proposition
**Title:** `FastStack Enterprise: JWT-Secured FastAPI + Docker Boilerplate`

**Value Proposition:** Stop spending 20+ hours configuring dependency injection, JWT lifecycle management, and containerization. This turnkey architecture provides a hardened, scalable foundation for SaaS products, featuring decoupled services, secure authentication middleware, and production-ready `Dockerfile` configurations.

---

## 2. Quick Start & Core Concepts
Get your development environment spinning in under 5 minutes.

| Feature | Technology | Benefit |
| :--- | :--- | :--- |
| **Framework** | FastAPI | High-concurrency, auto-generated OpenAPI docs. |
| **Auth** | PyJWT | Stateless, scalable session management. |
| **Database** | SQLAlchemy 2.0 | Async ORM for non-blocking I/O. |
| **Container** | Docker + Compose | Environment parity across dev/staging/prod. |
| **Validation** | Pydantic v2 | Industry-standard schema enforcement. |

---

## 3. Production Code Patterns & Architecture
### A. The JWT Security Middleware (`security.py`)
Encapsulate your logic. Do not put auth logic inside the route handler.

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
```

### B. The Production Dockerfile (`Dockerfile`)
Multi-stage build to keep your image size under 100MB.

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install poetry
COPY pyproject.toml .
RUN poetry export -f requirements.txt > requirements.txt

# Stage 2: Runner
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas
*   **The "Fat Controller" Pattern:** Avoid putting business logic in your `main.py` routes. Use `services/` or `crud/` layers.
*   **Hardcoded Secrets:** Never commit `.env` files. Use Pydantic Settings to read from environment variables strictly.
*   **Blocking I/O:** Using standard `requests` or blocking ORM calls in `async def` routes will hang your event loop. Always use `httpx` or `asyncio` compatible drivers.
*   **Lack of CORS Config:** Forgetting to explicitly define `allow_origins` in `CORSMiddleware` leaves your API open to cross-site script injection.

---

## 5. Performance & Optimization Tips
1.  **Dependency Caching:** Use `lru_cache` for database connection pools and shared configuration instances.
2.  **Gunicorn Workers:** In production, wrap Uvicorn with Gunicorn:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
3.  **Schema Serialization:** Leverage `response_model` in FastAPI decorators to minimize data sent to the client and automatically exclude sensitive fields.
4.  **Database Indexing:** Ensure your `User` model has a unique index on the `email` field—`Index(unique=True)`—to prevent race conditions during sign-up.

---

## 6. Commercial License & Attribution Summary

**License:** *Proprietary Commercial Use License*
*   **Grant:** You are granted a non-exclusive, perpetual license to use this codebase for commercial SaaS projects, client work, or internal tooling.
*   **Restriction:** Redistribution of this boilerplate as a standalone product or "template" is strictly prohibited.
*   **Attribution:** No attribution is required in the end-user product, but keeping the `LICENSE.md` file in the repository root is required for internal tracking.

***

**Architect’s Note:** *This system is built for scale. When you hit 10k+ concurrent users, look into transitioning from local JWT storage to an encrypted Redis store for token blacklisting.*