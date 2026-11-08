# Developer Toolkit: Person of Interest (POI)
## Architecture & Implementation Reference for Entity Tracking Systems

### 1. Product Title & Value Proposition
**Title:** Person of Interest (POI) Tracking & Resolution Architecture Kit  
**Value Prop:** A battle-tested blueprint for building high-concurrency entity resolution systems. Stop reinventing the wheel for tracking, state-merging, and cross-reference mapping. This kit provides the patterns, schemas, and performance optimizations required to handle millions of entity events with sub-millisecond lookups.

---

### 2. Quick Start & Core Concepts
The POI pattern relies on an immutable event-stream architecture and a materialized "Golden Record" state.

| Concept | Definition | Primary Tooling |
| :--- | :--- | :--- |
| **Entity ID** | Unique, stable identifier for a real-world object. | UUID v7 / KSUID |
| **Alias Map** | Multi-key lookup table linking transient IDs (IP, email) to Entity ID. | Redis Hash / Bloom Filter |
| **Resolution** | The process of merging two entities based on overlapping signals. | Deterministic Rules Engine |
| **Event Stream** | The audit trail of how an entity profile evolved over time. | Kafka / NATS JetStream |

---

### 3. Production Code Patterns & Architecture
The following pattern demonstrates a high-performance **Resolution Service** written in Go, focusing on the "Lookaside Cache" strategy.

```go
// POI Entity Model
type PersonOfInterest struct {
    EntityID  string            `json:"entity_id"`
    Signals   map[string]string `json:"signals"`
    LastSeen  time.Time         `json:"last_seen"`
    Version   int64             `json:"version"`
}

// Resolve identifies if two signal sets belong to the same POI
func Resolve(ctx context.Context, current, incoming Signal) (string, error) {
    // 1. Check Redis Cache for existing Alias
    entityID, err := cache.Get(ctx, incoming.Key)
    if err == nil {
        return entityID, nil
    }

    // 2. Fallback to Database Join (Deterministic Logic)
    entityID, err = db.QueryEntityBySignals(incoming)
    if err != nil {
        return "", fmt.Errorf("lookup failed: %w. Run 'poi sync' to rebuild index.", err)
    }
    
    return entityID, nil
}
```

**Architecture Flow:**
1. **Ingest:** Raw event lands on Kafka.
2. **Resolve:** Service matches signals against the Redis Alias Map.
3. **Merge:** If conflict detected, trigger `ReconcileJob` (Asynchronous).
4. **Update:** Push "Golden Record" update to downstream caches.

---

### 4. Common Anti-Patterns & Gotchas
*   **The "Big Table" Trap:** Do not store full entity metadata in the lookup table. Keep the lookup table strictly for `Transient Key -> EntityID` mapping.
*   **Cascading Writes:** Avoid synchronous database writes for every entity hit. Use a write-behind buffer or a distributed queue to handle high-frequency spikes.
*   **Non-Deterministic Merging:** Avoid "fuzzy" matching on the hot path. If the match confidence is < 95%, flag for human review in a secondary dashboard rather than auto-merging.

---

### 5. Performance & Optimization Tips
*   **Bloom Filters:** Use a Bloom filter in front of your database lookups. If the key isn't in the filter, don't waste an I/O hit on the database.
*   **UUID v7:** Use time-ordered UUIDs to ensure your database indexes remain performant as the POI set grows into the hundreds of millions.
*   **TTL Strategy:** Implement sliding-window TTLs on Alias Maps. If a transient signal (e.g., an IP address) hasn't been seen in 30 days, purge it to keep memory costs predictable.

---

### 6. Commercial License & Attribution Summary

**License: Commercial Developer Use (CDU-1.0)**
*   **Permitted:** You may use this architecture, code snippets, and schema designs in any commercial, proprietary, or open-source software project. 
*   **Prohibited:** You may not resell this kit as a standalone product or redistribute the original source text/markdown files.
*   **Attribution:** No attribution required in your final product code.

*Copyright © 2024 The Agency Engineering Division. All rights reserved. For support, run `poi --help` or contact support@theagency.dev.*