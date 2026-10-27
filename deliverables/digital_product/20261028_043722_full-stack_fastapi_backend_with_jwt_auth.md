# Product: FastAPI Enterprise Blueprint (JWT + Dockerized)

## 1. Product Title & Value Proposition
**Title:** The "TitanStack" FastAPI Boilerplate: Production-Ready JWT Auth & Dockerized Architecture.

**Value Proposition:** Stop spending 20+ hours configuring authentication middleware, dependency injection, and container orchestration. This turnkey solution provides a battle-tested foundation for high-concurrency REST APIs, ensuring your backend is secure, scalable, and ready for deployment to AWS/GCP/DigitalOcean within minutes.

---

## 2. Quick Start & Core Concepts

| Concept | Implementation Strategy | Why? |
| :--- | :--- | :--- |
| **Auth** | OAuth2 + JWT (RS256) | Stateless, industry standard. |
| **Containers** | Multi-stage Dockerfile | Minimized image size, faster CI/CD. |
| **DB Layer** | SQLAlchemy 2.0 (Async) | Non-blocking I/O for high throughput. |
| **Validation** | Pydantic v2 | Extreme speed, strict data typing. |
| **Project Layout** | Domain-Driven | Maintainable as the app grows. |

**Quick Start CLI:**
```bash
# Clone and install dependencies
git clone <repo-url> && cd titanstack
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run locally with Docker
docker-compose up --build
```

---

## 3. Production Code Patterns & Architecture

### The `security.py` (JWT Implementation)
```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "SUPER_SECRET_KEY" # Use environment variables!
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### The `Dockerfile` (Multi-Stage Build)
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Anti-Pattern: Global DB Sessions.** 
    *   *Fix:* Use `Depends(get_db)` to ensure session lifecycle management and avoid connection pool exhaustion.
*   **Anti-Pattern: Hardcoding Secrets.** 
    *   *Fix:* Utilize Pydantic `BaseSettings` for `.env` loading. Never commit secrets to Git.
*   **Gotcha: Blocking I/O.**
    *   *Fix:* Avoid standard `requests` or `time.sleep()`. Always use `httpx` and `asyncio.sleep()` to keep the Event Loop healthy.
*   **Gotcha: Omiting CORS.**
    *   *Fix:* Explicitly define allowed origins in `FastAPI(middleware=...)`. Don't leave `allow_origins=["*"]` in production.

---

## 5. Performance & Optimization Tips

1.  **Gunicorn Workers:** Deploy using `gunicorn` with `uvicorn.workers.UvicornWorker` to utilize multiple CPU cores effectively.
2.  **Response Models:** Use Pydantic `response_model` to exclude sensitive fields (like hashed passwords) from JSON responses automatically.
3.  **Connection Pooling:** Configure SQLAlchemy pool settings (`pool_size`, `max_overflow`) based on your DB instance specs.
4.  **Caching:** Implement `fastapi-cache` with Redis for frequently queried, static data endpoints to reduce latency by ~90%.

---

## 6. Commercial License & Attribution Summary

**License: Proprietary Commercial Use**
*   **Grant:** This code is licensed to the purchaser for use in unlimited personal and commercial projects.
*   **Restrictions:** You may not redistribute, resell, or open-source this boilerplate as a standalone product.
*   **Liability:** Provided "as-is" without warranty. MicroCorp AI is not liable for infrastructure costs or security breaches resulting from improper configuration.

**Attribution:** Developed by The Agency Engineering Division. *System Reference ID: TS-FASTAPI-2024*

---
*Architect's Note: Keep your containers small, your dependencies pinned, and your secrets rotated. Happy coding.*