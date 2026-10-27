# Developer Toolkit: Genie 4 Mastery Pack

**The definitive architecture guide for integrating and scaling high-latency LLM workflows in production.**

---

## 1. Product Title & Value Proposition
**Title:** Genie 4 Mastery Pack: Enterprise LLM Integration Kit
**Value Proposition:** Stop treating LLMs as "chatbots" and start treating them as high-performance microservices. This kit provides the battle-tested patterns, error-handling logic, and architectural scaffolding required to ship robust, production-grade applications using the Genie 4 API. Save 40+ hours of R&D and avoid the "prototype-to-production" stability gap.

---

## 2. Quick Start & Core Concepts

### Core Syntax Reference
| Operation | Command/Pattern | Purpose |
| :--- | :--- | :--- |
| **Auth** | `genie-cli auth --key <TOKEN>` | Scoped persistent credential management. |
| **Stream** | `genie.stream(task, cb)` | Minimizes Time-To-First-Token (TTFT). |
| **Context** | `genie.ctx.inject(payload)` | RAG-optimized injection schema. |
| **Retry** | `genie.retry(strategy=exp)` | Exponential backoff for rate-limit resilience. |

---

## 3. Production Code Patterns & Architecture Examples

### The "Resilient Orchestrator" Pattern
Never call an LLM directly from a request thread. Use this background worker pattern to manage retries and state.

```typescript
// patterns/orchestrator.ts
import { GenieClient } from '@genie/sdk';

const genie = new GenieClient({ timeout: 5000, maxRetries: 3 });

export async function processTask(input: string) {
  try {
    const result = await genie.completion({
      model: 'genie-4-pro',
      prompt: input,
      // Always define strict schema for output
      response_format: { type: 'json_object' }
    });
    
    return JSON.parse(result.content);
  } catch (err) {
    // Log with context, don't just throw
    console.error(`[GenieError] Task failed: ${err.code}. Check dashboard.`);
    throw new WorkflowRetryError(err);
  }
}
```

### Prompt Template Engine (Structured)
```markdown
# Role: Senior Code Auditor
# Objective: Identify security vulnerabilities
# Context: {{context}}
# Input: {{code_snippet}}
# Constraint: Only output JSON containing { "risk": "high/med/low", "reason": "...", "fix": "..." }
```

---

## 4. Common Anti-Patterns & Gotchas

*   **The "Context Bloat" Trap:** Do not pass the entire conversation history in every API call. Use a **sliding window buffer** or a vector database to fetch only the relevant `K` chunks.
*   **Prompt Injection Blindness:** Never trust user input to define system roles. Always wrap user input in clear delimiters (`### START USER INPUT ###`).
*   **The "Silent Failure" Anti-Pattern:** Treating a 429 (Rate Limit) as a code crash. Implement a jittered backoff strategy; a 429 is a temporary delay, not a termination signal.
*   **Ignoring Token Usage:** Not tracking usage per-request. Always log `usage.total_tokens` to your telemetry (Datadog/NewRelic) for accurate ROI and cost forecasting.

---

## 5. Performance & Optimization Tips

1.  **Request Parallelization:** Use `Promise.allSettled` to execute multi-task prompts, but implement a request-limiter (p-limit) to avoid saturating your concurrency quota.
2.  **Edge Caching:** Cache deterministic prompts (e.g., "Summarize this standard TOC") at the CDN level using standard HTTP `Cache-Control` headers.
3.  **TTFT Optimization:** If the client needs immediate feedback, prioritize **Streaming Mode**. The perceived performance is 3x faster than waiting for a full JSON payload.
4.  **Model Selection:** Route "Complex Logic" tasks to `genie-4-pro` and "Text Formatting" tasks to `genie-4-turbo` to reduce costs by up to 60%.

---

## 6. Commercial License & Attribution Summary

*   **Usage:** This kit is licensed under the **MicroCorp Proprietary License**.
*   **Permissions:** You may incorporate the provided code patterns into your commercial SaaS applications, internal tooling, and client deliverables.
*   **Restrictions:** You may **not** redistribute, resell, or publicly host this document as a standalone product.
*   **Attribution:** While not required in your production code, inclusion of `// Genie 4 Patterns: MicroCorp AI` in your documentation is appreciated.

*Need custom architecture consulting? Reach out to the Engineering Division at `dev-tooling@microcorp.ai`.*