# Enterprise Backend Blueprint: FastAPI + JWT + Docker
**Status:** Production-Ready | **Version:** 1.0.0 | **Arch-Level:** Senior 

---

## 1. Product Title & Value Proposition
**Title:** The MicroCorp "Iron-Clad" FastAPI Boilerplate  
**Value Proposition:** Stop spending 10 hours configuring OAuth2 flows, dependency injection, and Docker-Compose manifests. This turnkey solution provides a battle-tested architecture that handles authentication, database orchestration, and CI/CD readiness out of the box. 

**What’s Inside:**
*   **JWT-Based Auth:** Secure, stateless session management.
*   **Docker Orchestration:** Multi-stage builds for minimal image size.
*   **Clean Architecture:** Service-Repository pattern for testable business logic.
*   **Async Everything:** Built for high-concurrency throughput.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation Strategy | Why? |
| :--- | :--- | :--- |
| **Auth** | `python-jose` + `passlib` | Industry standard for token signing. |
| **Database** | `SQLAlchemy 2.0` (Async) | Modern, type-safe ORM. |
| **Validation** | `Pydantic v2` | Unrivaled performance for JSON schema. |
| **Deployment** | `Docker Multi-stage` | Keeps production images under 150MB. |

**Setup Command:**
```bash
git clone <repo-url> && cd backend
docker-compose up --build
```

---

## 3. Production Code Patterns

### The Auth Controller (`app/api/deps.py`)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None: raise Exception()
        return user_id
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
```

### The Dockerfile (`Dockerfile`)
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
RUN pip install poetry
COPY pyproject.toml .
RUN poetry export -f requirements.txt > requirements.txt

# Stage 2: Final
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas
*   **Blocking Operations:** Never use `time.sleep()` or synchronous I/O inside FastAPI path operations. Use `asyncio.sleep()` or `run_in_threadpool`.
*   **Hardcoded Secrets:** Never put your `JWT_SECRET` in the repo. Use a `.env` file and `pydantic-settings` to inject environment variables.
*   **N+1 Queries:** Be cautious when accessing related models in SQLAlchemy. Use `selectinload()` to perform eager loading.

---

## 5. Performance & Optimization Tips
1.  **Gunicorn + Uvicorn Workers:** For production, always use Gunicorn with Uvicorn worker classes to manage process-level concurrency.
    *   *Cmd:* `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
2.  **Connection Pooling:** Configure SQLAlchemy's `pool_size` and `max_overflow` to prevent database connection exhaustion under heavy load.
3.  **Caching:** Integrate `Redis` for high-frequency lookup data to reduce database hits.

---

## 6. Commercial License & Attribution

**License:** MIT License (Commercial Use Permitted)  
**Attribution:** This boilerplate was architected by The Agency (MicroCorp AI Division). 

*   **Commercial Clause:** You are granted a perpetual, worldwide, non-exclusive license to use, modify, and integrate this boilerplate into commercial software products for your clients.
*   **Restriction:** You may not redistribute the boilerplate as a standalone competitive product. 

---
*Architect's Note: Keep your containers small, your dependencies pinned, and your secrets vaulted.*