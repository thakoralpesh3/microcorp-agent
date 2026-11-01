# Product Title: FastAuth-Stack Pro
**The Enterprise-Grade FastAPI + JWT + Docker Boilerplate**

### Value Proposition
Stop reinventing the auth wheel. This turnkey solution provides a production-ready, security-hardened backend architecture. Designed for developers who need to ship secure, scalable REST APIs without the overhead of debugging standard boilerplate for weeks. 

---

## 1. Quick Start & Core Concepts

This boilerplate uses **FastAPI** for performance, **PyJWT** for authentication, and **Docker/Docker-Compose** for environment parity.

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Framework** | FastAPI | High-speed, async request handling |
| **Auth** | PyJWT | Stateless, secure token-based authentication |
| **Database** | PostgreSQL | Robust relational data storage |
| **Container** | Docker | Environment consistency and portability |
| **Validation** | Pydantic v2 | Strict schema enforcement |

---

## 2. Production Code Patterns

### A. JWT Security Dependency
Place this in `app/core/security.py` to protect your sensitive endpoints.

```python
from datetime import datetime, timedelta
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "SUPER_SECRET_KEY_REPLACE_IN_ENV"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

### B. Dockerfile (Optimized Multi-Stage)
Keep your image footprint under 150MB by utilizing multi-stage builds.

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

## 3. Common Anti-Patterns & Gotchas

*   **Hardcoding Secrets:** Never commit `.env` files. Use `pydantic-settings` to manage environment variables.
*   **Blocking I/O:** FastAPI is asynchronous. Avoid using synchronous libraries (like `requests` or blocking DB drivers) inside route handlers. Use `httpx` or `asyncpg` instead.
*   **Excessive Logging:** Do not log full JWT payloads or sensitive headers in production; use standard JSON logging for observability.
*   **Missing CORS:** Forgetting to explicitly define `CORSMiddleware` origins will break your frontend integration.

---

## 4. Performance & Optimization Tips

1.  **Uvicorn Worker Management:** In production, use `gunicorn` with `uvicorn` workers to handle multi-core utilization:
    `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
2.  **Connection Pooling:** Use `SQLAlchemy` or `Tortoise-ORM` connection pools to prevent database connection exhaustion.
3.  **Dependency Injection:** Leverage FastAPI’s `Depends` to cache expensive calculations or DB sessions across multiple requests.
4.  **Caching:** Use Redis for JWT blacklisting (if implementing logout) and rate limiting to prevent DDoS.

---

## 5. Commercial License & Attribution

**Terms of Use:**
*   **License:** This code is provided under the **MIT License**. You are free to modify, distribute, and use it in commercial projects.
*   **Attribution:** While not strictly required, a link back to MicroCorp AI is appreciated for ongoing updates.
*   **Disclaimer:** This is a scaffolding tool. Always perform a security audit on your implementation before deploying to high-traffic production environments. 

---
*Architect's Note: Keep your `.env` files out of source control. Use HashiCorp Vault or AWS Secrets Manager for true enterprise-scale deployment.*