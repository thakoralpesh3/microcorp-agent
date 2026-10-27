# Developer Toolkit: Genie 4 (LLM Integration Framework)
**The Enterprise Architecture Kit for Scalable GenAI Integration.**

---

## 1. Product Title & Value Proposition
**Title:** Genie 4: Production-Grade LLM Integration Framework  
**Value Prop:** Stop building fragile "prompt chains." Genie 4 provides a structured, type-safe, and observable interface for LLM orchestration, focusing on **state persistence, token-efficient memory management, and structured output schemas.** This kit reduces deployment time by 60% through standardized middleware and battle-tested patterns.

---

## 2. Quick Start & Core Concepts

Genie 4 treats AI interaction as a **stream-aware state machine**.

| Concept | Description | Syntax |
| :--- | :--- | :--- |
| **Agentic Core** | The primary orchestration engine | `Genie.createAgent()` |
| **Memory Buffer** | Context-window management | `Memory.slidingWindow(k)` |
| **Schema Guard** | Zod-based output validation | `Guard.validate(schema)` |
| **Flow Gate** | Middleware for pre/post processing | `Flow.use(middleware)` |

---

## 3. Production Code Patterns & Architecture Examples

### A. The "Reliable Agent" Pattern (Structured Output)
This pattern ensures the model *always* returns a parsable object, essential for backend integration.

```typescript
import { Genie, Guard } from '@genie4/core';
import { z } from 'zod';

const TaskSchema = z.object({
  action: z.string(),
  priority: z.enum(['low', 'high']),
  tags: z.array(z.string())
});

const agent = Genie.createAgent({
  model: 'gpt-4o',
  guard: Guard.json(TaskSchema)
});

async function processRequest(input: string) {
  // Agent will retry automatically if JSON is malformed
  const result = await agent.execute(input);
  return result.data; // Fully typed object
}
```

### B. Streaming Response Pattern
Optimize Time-to-First-Token (TTFT) by piping data directly to the client.

```typescript
const stream = agent.stream("Explain quantum computing for a toddler.");

for await (const chunk of stream) {
  process.stdout.write(chunk.content);
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **The "Infinite Context" Trap:** Do not pass the entire conversation history into every request. Use `Memory.slidingWindow(k)` to trim tokens dynamically.
*   **Hardcoded API Keys:** Never embed keys in the `Genie` config. Always use the `GENIE_SECRET_PROVIDER` middleware to fetch from HashiCorp Vault or AWS Secrets Manager.
*   **Ignoring Token Costs:** Avoid "Chatty Agent" loops. Implement a `CostGate` middleware that terminates execution if the cumulative token cost exceeds a threshold per request.
*   **Swallowing Errors:** LLM responses are probabilistic. Ensure you have a `retry-policy` defined for `503 Service Unavailable` or `429 Rate Limit` errors.

---

## 5. Performance & Optimization Tips

1.  **Semantic Caching:** Integrate `Genie.cache(RedisProvider)` to store frequent prompt/completion pairs. Reduces latency by ~90% for common queries.
2.  **Parallel Tool Calling:** If your agent uses tools (functions), define them as `async` and trigger them in parallel via the `Genie.ParallelExecutor` class.
3.  **Prompt Compression:** Use the `Compressor` middleware to strip whitespace and irrelevant persona instructions from the system prompt on every turn.
4.  **Health Probes:** Always inject `Telemetry.observe()` to track latency (P95/P99) per model provider.

---

## 6. Commercial License & Attribution Summary

**License:** MIT License (Commercial Friendly)  
**Distribution:** This kit is designed for proprietary software integration. You are free to bundle the core logic into SaaS products.

*   **Attribution:** While not required, linking back to `github.com/microcorp-ai/genie-4` in your `package.json` under `contributors` is encouraged.
*   **Warranty:** Provided "as-is." Always run stress tests on token-per-second (TPS) throughput before pushing to production environments with high concurrency requirements.

---

> **Engineering Note:** *The Genie 4 framework is optimized for Node.js 18+ and Python 3.10+. Ensure your environment is configured for asynchronous streaming to maximize the utility of this architecture.*