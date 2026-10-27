# Product: FastStack Enterprise – The Production-Grade FastAPI Boilerplate

## 1. Product Title & Value Proposition
**Title:** FastStack Enterprise: Secure JWT-Auth FastAPI with Dockerized Deployment.
**Value Proposition:** Stop spending 20+ hours configuring dependency injection, JWT middleware, and Docker orchestration. This turnkey solution provides a battle-tested architecture that scales, ensuring your backend is secure, performant, and ready for CI/CD pipelines from Day 1.

---

## 2. Quick Start & Core Concepts
This boilerplate follows the **Clean Architecture** pattern to keep business logic decoupled from transport layers.

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | FastAPI | Async-first, high-performance API routing |
| **Auth** | PyJWT | Stateless, scalable token-based authentication |
| **Database** | SQLAlchemy 2.0 | Async ORM with Migrations (Alembic) |
| **Container** | Docker/Compose | Environment consistency (Dev/Prod) |
| **Validation** | Pydantic v2 | Type-safe request/response parsing |

---

## 3. Production Code Patterns & Architecture Examples

### A. The JWT Security Dependency
Place this in `app/core/security.py` to protect sensitive routes.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, "SECRET_KEY", algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None: raise HTTPException(status_code=401)
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

### B. Dockerfile (Optimized for Multi-Stage Build)
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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid
*   **The "Fat Router" Trap:** Avoid putting business logic inside `routers/`. Keep routes thin; delegate logic to a `services/` layer.
*   **Hardcoding Secrets:** Never store `.env` values in Git. Always use `pydantic-settings` to load configuration from environment variables.
*   **Blocking I/O:** Using standard `requests` or blocking ORM calls in `async def` routes will kill your event loop. Use `httpx` and `asyncpg`.
*   **CORS Negligence:** Don't use `allow_origins=["*"]` in production. Explicitly define your frontend domain.

---

## 5. Performance & Optimization Tips
1.  **Gunicorn Workers:** In production, run FastAPI with `gunicorn` + `uvicorn` workers for better stability under high concurrency.
2.  **Connection Pooling:** Use `AsyncSession` with a scoped lifecycle to prevent database connection leaks.
3.  **Caching:** Implement `Redis` for high-frequency `GET` requests (e.g., Auth token verification or public static metadata).
4.  **Pydantic V2:** Always define `model_config = ConfigDict(from_attributes=True)` to leverage high-performance serialization.

---

## 6. Commercial License & Attribution Summary

**License: Proprietary Commercial Use**
*   **Permitted:** You may use this boilerplate for your internal projects, freelance client work, and commercial SaaS products.
*   **Prohibited:** You may **not** resell this boilerplate as a stand-alone product or template on marketplaces (e.g., Gumroad, ThemeForest).
*   **Attribution:** No attribution is required in your end-product, but credit back to *MicroCorp AI Engineering* is appreciated.

---
*Architect's Note: Keep your migration scripts versioned and your dependencies pinned. Build for change, not just for code.*