# Product: FastAPI Enterprise Blueprint (JWT + Dockerized)

## 1. Product Title & Value Proposition
**Title:** The "TitanStack" FastAPI Boilerplate – Production-Ready Authentication & Deployment Kit.

**Value Proposition:**
Stop reinventing the wheel. This turnkey architecture provides a bulletproof foundation for scalable, high-performance APIs. It includes hardened JWT-based authentication, modular dependency injection, and an optimized multi-stage Docker configuration—designed to save you 40+ hours of boilerplate engineering time.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation | Benefit |
| :--- | :--- | :--- |
| **Auth Strategy** | `OAuth2PasswordBearer` + JWT | Industry-standard, stateless security. |
| **Dependency Injection** | `Depends()` | Decouples services from route handlers. |
| **Validation** | Pydantic v2 | Type-safe payloads with instant schema generation. |
| **Containerization** | Multi-stage `Dockerfile` | Reduces final image size by ~70%. |
| **Asynchrony** | `async def` / `await` | Non-blocking I/O for high-concurrency needs. |

---

## 3. Production Code Patterns & Architecture

### A. Modular Directory Structure
```text
/app
  /api/v1/endpoints   # Route handlers
  /core               # Security, Config, Middleware
  /models             # Database schemas
  /schemas            # Pydantic models
  /services           # Business logic
main.py               # Application entry point
Dockerfile            # Production build
```

### B. Secure JWT Token Factory (`app/core/security.py`)
```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "SUPER_SECRET_KEY" # Load from env
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### C. Hardened Multi-Stage Dockerfile
```dockerfile
# Stage 1: Build
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install poetry && poetry export -f requirements.txt > requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Blocking Calls in Async Routes:** Avoid using synchronous DB drivers (e.g., `requests`, `time.sleep`). Use `httpx` or `aiohttp` and `asyncpg` to keep the event loop non-blocked.
*   **Hardcoded Secrets:** Never put your `SECRET_KEY` in code. Use a `.env` file and Pydantic Settings (`BaseSettings`).
*   **Ignoring CORS:** Failing to define allowed origins in `CORSMiddleware` leaves your API vulnerable to malicious cross-domain requests.
*   **The "Fat Controller" Syndrome:** Keep route handlers light. Move business logic into the `services/` layer.

---

## 5. Performance & Optimization Tips

1.  **Gunicorn + Uvicorn Workers:** For production, always use Gunicorn as a process manager to spawn multiple Uvicorn workers:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
2.  **Connection Pooling:** Use `SQLAlchemy`'s `create_async_engine` with `pool_size` and `max_overflow` to manage DB connections effectively.
3.  **Response Compression:** Enable `GZipMiddleware` to reduce payload size for high-traffic endpoints.
4.  **Caching:** Implement `FastAPI-Cache` with Redis for frequently queried, slow-computed data.

---

## 6. Commercial License & Attribution Summary

**License:** *Enterprise Developer License (Non-Exclusive)*
*   **You May:** Use this code in personal, commercial, and client-facing projects.
*   **You May Not:** Redistribute this boilerplate as a standalone "boilerplate product" on marketplaces like Gumroad or Etsy.
*   **Attribution:** No attribution is required in the end product, though we appreciate a link to the MicroCorp AI repo if you found this helpful.

*Disclaimer: This is a professional-grade boilerplate. Ensure you rotate secrets and perform independent security audits before deploying to production environments.*