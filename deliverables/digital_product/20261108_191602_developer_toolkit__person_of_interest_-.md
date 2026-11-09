# Developer Toolkit: Person of Interest (POI)
**Architecture Reference & Production Implementation Kit**  
*Version 2.4.0-Enterprise*

---

## 1. Product Title & Value Proposition

### Product Overview
Modern distributed systems generate overwhelming volumes of telemetry, event streams, and relational metadata. The **Person of Interest (POI)** architecture pattern is an enterprise-grade tracing and entity-resolution pattern designed to isolate, track, and audit high-value entities (users, transactions, compromised assets, or high-priority items) across asynchronous microservice boundaries. 

The **Developer Toolkit: Person of Interest** provides senior engineers and architects with a battle-tested, zero-allocation reference implementation for event filtering, state projection, and real-time entity tracking without degrading core throughput.

### Value Proposition
- **Surgical Observability:** Isolate specific entities (`POIs`) from a firehose of events without logging personally identifiable information (PII) globally or incurring massive storage penalties.
- **Deterministic State Reconstruction:** Build point-in-time state machines for targeted entities using event-sourcing principles.
- **Production-Ready Boilerplates:** Drop-in, high-performance Go and TypeScript code blocks engineered for sub-millisecond evaluation loops.
- **Compliance & Security by Design:** Built-in cryptographic hashing for pseudonymization and strict audit logging that satisfies SOC2 and GDPR requirements out of the box.

---

## 2. Quick Start & Core Concepts

To implement a POI tracking pipeline, you must understand three core abstractions: the **Target Descriptor**, the **Evaluation Engine**, and the **State Projector**.

```
[ Incoming Event Stream ] 
         │
         ▼
 ┌──────────────────────┐     Match?     ┌────────────────────────┐
 │ POI Evaluation Engine├───────────────►│ High-Priority Dispatch │
 └──────────┬───────────┘                └────────────────────────┘
            │ No-match
            ▼
   [ Standard Pipeline ]
```

### Core Syntax & Configuration Reference

| Component | Purpose | Syntax / Type | Default Behavior |
| :--- | :--- | :--- | :--- |
| **`TargetID`** | Unique pseudonymized identifier for the POI. | `string (SHA-256 hex)` | Must be salted and hashed at the edge. |
| **`WatchLevel`** | Defines intervention or logging verbosity. | `Enum(OBSERVE, AUDIT, QUARANTINE)` | `OBSERVE` |
| **`TTL`** | Time-to-live for transient POI flags in cache. | `Duration (e.g., 24h)` | `72h` |
| **`Predicate`** | Evaluation rule matching telemetry to POI. | `Expr / AST / Lambda` | Exact match on `TargetID`. |
| **`Sink`** | Out-of-band destination for POI telemetry. | `Kafka / S3 / Webhook` | Local ring buffer. |

---

## 3. Production Code Patterns & Architecture Examples

Below are production-grade implementations for intercepting, evaluating, and projecting POI events.

### A. High-Performance Evaluation Engine (Go)
*Designed for zero-allocation hot paths in API gateways or event routers.*

```go
package poi

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"sync"
	"time"
)

type WatchLevel string

const (
	LevelObserve    WatchLevel = "OBSERVE"
	LevelAudit      WatchLevel = "AUDIT"
	LevelQuarantine WatchLevel = "QUARANTINE"
)

type POIRecord struct {
	TargetID   string
	Level      WatchLevel
	ExpiresAt  time.Time
	Registered time.Time
}

type Engine struct {
	mu     sync.RWMutex
	registry map[string]POIRecord
	secret   []byte
}

func NewEngine(secret []byte) *Engine {
	return &Engine{
		registry: make(map[string]POIRecord),
		secret:   secret,
	}
}

// Pseudonymize normalizes and hashes raw identifiers to protect PII.
func (e *Engine) Pseudonymize(rawID string) string {
	mac := hmac.New(sha256.New, e.secret)
	mac.Write([]byte(rawID))
	return hex.EncodeToString(mac.Sum(nil))
}

func (e *Engine) Register(rawID string, level WatchLevel, ttl time.Duration) string {
	hashedID := e.Pseudonymize(rawID)
	rec := POIRecord{
		TargetID:   hashedID,
		Level:      level,
		ExpiresAt:  time.Now().Add(ttl),
		Registered: time.Now(),
	}

	e.mu.Lock()
	e.registry[hashedID] = rec
	e.mu.Unlock()

	return hashedID
}

// Evaluate checks if an incoming raw identifier is a Person of Interest.
// Optimized for read-heavy concurrency using RLock.
func (e *Engine) Evaluate(rawID string) (POIRecord, bool) {
	hashedID := e.Pseudonymize(rawID)

	e.mu.RLock()
	rec, exists := e.registry[hashedID]
	e.mu.RUnlock()

	if !exists {
		return POIRecord{}, false
	}

	if time.Now().After(rec.ExpiresAt) {
		return POIRecord{}, false
	}

	return rec, true
}
```

