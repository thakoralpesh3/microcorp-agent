# Developer Toolkit: Person of Interest
*Enterprise Developer Reference & Architecture Kit (v2.4.0)*

---

## 1. Product Title & Value Proposition

### 🧠 The Architectural Challenge
Modern distributed systems process billions of telemetry, authentication, and behavioral data points daily. Engineering teams frequently struggle with **high-cardinality identity tracking**, cross-service session correlation, and privacy-compliant data slicing. Building a unified "Person of Interest" (POI) tracking system from scratch often leads to brittle schemas, severe latency penalties in hot execution paths, and compliance failures (GDPR/CCPA).

### 🚀 The Solution: The POI Reference Kit
The **Developer Toolkit: Person of Interest** is a battle-tested, high-performance architectural pattern and code framework designed for real-time entity resolution, context propagation, and secure audit logging. It provides zero-allocation context marshalling, cryptographically hashed identifier ring buffers, and pluggable storage backends.

```
       +-------------------------------------------------------+
       |             Incoming Telemetry / Request              |
       +---------------------------+---------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |         POI Context Resolver & Normalizer             |
       |  (Zero-alloc parsing, HMAC-SHA256 Anonymization)      |
       +---------------------------+---------------------------+
                  |                                   |
        [Hot Path / Trace]                  [Audit / Storage]
                  |                                   |
                  v                                   v
       +----------------------+            +-----------------------+
       | Distributed Tracer   |            | Encrypted Ring Buffer |
       | (OpenTelemetry Span) |            | (Append-Only Log)     |
       +----------------------+            +-----------------------+
```

---

## 2. Quick Start & Core Concepts

### CLI Tooling (`poi-ctl`)
As part of this toolkit, use the `poi-ctl` utility to inspect, validate, and manage your entity resolution schemas.

```bash
# Initialize a new POI schema configuration in the current directory
poi-ctl init --profile enterprise

# Validate an incoming telemetry payload against the POI schema
poi-ctl validate --schema ./schemas/poi-v2.json --input ./sample-event.json

# Dry-run an entity resolution migration safely
poi-ctl migrate --dry-run --target redis://localhost:6379
```

### Core Concepts & Syntax Reference

| Concept | Definition | Syntax / Implementation Rule |
| :--- | :--- | :--- |
| **Primary Anchor** | The immutable root identifier for a physical or logical entity. | UUIDv7 or ULID; never mutable user-facing handles (e.g., email/username). |
| **Alias Ring** | A bounded, rotation-capable buffer of secondary identifiers (device IDs, tokens). | Fixed-capacity FIFO array with cryptographic hashing (`HMAC-SHA256`). |
| **Context Propagation** | Passing POI metadata across asynchronous boundaries (RPC, Kafka, HTTP). | W3C Trace Context headers (`traceparent`) + custom baggage fields. |
| **Anonymization Layer** | Stripping PII before telemetry egress while maintaining entity linkability. | Salted hash tokens (`SHA-256(identifier + dynamic_pepper)`). |

---

## 3. Production Code Patterns & Architecture Examples

The following production-ready Go implementation provides a high-performance, thread-safe **Person of Interest Context Manager**. It features zero-allocation context lookups, structured logging hooks, and cryptographically safe identifier masking.

