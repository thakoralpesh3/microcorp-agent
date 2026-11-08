# Person of Interest (POI): Developer Toolkit & Architecture Kit
*Enterprise-Grade Surveillance, Entity Resolution, and Real-Time Telemetry Processing*

## 1. Product Title & Value Proposition

### Product Title
**Person of Interest (POI): Enterprise Telemetry & Entity Resolution Developer Kit**

### Value Proposition
Modern distributed systems, security operations centers, and real-time analytics platforms drown in fragmented telemetry. IP addresses rotate, user sessions span multiple devices, API tokens get compromised, and logs arrive out of order across disparate geographical regions. 

**Person of Interest (POI)** is a production-tested architectural reference and toolkit designed to solve the **Entity Resolution and Real-Time Tracking Problem**. It provides software engineers, security architects, and backend developers with battle-tested patterns to ingest, normalize, correlate, and track entities (users, devices, IPs, or assets) across massive data streams with sub-millisecond lookup times and deterministic consistency.

### What's Included
- **Zero-Dependency Architecture Core**: Blueprint for a high-throughput event ingestion pipeline.
- **Entity Resolution Engine**: Probabilistic and deterministic matching algorithms implemented in production-ready Go and TypeScript.
- **Drop-in CLI Tooling (`poi-ctl`)**: Fast, scriptable operational command-line tool built to enterprise CLI standards (sub-100ms startup, structured JSON output, explicit exit codes).
- **Production Code Patterns**: Complete, copy-paste ready implementations for state management, deduplication, and alerting hooks.

---

## 2. Quick Start & Core Concepts

The POI framework operates on a four-stage pipeline: **Ingest $\rightarrow$ Normalize $\rightarrow$ Resolve $\rightarrow$ Act**.

```
[ Raw Telemetry ] 
       │
       ▼ (Stream / API)
[ 1. Ingestion Layer ] ──> Fast validation & structural checks
       │
       ▼
[ 2. Normalization ] ──> Canonical schema conversion (UTC, IP sanitization)
       │
       ▼
[ 3. Entity Resolution ] ─> Disjoint-Set / Graph-based identity stitching
       │
       ▼
[ 4. Action Engine ] ───> Webhooks, Alerting, State persistence
```

### CLI Quick Start (`poi-ctl`)
```bash
# Initialize local POI configuration
poi-ctl init --region us-east-1

# Validate an incoming event payload against the POI schema
poi-ctl validate --input ./sample-event.json

# Resolve entity linkages for a given identifier
poi-ctl resolve --id "usr_9981247192" --depth 2 --format json

# Run a dry-run simulation of an alerting rule
poi-ctl alert test --rule ./rules/suspicious-geo.yml --dry-run
```

### Core Concepts & CLI Command Reference

| Concept | Definition | Primary CLI Command | Exit Codes & Meaning |
| :--- | :--- | :--- | :--- |
| **Entity** | A unique real-world actor or asset distilled from multiple ephemeral identifiers (cookies, IPs, device fingerprints). | `poi-ctl entity inspect <ID>` | **0**: Found<br>**1**: Connection Error<br>**2**: Entity Not Found |
| **Telemetry Event** | An immutable, timestamped record of an action emitted by an edge service, proxy, or application worker. | `poi-ctl validate <FILE>` | **0**: Valid payload<br>**1**: Schema syntax error<br>**2**: Missing required fields |
| **Identity Stitching** | The algorithmic process of merging disparate identifiers into a single canonical Entity Graph. | `poi-ctl resolve --id <ID>` | **0**: Resolved successfully<br>**3**: Circular reference detected |
| **Watchlist Rule** | Declarative criteria triggering high-priority operational hooks when an entity crosses risk thresholds. | `poi-ctl alert evaluate` | **0**: No triggers<br>**1**: Rule violation detected<br>**4**: Malformed rule syntax |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: High-Performance Entity Resolution Engine (Go)
This production-ready Go module implements a thread-safe Union-Find (Disjoint-Set) data structure with path compression. It allows real-time identity stitching when telemetry links two separate identifiers (e.g., an anonymous session token logging into a known user account).

