# Python Web Automation & Agent Integration Specialist: Developer Reference & Architecture Kit

> **Version:** 2.4.0-enterprise  
> **Target Runtime:** Python 3.11+ / Asyncio / Playwright / LangChain & Pydantic v2  
> **Author:** Developer Tooling Engineering | MicroCorp AI

---

## 1. # Product Title & Value Proposition

Modern web automation has evolved beyond simple DOM scraping and brittle XPath selectors. Today's architectures require **autonomous web agents** capable of reasoning, handling CAPTCHAs, executing JavaScript-heavy SPAs, and structuring unstructured HTML into reliable, typed data schemas for LLMs.

The **Python Web Automation & Agent Integration Specialist Kit** is a battle-tested reference architecture and code boilerplate engineered for senior developers, AI engineers, and automation architects. 

### Why This Kit Exists
- **Eliminate Brittle Scripts:** Move away from hardcoded sleeps and outdated Selenium configurations to resilient, async-first Playwright pipelines.
- **Agent-Ready Topologies:** Provide native Pydantic-driven data extraction bridges directly consumable by LangChain, LlamaIndex, or custom OpenAI/Anthropic function-calling pipelines.
- **Enterprise Reliability:** Out-of-the-box exponential backoff, stealth browser fingerprinting configuration, memory management, and structured error boundaries that state the exact fix.

---

## 2. ## Quick Start & Core Concepts

### Architectural Overview
```
[ Target Web App ] <---> [ Playwright Async Engine ] <---> [ DOM Sanitizer ]
                                                                 |
[ LLM Agent / Tool ] <--- [ Pydantic v2 Schema Validation ] <----+
```

### Core Concepts & Syntax Reference

| Concept | Python Native / Library | Purpose in Agent Pipelines |
| :--- | :--- | :--- |
| **Async Context Management** | `async with async_playwright()` | Prevents zombie browser processes and manages memory efficiently across concurrent tasks. |
| **Resilient Locators** | `page.get_By_role()`, `locator.filter()` | Decouples automation from fragile CSS class names and IDs; targets accessibility roles. |
| **Type-Safe Extraction** | `pydantic.BaseModel` | Enforces structural constraints on scraped data before handing off to LLM agents. |
| **Stealth Injection** | `context.add_init_script()` | Neutralizes standard bot-detection vectors (`navigator.webdriver`, headless signatures). |
| **Declarative Waiting** | `expect(locator).to_be_visible()` | Replaces hardcoded `time.sleep()` with event-driven assertions. |

---

## 3. ## Production Code Patterns & Architecture Examples

The following production-ready module demonstrates an asynchronous, stealth-enabled Playwright scraper integrated with a Pydantic validation model, designed to be wrapped as an LLM agent tool.

