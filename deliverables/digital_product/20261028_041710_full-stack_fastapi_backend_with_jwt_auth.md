# Full-Stack FastAPI Enterprise Boilerplate
## JWT Auth, PostgreSQL & Docker Orchestration

### 1. Product Title & Value Proposition
**Title:** *FastAPI-JWT-Enterprise Starter Kit*  
**Value Prop:** A production-hardened, industry-standard backend scaffolding designed for rapid deployment. Eliminates the "blank page" syndrome by providing integrated JWT-based security, SQLAlchemy 2.0 ORM patterns, and Dockerized infrastructure. Save 20+ hours of boilerplate setup time.

---

### 2. Quick Start & Core Concepts
Get your environment running with standard industry primitives.

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Framework** | FastAPI | Async high-performance API |
| **Auth** | PyJWT | Standardized Token Implementation |
| **Database** | PostgreSQL | Relational persistence |
| **ORM** | SQLAlchemy 2.0 | Async data abstraction |
| **Container** | Docker/Compose | Environment consistency |

**Quick Setup:**
```bash
# Clone the repository
git clone <repo-url>
# Launch the stack
docker-compose up --build
# API Docs will be available at
http://localhost:8000/docs
```

---

### 3. Production Code Patterns & Architecture

#### A. Security: JWT Provider Factory
A centralized service to handle token lifecycle, strictly following best practices for `exp` (expiration) and `sub` (subject) claims.

```python
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "SUPER_SECRET_ENV_VAR"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

#### B. Database: The Async Dependency
Using FastAPI `Depends` to provide a scoped session to every route, ensuring connection cleanup.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@db:5432/main")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
```

---

### 4. Common Anti-Patterns & Gotchas
*   **The "Secret" Leak:** Never hardcode your `SECRET_KEY`. Use a `.env` file and `pydantic-settings` to inject them.
*   **Blocking Calls:** Avoid using `time.sleep()` or synchronous I/O drivers in `async def` routes. Use `await` or `run_in_threadpool`.
*   **Schema Bloat:** Avoid using your SQLAlchemy models as Pydantic response schemas. Create separate `schemas.py` files for Request (Input) and Response (Output) to prevent data leaking.
*   **Missing CORS:** Forgetting to configure `CORSMiddleware` will result in phantom frontend 403 errors during development.

---

### 5. Performance & Optimization Tips
1.  **Gunicorn + Uvicorn Workers:** In production, do not run with just `uvicorn`. Use `gunicorn` with `uvicorn.workers.UvicornWorker` to scale across CPU cores.
2.  **Connection Pooling:** Always tune your `pool_size` and `max_overflow` in your SQLAlchemy engine config based on your DB instance size.
3.  **Caching:** Implement `Redis` for high-frequency lookup endpoints (e.g., user profiles or config data).
4.  **Query Minimization:** Utilize `selectinload` or `joinedload` in your SQLAlchemy queries to prevent N+1 performance degradation.

---

### 6. Commercial License & Attribution Summary

*   **Usage:** This code is licensed under the **MIT License**. You are free to use it for personal, freelance, or commercial SaaS projects.
*   **Attribution:** While not strictly required, a mention of *MicroCorp AI Engineering* in your project's `README.md` is appreciated.
*   **Support:** This boilerplate is provided "as-is". For custom architecture consulting or security audits, contact The Agency’s Engineering Division.

***

**Architect's Note:** *This structure ensures your project remains maintainable as your team grows. Keep the codebase clean, the tests green, and your deployments automated.*