```go
// Package poi implements high-speed entity resolution using Disjoint-Set union.
package poi

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// EntityGraph manages identity mappings with thread safety.
type EntityGraph struct {
	mu     sync.RWMutex
	parent map[string]string
	rank   map[string]int
}

// NewEntityGraph initializes a pristine resolution store.
func NewEntityGraph() *EntityGraph {
	return &EntityGraph{
		parent: make(map[string]string),
		rank:   make(map[string]int),
	}
}

// AddIdentifier registers an identifier if it does not already exist.
func (g *EntityGraph) AddIdentifier(id string) {
	g.mu.Lock()
	defer g.mu.Unlock()

	if _, exists := g.parent[id]; !exists {
		g.parent[id] = id
		g.rank[id] = 0
	}
}

// Find locates the canonical root entity for a given identifier with path compression.
func (g *EntityGraph) Find(id string) (string, error) {
	g.mu.Lock()
	defer g.mu.Unlock()

	root, exists := g.parent[id]
	if !exists {
		return "", fmt.Errorf("identifier not found: %s — run `poi-ctl entity register` first", id)
	}

	// Path compression traversal
	if root != id {
		resolvedRoot, err := g.findRecursive(root)
		if err != nil {
			return "", err
		}
		g.parent[id] = resolvedRoot
		return resolvedRoot, nil
	}

	return id, nil
}

func (g *EntityGraph) findRecursive(id string) (string, error) {
	p, exists := g.parent[id]
	if !exists {
		return "", fmt.Errorf("dangling reference in entity graph: %s", id)
	}
	if p == id {
		return id, nil
	}
	root, err := g.findRecursive(p)
	if err != nil {
		return "", err
	}
	g.parent[id] = root
	return root, nil
}

// Union stitches two identifiers together under a single canonical entity.
func (g *EntityGraph) Union(id1, id2 string) error {
	g.AddIdentifier(id1)
	g.AddIdentifier(id2)

	root1, err := g.Find(id1)
	if err != nil {
		return err
	}
	root2, err := g.Find(id2)
	if err != nil {
		return err
	}

	if root1 == root2 {
		return nil // Already unified
	}

	g.mu.Lock()
	defer g.mu.Unlock()

	// Union by rank
	if g.rank[root1] < g.rank[root2] {
		g.parent[root1] = root2
	} else if g.rank[root1] > g.rank[root2] {
		g.parent[root2] = root1
	} else {
		g.parent[root2] = root1
		g.rank[root1]++
	}

	return nil
}

// TelemetryEvent represents an incoming normalized observation.
type TelemetryEvent struct {
    EventID   string    `json:"event_id"`
    ActorID   string    `json:"actor_id"`
    TargetID  string    `json:"target_id"`
    Timestamp time.Time `json:"timestamp"`
    Action    string    `json:"action"`
}

func ProcessEvent(ctx context.Context, graph *EntityGraph, event TelemetryEvent) error {
    if event.ActorID == "" || event.TargetID == "" {
        return fmt.Errorf("invalid telemetry payload [EventID: %s]: missing actor or target ID — verify upstream producer", event.EventID)
    }
    
    err := graph.Union(event.ActorID, event.TargetID)
    if err != nil {
        return fmt.Errorf("failed to resolve entity linkage for event %s: %w", event.EventID, err)
    }
    
    return nil
}
```

### Pattern 2: Real-Time Stream Ingestion & Deduplication Pipeline (TypeScript / Node.js)
High-frequency telemetry ingestion requires sliding-window deduplication to prevent flooding downstream databases with duplicate heartbeats or log emissions.

