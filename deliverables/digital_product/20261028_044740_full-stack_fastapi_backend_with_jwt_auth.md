# Product: FastAPI Enterprise Blueprint (JWT + Dockerized)

## 1. Product Title & Value Proposition
**Title:** The "TitanStack" FastAPI Boilerplate  
**Value Proposition:** Stop spending 20+ hours configuring authentication flows, dependency injection, and containerization. The TitanStack provides a production-ready, security-hardened FastAPI foundation designed for high-concurrency and rapid deployment. 

*   **Authentication:** RS256 JWT implementation (industry standard).
*   **DevOps:** Multi-stage Dockerfile for minimized image footprint.
*   **Architecture:** Clean, modular repository structure.

---

## 2. Quick Start & Core Concepts
| Component | Technology | Role |
| :--- | :--- | :--- |
| **API Framework** | FastAPI | Async-first, performance-oriented framework. |
| **Authentication** | PyJWT | Standardized stateless token-based auth. |
| **Database** | SQLAlchemy 2.0 | Async ORM for non-blocking I/O. |
| **Containerization**| Docker/Compose | Environment consistency across dev/prod. |
| **Validation** | Pydantic v2 | High-speed data parsing and schema integrity. |

**Installation:**
```bash
# Clone the repository
git clone https://github.com/microcorp/titan-stack.git
# Launch local dev environment
docker-compose up --build
```

---

## 3. Production Code Patterns & Architecture
### Directory Structure
```text
/app
  /api/v1/endpoints  # Route definitions
  /core              # Config & JWT logic
  /models            # SQLAlchemy tables
  /schemas           # Pydantic validation
  /services          # Business logic (Don't put logic in routes!)
main.py              # Application entry point
```

### JWT Security Pattern (`app/core/security.py`)
```python
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "SUPER_SECRET_KEY" # Use environment variables!
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### Async Database Session Middleware
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@db/dbname")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 4. Common Anti-Patterns & Gotchas
*   **The "Fat Route" Anti-Pattern:** Never write SQL queries or complex business logic inside your `router` functions. Keep your routers as pure "Controllers" that delegate to a `/services` layer.
*   **Hardcoded Secrets:** Never push `.env` files. Use `pydantic-settings` to inject configurations via OS environment variables.
*   **Blocking I/O:** Using standard `requests` or blocking `time.sleep()` inside FastAPI stops the entire event loop. Always use `httpx` or `aiofiles`.

---

## 5. Performance & Optimization Tips
1.  **Gunicorn + Uvicorn Workers:** For production, use `gunicorn -k uvicorn.workers.UvicornWorker`. It manages multiple processes, ensuring high availability.
2.  **Schema Caching:** Utilize `response_model_exclude_unset=True` in your endpoint definitions to minimize payload sizes.
3.  **Connection Pooling:** Always tune your `pool_size` and `max_overflow` in your SQLAlchemy engine settings to prevent DB exhaustion during traffic spikes.
4.  **Health Checks:** Always include a `/health` endpoint that checks DB connectivity; your load balancer (AWS ALB/K8s) needs this to manage lifecycle events.

---

## 6. Commercial License & Attribution Summary

**License: Commercial Use Grant**
*   **Permitted:** You may use this codebase as the foundation for internal projects, client deliverables, or SaaS products.
*   **Prohibited:** You may not redistribute the boilerplate as a stand-alone "starter kit" or "template" for sale on marketplaces.
*   **Attribution:** Please maintain the `MicroCorp AI` header in the `README.md` files of your deployed products to support future maintenance of the stack.

*Engineered by MicroCorp AI Backend Division. Built for Scale.*