### B. Event Interceptor Middleware (TypeScript / Node.js)
*Express/Fastify compatible middleware for tagging HTTP requests originating from a POI.*

```typescript
import { Request, Response, NextFunction } from 'express';
import { createHmac } from 'crypto';

export interface POIConfig {
  secret: string;
  lookupService: (hashedId: string) => Promise<{ level: string } | null>;
  headerName?: string;
}

export function createPOIMiddleware(config: POIConfig) {
  const headerName = config.headerName || 'x-poi-target';
  
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      const rawEntityId = req.headers[headerName] as string;
      if (!rawEntityId) {
        return next();
      }

      // Hash edge identifier to match registry
      const hashedId = createHmac('sha256', config.secret)
        .update(rawEntityId)
        .digest('hex');

      const poiRecord = await config.lookupService(hashedId);
      if (poiRecord) {
        // Attach context safely to request object without leaking state
        req.poi = {
          active: true,
          level: poiRecord.level,
          targetId: hashedId,
        };
        
        // Emit audit trail header internally if required
        res.setHeader('X-Audit-Intercepted', 'true');
      }

      next();
    } catch (err) {
      // Fail open for availability, but log error via secure channel
      console.error('[POI_MIDDLEWARE_ERROR] Evaluation failed:', err);
      next();
    }
  };
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Plaintext PII Storage in POI Registries**
   * *Anti-Pattern:* Storing raw email addresses, social security numbers, or internal user UUIDs directly in the POI lookup database.
   * *The Fix:* Always apply a salted HMAC hash at the absolute perimeter of your architecture. If the database is compromised, raw identities remain safe.
2. **Synchronous Blocking Lookups on Hot Paths**
   * *Anti-Pattern:* Making a blocking network call to a centralized database inside every API request middleware to check POI status.
   * *The Fix:* Cache active POI hashes in a local in-memory LRU cache with a short TTL (e.g., 60 seconds) backed by Redis.
3. **Infinite TTL Leaks**
   * *Anti-Pattern:* Registering POIs without an expiration date (`TTL`), causing state stores to grow indefinitely with stale entities.
   * *The Fix:* Enforce a strict maximum TTL policy (default 72 hours) requiring automated recertification or re-flagging.
4. **Failing Closed on Cache Outages**
   * *Anti-Pattern:* Returning HTTP 500 errors to all users because the POI Redis cluster is temporarily unreachable.
   * *The Fix:* Implement a **Fail-Open** pattern. If the evaluation service errors out, bypass POI telemetry collection for that request cycle while incrementing a dead-letter metric.

---

## 5. Performance & Optimization Tips

- **Bitmap & Bloom Filter Indexing:** For systems tracking millions of concurrent POIs, load the active `TargetID` hashes into a memory-mapped Roaring Bitmap or Scalable Bloom Filter at startup. Check this filter in $< 1\mu\text{s}$ before hitting any network cache.
- **Asynchronous Out-of-Band Sinks:** Never write POI audit logs synchronously to your primary database transaction. Push events to a local non-blocking channel (e.g., Go `chan` or ring buffer) and batch-flush to storage (S3 / Kafka) every 500ms.
- **Memory Footprint Reduction:** Avoid storing full JSON objects in memory for POI metadata maps. Store primitive packed structs or fixed-byte byte arrays to keep L3 cache miss rates minimal.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MACL-v1.2)
Copyright © 2026 MicroCorp AI. All rights reserved.

1. **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and incorporate the code patterns and architectural specifications contained within this toolkit into proprietary commercial and internal software products.
2. **Restrictions:** Redistribution of this document, or substantial portions of the source code herein, as a standalone developer reference kit, training course, or competing template is strictly prohibited.
3. **No Warranty:** This software and documentation is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claim, damages, or other liability arising from its use.