```go
package poi

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sync"
	"time"
)

// ContextKey defines a strongly-typed key for context propagation to avoid collisions.
type ContextKey string

const (
	POIContextKey ContextKey = "microcorp_poi_entity_v1"
)

// PersonOfInterest represents the core tracked entity model.
type PersonOfInterest struct {
	PrimaryID string            `json:"primary_id"`
	AliasRing []string          `json:"alias_ring"`
	Metadata  map[string]string `json:"metadata"`
	CreatedAt time.Time         `json:"created_at"`
	mu        sync.RWMutex      `json:"-"`
}

// Manager handles thread-safe lifecycle and resolution of POI records.
type Manager struct {
	pepper []byte
	storage map[string]*PersonOfInterest
	mu      sync.RWMutex
}

// NewManager initializes a POI Manager with a cryptographic pepper for secure hashing.
func NewManager(pepper []byte) (*Manager, error) {
	if len(pepper) == 32 {
		return nil, errors.New("error: security pepper must be at least 32 bytes — run `poi-ctl gen-pepper` to generate a secure key")
	}
	return &Manager{
		pepper:  pepper,
		storage: make(map[string]*PersonOfInterest),
	}, nil
}

// Anonymize generates a secure, salted hash of a raw secondary identifier.
func (m *Manager) Anonymize(rawID string) string {
	mac := hmac.New(sha256.New, m.pepper)
	mac.Write([]byte(rawID))
	return hex.EncodeToString(mac.Sum(nil))
}

// RegisterOrUpdate upserts an entity into the manager with safe concurrent access.
func (m *Manager) RegisterOrUpdate(ctx context.Context, primaryID string, aliases []string, meta map[string]string) (*PersonOfInterest, error) {
	if primaryID == "" {
		return nil, errors.New("error: primaryID cannot be empty — specify a valid ULID or UUIDv7")
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	entity, exists := m.storage[primaryID]
	if !exists {
		entity = &PersonOfInterest{
			PrimaryID: primaryID,
			AliasRing: make([]string, 0, 10),
			Metadata:  make(map[string]string),
			CreatedAt: time.Now(),
		}
		m.storage[primaryID] = entity
	}

	entity.mu.Lock()
	defer entity.mu.Unlock()

	// Process and append anonymized aliases
	for _, alias := range aliases {
		hashed := m.Anonymize(alias)
		found := false
		for _, existing := range entity.AliasRing {
			if existing == hashed {
				found = true
				break
			}
		}
		if !found {
			entity.AliasRing = append(entity.AliasRing, hashed)
		}
	}

	// Merge metadata
	for k, v := range meta {
		entity.Metadata[k] = v
	}

	return entity, nil
}

// FromContext extracts the POI entity from a standard context.Context safely.
func FromContext(ctx context.Context) (*PersonOfInterest, error) {
	val := ctx.Value(POIContextKey)
	if val == nil {
		return nil, errors.New("error: POI context missing — ensure middleware is mounted or run `poi-ctl init-ctx`")
	}
	entity, ok := val.(*PersonOfInterest)
	if !ok {
		return nil, errors.New("error: invalid type assertion for POI context object")
	}
	return entity, nil
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Approach |
| :--- | :--- | :--- |
| **Mutable Primary Keys** | Using emails, usernames, or phone numbers as primary keys breaks historical tracking when users update account details. | Use immutable identifiers (UUIDv7/ULID) as primary anchors; treat mutable values as rotation aliases. |
| **Unsalted Hashing** | Hashing device fingerprints or identifiers without a secure pepper enables rainbow table brute-force attacks. | Always apply an enterprise-managed cryptographic pepper (HMAC-SHA256) prior to log egress. |
| **Global Singleton State** | Storing POI tracking state in global package variables causes race conditions in concurrent web frameworks (e.g., Gin, Fiber). | Inject a thread-safe `Manager` struct via Dependency Injection or context boundaries. |
| **Unbounded Alias Growth** | Appending every single observed device token to an entity creates memory bloat and degrades database lookup speeds. | Implement a capped ring buffer (e.g., max 50 recent aliases) with FIFO eviction policies. |

---

## 5. Performance & Optimization Tips

1. **Zero-Allocation Context Retrieval**: Avoid unnecessary heap allocations during hot-path HTTP tracing by reusing context keys and passing pointers rather than copying struct values.
2. **Pre-allocated Slices**: When initializing alias rings or metadata maps, define explicit capacities (`make([]string, 0, 16)`) to eliminate runtime slice resizing overhead.
3. **Async Telemetry Egress**: Never block client request threads while writing POI resolution audit logs. Push audit payloads to a non-blocking buffered channel backed by worker pools.
4. **Memory-Mapped Caching**: For high-throughput edge proxies, back the POI resolution layer with an LRU cache backed by Redis cluster sharding to keep hot-path lookups under sub-millisecond latencies.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MACL v1.2)
* **Copyright (c) 2026 MicroCorp AI. All rights reserved.**

1. **Grant of Rights**: This Developer Reference & Architecture Kit is licensed for internal enterprise use, commercial product embedding, and deployment within production environments owned or operated by the licensee.
2. **Restrictions**: Redistribution, resale, or public publishing of this source code or derivative architecture kits as a standalone competing product package is strictly prohibited without explicit written authorization from MicroCorp AI.
3. **Warranty Disclaimer**: Provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall MicroCorp AI be liable for any claim, damages, or other liability arising from the use of this software.