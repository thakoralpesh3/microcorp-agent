# Developer Toolkit: Genie 4 Execution Plan
## The Architect's Blueprint for High-Performance AI Orchestration

Genie 4 is not just an LLM; it is a state-managed, context-aware reasoning engine. This kit provides the battle-tested patterns required to move from "chatting with an API" to "building resilient, deterministic AI systems."

---

## 1. Quick Start & Core Concepts

Stop treating AI calls as isolated events. Treat them as **units of work** within a structured execution graph.

| Concept | Definition | Developer Tooling Strategy |
| :--- | :--- | :--- |
| **Context Window** | The active working memory. | Keep it lean; prune stale tokens via RAG middleware. |
| **Reasoning Chain** | Step-by-step logic nodes. | Enforce JSON-mode output for machine-parsable logic. |
| **The "Genie" Guard** | Input/Output validation. | Use Pydantic/Zod schemas to define strict boundaries. |
| **Stateful Memory** | Long-term interaction state. | Externalize to Redis; keep the prompt-side state stateless. |

---

## 2. Production Code Patterns & Architecture Examples

### A. The "Structured Reasoner" Pattern (Typescript/Node.js)
Avoid raw string prompting. Use functional interfaces to ensure the execution plan is machine-readable.

```typescript
// Define your Execution Plan Schema
interface ExecutionPlan {
  steps: string[];
  rationale: string;
  confidenceScore: number;
}

async function executeGeniePlan(task: string): Promise<ExecutionPlan> {
  const systemPrompt = `You are an expert orchestrator. Output JSON only. 
  Schema: { "steps": string[], "rationale": string, "confidenceScore": number }`;
  
  const response = await genie.call({
    model: 'genie-4-pro',
    messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: task }],
    response_format: { type: 'json_object' }
  });

  return JSON.parse(response.content);
}
```

### B. The "Fallback Orchestrator" Pattern
Never let a single failure take down the pipeline. Always implement a deterministic fallback.

```python
def get_intelligent_response(query):
    try:
        return genie.execute(query)
    except GenieRateLimitError:
        # Graceful degradation to a smaller, faster model
        return genie.execute_light(query) 
    except Exception as e:
        log.error(f"Execution failed: {e}. Fix: Check API key rotations.")
        raise
```

---

## 3. Common Anti-Patterns & Gotchas

*   **The "Infinite Loop" Prompt**: Asking the AI to "keep refining until perfect" without a max-iteration counter. 
    *   *Fix*: Hard-cap the iteration count in your `System Prompt` (e.g., `max_iterations: 3`).
*   **Context Bloat**: Including every previous turn in the history.
    *   *Fix*: Implement a "Rolling Summary" buffer. Keep only the last 5 turns + the initial system instructions.
*   **Ignoring Exit Codes**: Treating AI success as binary (200 OK).
    *   *Fix*: Always inspect the `finish_reason` in the metadata. If it's `length` or `content_filter`, the process is effectively a failure.

---

## 4. Performance & Optimization Tips

1.  **Warm-Up Latency**: Use `keep-alive` headers or persistent connections to avoid TLS handshake overhead on every request.
2.  **Streaming vs. Batching**: Use Server-Sent Events (SSE) for UI responsiveness, but batch background tasks (RAG indexing/summarization) into asynchronous workers.
3.  **Token Caching**: If your system prompt is >500 tokens, use vendor-specific caching features. This reduces input costs by 90% for subsequent calls in a session.
4.  **The 100ms Rule**: If a request exceeds 100ms startup time, move it out of the critical path (UI render) into a background task (bullmq, temporal, or celery).

---

## 5. Commercial License & Attribution Summary

**Usage Rights:**
*   This architecture kit is licensed under **MIT**. You may modify, redistribute, and integrate these patterns into commercial enterprise software without attribution requirements.
*   *Caveat*: You are responsible for testing the output of your AI pipeline. We provide the *pattern*, not the *accuracy*.

**Attribution:**
*   Crafted by **The Agency Engineering Division**. 
*   If you found this useful, cite this repository in your `README.md` or `ARCHITECTURE.md` file as a reference for your AI pipeline design.

---

*Need help deploying this at scale? Run `genie-tool --help` to see how our CLI automates your deployment pipelines.*