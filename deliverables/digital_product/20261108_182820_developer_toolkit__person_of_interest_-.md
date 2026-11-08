# Developer Toolkit: Person of Interest (PoI)

## 1. Product Title & Value Proposition
**Title:** The "Person of Interest" (PoI) Architecture Pattern Kit  
**Value Prop:** A robust, observable, and decoupled architectural pattern for tracking cross-service entity lifecycles. Stop leaking state through your monolith and start using a formal `PoI` registry to manage transient entity tracking, audit trails, and multi-service context propagation. 

This kit provides the structural blueprints to implement a "Person of Interest" system that ensures data consistency, observability, and compliance in high-velocity distributed systems.

---

## 2. Quick Start & Core Concepts

The `PoI` pattern centers on a **Global Context Object** that flows through your stack. It serves as the single source of truth for an entity's status, risk score, and telemetry.

### Core Interface Table
| Component | Responsibility | Pattern |
| :--- | :--- | :--- |
| **PoI Registry** | Tracks entity lifecycle state | Singleton / Sidecar |
| **Context Envelope** | Serialized transit object | Header / Metadata |
| **Status Stream** | Event notification bus | Pub/Sub |
| **TTL Monitor** | Lifecycle expiration | Background Job |

---

## 3. Production Code Patterns & Architecture

### The PoI Envelope (Golang Implementation)
Use this structure to propagate context across microservices.

```go
// poi.go
type PersonOfInterest struct {
    EntityID   string    `json:"entity_id"`
    Priority   int       `json:"priority"` // 1-5
    Metadata   map[string]string `json:"metadata"`
    ExpiresAt  time.Time `json:"expires_at"`
}

// ExtractPoI pulls the envelope from the context or request headers
func ExtractPoI(r *http.Request) (*PersonOfInterest, error) {
    val := r.Header.Get("X-PoI-Envelope")
    if val == "" {
        return nil, fmt.Errorf("missing PoI envelope: run `poi init` or check ingress middleware")
    }
    // ... deserialization logic
    return poi, nil
}
```

### Middleware Integration Pattern
```javascript
// middleware.js
const injectPoI = (req, res, next) => {
    const poi = req.headers['x-poi-envelope'];
    if (!poi) {
        // Fail Fast: Do not allow untracked entities in sensitive routes
        return res.status(401).json({ 
            error: "PoI Context missing", 
            fix: "Ensure upstream service attaches X-PoI-Envelope header." 
        });
    }
    req.poi = JSON.parse(poi);
    next();
};
```

---

## 4. Common Anti-Patterns & Gotchas

*   **The "Context Dump" Anti-Pattern:** Including full database objects inside the PoI envelope. 
    *   *Fix:* Keep the PoI envelope to **< 4KB**. Store only the Entity ID and state flags; use the ID to fetch full details from a cache (Redis).
*   **The Orphaned State:** Updating an entity's status in one service but failing to update the PoI registry.
    *   *Fix:* Use transactional outbox patterns. If the PoI registry isn't updated, the event isn't committed.
*   **Silent Failures:** Ignoring a missing PoI header in dev environments.
    *   *Fix:* Implement a `strict-mode` flag that errors out if headers are missing during integration testing.

---

## 5. Performance & Optimization Tips

1.  **Lazy Resolution:** Don't hydrate the full PoI profile unless the specific code path requires it. Use a `PoI-Light` header for basic routing and `PoI-Full` for resource-heavy operations.
2.  **Zero-Network Path:** If you are within the same cluster, pass the PoI object via shared memory or local cache instead of full serialization/deserialization cycles.
3.  **Circuit Breaking:** If the PoI Registry service slows down, use a fallback local cache for entity status. A slow PoI lookup should never tank the user's request.

---

## 6. Commercial License & Attribution Summary

*   **License:** MIT License. You are free to integrate this code into proprietary, commercial, or open-source software.
*   **Attribution:** While not required, an attribution line in your `README.md` or `ABOUT.md` is appreciated: 
    *   *"PoI Architecture Pattern implemented using the MicroCorp AI Developer Toolkit."*
*   **Warranty:** Provided "as-is". The Engineering Division of The Agency maintains that high-quality code is a result of testing, not just documentation. **Always write unit tests for your header parsing logic.**

***

*Need support?*  
*Run `poi --version` to check your build.*  
*Documentation index: `docs.microcorp.ai/poi`*