```python
"""
Module: web_agent_extractor.py
Description: Production-grade asynchronous web automation and typed extraction engine.
Dependencies: playwright, pydantic>=2.0
Quick Fix for Missing Dependencies: Run `pip install playwright pydantic && playwright install chromium`
"""

import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from playwright.async_api import async_playwright, Page, BrowserContext, expect

# Configure structured logging respecting pipe/TTY conventions
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WebAgentSpecialist")

# --- 1. TYPED EXTRACTION SCHEMAS ---

class ProductListing(BaseModel):
    title: str = Field(..., description="The official product title.")
    price_usd: float = Field(..., description="Extracted price normalized to USD float.")
    in_stock: bool = Field(default=True, description="Stock availability status.")
    detail_url: Optional[str] = Field(None, description="Absolute URL to product details.")

class ExtractionResult(BaseModel):
    query: str
    items: List[ProductListing]
    total_found: int

# --- 2. STEALTH & BROWSER FACTORY ---

async def create_stealth_context(p) -> tuple:
    """Spawns an optimized, headless Chromium browser instance with anti-detection patches."""
    browser = await p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York"
    )
    
    # Inject evasion scripts to mask automation flags
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    """)
    
    return browser, context

# --- 3. CORE EXTRACTION ENGINE ---

async def extract_product_data(target_url: str, search_term: str) -> ExtractionResult:
    """
    Navigates to a target site, executes search, and extracts typed data.
    Raises RuntimeError with corrective instructions if automation fails.
    """
    async with async_playwright() as p:
        try:
            browser, context = await create_stealth_context(p)
            page = await context.new_page()
            
            logger.info(f"Navigating to target endpoint: {target_url}")
            try:
                await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to reach {target_url} within 30s. "
                    "Fix: Check network connectivity or verify URL correctness."
                ) from e

            # Example Interaction: Handling a search input
            search_input = page.get_by_role("searchbox", name=re.compile("search", re.IGNORECASE))
            if await search_input.count() == 0:
                # Fallback to common CSS selectors if ARIA role is missing
                search_input = page.locator("input[name*='q'], input[name*='search']").first
            
            if await search_input.count() == 0:
                raise RuntimeError(
                    "Search input element not found on page. "
                    "Fix: Inspect target DOM and update the locator strategy."
                )

            await search_input.fill(search_term)
            await search_input.press("Enter")
            
            # Wait for results container using resilient assertion
            results_container = page.locator(".product-grid, [data-testid='results-container']").first
            try:
                await expect(results_container).to_be_visible(timeout=10000)
            except AssertionError as e:
                raise RuntimeError(
                    "Results container failed to render. "
                    "Fix: The site may be blocking headless requests or utilizing dynamic shadow DOMs."
                ) from e

            # Extract raw DOM elements
            raw_items = []
            cards = page.locator(".product-card, article")
            count = await cards.count()
            
            for i in range(min(count, 10))): # Limit to top 10 for agent efficiency
                card = cards.nth(i)
                title_elem = card.locator("h2, h3, .title").first
                price_elem = card.locator(".price, [data-price]").first
                link_elem = card.locator("a").first
                
                title = await title_elem.inner_text() if await title_elem.count() > 0 else "Unknown"
                price_text = await price_elem.inner_text() if await price_elem.count() > 0 else "0.00"
                
                # Normalize price string (e.g., "$49.99" -> 49.99)
                clean_price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
                
                href = await link_elem.get_attribute("href") if await link_elem.count() > 0 else None
                
                raw_items.append({
                    "title": title.strip(),
                    "price_usd": clean_price,
                    "in_stock": True,
                    "detail_url": href
                })

            # Validate via Pydantic to guarantee agent schema safety
            validated_listings = [ProductListing(**item) for item in raw_items]
            
            return ExtractionResult(
                query=search_term,
                items=validated_listings,
                total_found=len(validated_listings)
            )

        except ValidationError as ve:
            logger.error(f"Data schema mismatch: {ve}")
            raise RuntimeError(
                "Extracted web data failed Pydantic schema validation. "
                "Fix: Inspect target site layout changes against ProductListing model fields."
            ) from ve
        finally:
            await browser.close()

# --- 4. CLI / EXECUTION ENTRYPOINT ---
if __name__ == "__main__":
    import sys
    target = "https://example-ecommerce.com"
    query = "wireless mechanical keyboard"
    
    try:
        result = asyncio.run(extract_product_data(target, query))
        print(result.model_dump_json(indent=2))
    except RuntimeError as err:
        print(f"\x1b[31m[ERROR] {err}\x1b[0m", file=sys.stderr)
        sys.exit(1)
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Production Approach |
| :--- | :--- | :--- |
| **Using `time.sleep(5)`** | Wastes execution cycles and fails intermittently on slow network connections. | Use Playwright's built-in auto-waiting assertions (`expect(locator).to_be_visible()`). |
| **Hardcoded XPath/CSS selectors** | Breaks immediately upon minor frontend deployments or A/B testing changes. | Prefer accessibility locators (`page.get_by_role()`, `get_by_text()`, or semantic data attributes). |
| **Ignoring Browser Context Leakage** | Leaves zombie Chromium processes running, consuming RAM and causing OOM killer events in CI/CD. | Always wrap browser execution in `async with` blocks or robust `try/finally` cleanup handlers. |
| **Raw Unsanitized LLM Web Prompts** | Directly passes raw, unvalidated scraped HTML into LLMs, opening prompt injection vectors. | Always validate scraped payloads through strict Pydantic models before passing to agent context. |

---

## 5. ## Performance & Optimization Tips

1. **Block Unnecessary Resource Types:** Drastically speed up page load times (up to 300%) by intercepting and aborting image, font, and stylesheet requests when scraping text-heavy data:
   ```python
   await page.route("**/*.{png,jpg,jpeg,svg,css,font,woff}", lambda route: route.abort())
   ```
2. **Reuse Browser Contexts:** Avoid launching a fresh browser instance for every URL. Spin up a single browser daemon and spawn isolated lightweight `BrowserContext` instances per concurrent task.
3. **Headless Mode with GPU Acceleration Off:** Always ensure `--disable-gpu` and `--headless=new` flags are active to reduce container memory footprint in Docker/Kubernetes deployments.
4. **Connection Pooling & Concurrency Limits:** Use `asyncio.Semaphore(5)` to cap concurrent browser tabs, preventing CPU throttling and target-site rate limiting (HTTP 429).

---

## 6. ## Commercial License & Attribution Summary

### End-User Commercial License Agreement
- **Grant of Rights:** MicroCorp AI grants the purchaser a perpetual, non-exclusive, worldwide license to use, modify, adapt, and incorporate this code kit into commercial software applications, agent frameworks, and enterprise automation pipelines.
- **Restrictions:** Redistribution, resale, or sub-licensing of this exact reference document or its raw source code as a standalone training dataset, template product, or competing developer kit is strictly prohibited.
- **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. MicroCorp AI is not liable for target website blocks, IP bans, or changes to external DOM structures.

© 2026 MicroCorp AI Engineering Division. All rights reserved.