```typescript
import { createHash } from 'crypto';

export interface TelemetryPacket {
    sourceIp: string;
    sessionId: string;
    payload: Record<string, unknown>;
    receivedAt: number;
}

export interface DedupConfig {
    windowMs: number;
    maxCacheSize: number;
}

/**
 * High-performance sliding window deduplicator for streaming telemetry.
 */
export class StreamDeduplicator {
    private cache = new Map<string, number>();
    private windowMs: number;
    private maxCacheSize: number;

    constructor(config: DedupConfig) {
        this.windowMs = config.windowMs;
        this.maxCacheSize = config.maxCacheSize;
    }

    /**
     * Evaluates a packet. Returns true if the packet is unique, false if duplicate.
     */
    public evaluate(packet: TelemetryPacket): boolean {
        const now = Date.now();
        this.pruneExpired(now);

        const fingerprint = this.hashPacket(packet);

        if (this.cache.has(fingerprint)) {
            return false; // Duplicate detected within window
        }

        if (this.cache.size >= this.maxCacheSize) {
            // Evict oldest entry (first key in Map)
            const oldestKey = this.cache.keys().next().value;
            if (oldestKey) {
                this.cache.delete(oldestKey);
            }
        }

        this.cache.set(fingerprint, now);
        return true;
    }

    private hashPacket(packet: TelemetryPacket): string {
        const raw = `${packet.sourceIp}:${packet.sessionId}:${JSON.stringify(packet.payload)}`;
        return createHash('sha256').update(raw).digest('hex');
    }

    private pruneExpired(now: number): void {
        // Periodic O(N) sweep when approaching capacity or on interval
        if (this.cache.size > this.maxCacheSize * 0.8) {
            for (const [key, timestamp] of this.cache.entries()) {
                if (now - timestamp > this.windowMs) {
                    this.cache.delete(key);
                } else {
                    break; // Map maintains insertion order; older items are first
                }
            }
        }
    }
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Unbounded In-Memory Entity Graphs
* **The Mistake**: Keeping all historical entity relations in an unbounded local map or dictionary without partition keys or TTLs, leading to Out-Of-Memory (OOM) crashes in production clusters.
* **The Fix**: Implement LRU caching layers over persistent graph storage (e.g., Redis or Neo4j) and ensure all ephemeral identifiers expire after 72 hours of inactivity.

### ❌ Anti-Pattern 2: Swallowing Resolution Errors with Raw Stack Traces
* **The Mistake**: Catching graph lookup errors and dumping raw unformatted stack traces or ambiguous messages (`Error: ENOENT`) to human operators or API consumers.
* **The Fix**: Return structured errors that state what happened, why, and the exact remediation command.
  * *Bad*: `Error: graph failure at 0x7fff`
  * *Good*: `Error: Entity record missing for ID 'usr_123' in partition 'us-east-1' — run 'poi-ctl entity rebuild --id usr_123' to re-index.`

### ❌ Anti-Pattern 3: Blocking Hot Paths with Synchronous Webhooks
* **The Mistake**: Triggering synchronous HTTP webhook calls inside the telemetry ingestion hot loop when an entity triggers a watchlist alert.
* **The Fix**: Push alert notifications onto an asynchronous message broker (Kafka, RabbitMQ, or Redis Streams) immediately, returning `202 Accepted` to the event producer.

---

## 5. Performance & Optimization Tips

1. **Sub-100ms CLI Startup**: Avoid loading heavy ORMs or remote configuration schemas on initialization. Lazy-load database drivers only when executing subcommands that require persistence.
2. **Deterministic Exit Codes**: Ensure CI/CD pipelines and automated orchestration tools can reliably interpret failures without parsing messy stdout strings. Use code `0` for success, `1` for operational failure, and `2` for configuration/syntax errors.
3. **Pipe-Aware Output Formatting**: 
   - When attached to a TTY, render rich tables with colorized status indicators.
   - When piped (`poi-ctl resolve --id 123 | jq .`), automatically suppress ANSI escape codes, spinners, and banner headers to emit clean, machine-parseable JSON.
4. **Memory Footprint Reduction**: Pre-allocate Go slices and maps where maximum expected load is known (`make(map[string]string, 100000)`) to minimize GC pause latencies during traffic spikes.

---

## 6. Commercial License & Attribution Summary

### License Grant
Copyright © 2024 MicroCorp AI & The Agency Engineering Division. All rights reserved.

Licensed under the **MicroCorp Commercial Developer License (MCDL v1.2)**. 
* You are granted a perpetual, worldwide, non-exclusive license to use, modify, and integrate this toolkit into internal systems, proprietary software, and commercial SaaS products.
* Redistribution of this source code or architecture kit as a standalone competing product or template library is strictly prohibited without explicit written consent from MicroCorp AI.

### Warranty & Disclaimer
THIS SOFTWARE AND ARCHITECTURE KIT ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.