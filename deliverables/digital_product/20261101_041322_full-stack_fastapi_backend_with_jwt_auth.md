# Product Title: FastAuth Pro — Enterprise-Grade FastAPI Boilerplate

## 1. Product Title & Value Proposition
**FastAuth Pro** is a production-ready, modular FastAPI scaffolding kit designed to eliminate the 20-hour setup time for secure, scalable RESTful APIs. 

**Value Proposition:**
*   **Zero-to-Deployed:** Complete Docker/Docker-Compose orchestration.
*   **Security First:** Stateless JWT authentication with Argon2 password hashing.
*   **Enterprise Architecture:** Clean dependency injection and repository patterns.
*   **Time-to-Market:** Perfect for rapid prototyping or high-performance microservices.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation | Why? |
| :--- | :--- | :--- |
| **Auth Strategy** | JWT (RS256) | Stateless, scalable, avoids DB lookups per request. |
| **Data Validation** | Pydantic v2 | High-speed type safety and auto-doc generation. |
| **DB Layer** | SQLAlchemy 2.0 (Async) | Non-blocking I/O for high concurrency. |
| **Containerization** | Multi-stage Docker | Minimal image footprint, hardened security. |

---

## 3. Production Code Patterns

### The Authentication Guard (`security.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user_id
```

### The Dockerfile (Production Optimized)
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

*   **Blocking I/O in Async Routes:** Never use `time.sleep()` or standard `requests` library inside an `async def`. It halts the event loop. Use `asyncio.sleep()` or `httpx`.
*   **Hardcoded Secrets:** Never include `.env` or hardcoded tokens in your repo. Use `pydantic-settings` to inject configurations via environment variables.
*   **Ignoring CORS:** Developers often set `allow_origins=["*"]`. In production, strictly whitelist your frontend domain.
*   **N+1 Query Problems:** Always use `joinedload` or `selectinload` in SQLAlchemy when dealing with relational data to avoid database bombardment.

---

## 5. Performance & Optimization Tips

1.  **Gunicorn Workers:** Always use Uvicorn with Gunicorn (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker`) to manage multiple processes on multi-core systems.
2.  **Connection Pooling:** Configure SQLAlchemy's `pool_size` and `max_overflow` to match your database instance’s capacity.
3.  **Caching:** Integrate `fastapi-cache` with Redis for expensive read operations (e.g., dashboard stats).
4.  **Health Checks:** Expose a `/health` endpoint that checks the DB connection status; this allows K8s or Docker Swarm to cycle unresponsive containers.

---

## 6. Commercial License & Attribution Summary

**Commercial Usage Rights:**
*   **Grant:** This boilerplate is licensed under the *MicroCorp Enterprise License*. You are permitted to use this code in unlimited commercial products, SaaS platforms, and client deliverables.
*   **Restrictions:** You may not redistribute this boilerplate as a competing "Template" or "Scaffolding Kit" without written consent from MicroCorp AI.
*   **Attribution:** Attribution is appreciated but not required. Keep the header comments intact if possible to assist with future developer onboarding.

*© 2024 MicroCorp AI Engineering Division. All rights reserved.*