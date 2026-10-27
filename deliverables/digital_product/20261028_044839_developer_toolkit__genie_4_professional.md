# Genie 4 Professional Suite: Developer Reference & Architecture Kit

**Maximize your AI-integrated development lifecycle with the Genie 4 Professional Suite. This toolkit provides the architectural scaffolding, production-grade patterns, and performance optimizations required to build enterprise-scale LLM applications.**

---

## 1. Product Title & Value Proposition
**Title:** Genie 4 Professional Suite: Advanced Architecture & Integration Kit
**Value Proposition:** Stop wrestling with unpredictable LLM responses. The Genie 4 Suite provides a structured, type-safe, and production-ready framework to integrate Large Language Models into your existing tech stack with reliability, observability, and modularity at its core.

---

## 2. Quick Start & Core Concepts

| Concept | Definition | Key Syntax |
| :--- | :--- | :--- |
| **Provider Client** | The base connection layer. | `Genie.connect({ provider: 'claude-3.5', key: env.API_KEY })` |
| **Context Window** | Managing token limits and memory. | `session.setWindow(8192)` |
| **System Persona** | Defines role and behavior constraints. | `persona.inject('SYSTEM_ROLE_EXPERT')` |
| **Structured Output** | Enforcing JSON schemas. | `res.schema(ZodSchema)` |

---

## 3. Production Code Patterns & Architecture Examples

### A. The "Chain-of-Thought" Repository Pattern
This pattern decouples the prompting logic from your business logic, ensuring your prompts are version-controlled and testable.

```typescript
// services/genie.service.ts
import { GenieClient } from '@genie/sdk';

export class AgentOrchestrator {
  private client = new GenieClient();

  async executeTask(prompt: string, schema: any) {
    return await this.client.chat({
      messages: [
        { role: 'system', content: 'You are a technical architect.' },
        { role: 'user', content: prompt }
      ],
      responseFormat: { type: 'json_object', schema },
      temperature: 0.2 // Low temperature for deterministic output
    });
  }
}
```

### B. Streaming Response Handler (Frontend)
Use this React hook pattern for responsive, real-time UI updates.

```tsx
// hooks/useGenieStream.ts
export const useGenieStream = () => {
  const [stream, setStream] = useState('');

  const startStream = async (query: string) => {
    const reader = await fetch('/api/genie/stream', {
      method: 'POST',
      body: JSON.stringify({ query })
    }).then(res => res.body?.getReader());

    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      setStream(prev => prev + new TextDecoder().decode(value));
    }
  };
  return { stream, startStream };
};
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **Prompt Injection Vulnerability:** Never inject raw user input directly into system prompts. Always sanitize or use a "delimiter" pattern (e.g., `### USER_INPUT ###`).
*   **The "Infinite Loop" Agent:** Avoid autonomous agents without a clear step-limiter. Always implement a `max_steps` constraint to prevent recursive model execution.
*   **Hardcoded API Keys:** Never expose `GENIE_KEY` in client-side code. Use an intermediary API route to proxy requests securely.
*   **Over-Reliance on Memory:** Large context windows consume significant tokens. Practice "Context Pruning" by summarizing previous messages rather than passing the entire history.

---

## 5. Performance & Optimization Tips

1.  **Semantic Caching:** Before hitting the Genie 4 API, hash the prompt and check a Redis instance to see if a similar query was answered recently.
2.  **Streaming over JSON:** Always prefer `stream` mode for high-latency tasks to maintain a high perceived performance (Perceived Speed).
3.  **Tiered Model Selection:** Route simple tasks (e.g., formatting) to `Genie-Mini` and complex logic/reasoning to `Genie-4-Ultra` to save 60% on token costs.
4.  **Batching:** When processing bulk data, use batch API endpoints to receive higher throughput and discounted pricing.

---

## 6. Commercial License & Attribution Summary

**License:** MIT Open Source License (Modified for Enterprise).
**Attribution:** This toolkit is provided by **MicroCorp AI**. 

*   **Commercial Use:** You are permitted to integrate this code into commercial, proprietary products.
*   **Redistribution:** You may modify and redistribute this toolkit provided the original comment headers remain intact.
*   **Warranty:** This code is provided "as is." MicroCorp AI is not responsible for token usage costs resulting from implementation bugs.

---
*Built by The Agency Engineering Division. Pixel-perfect architectures for the AI-first era.*