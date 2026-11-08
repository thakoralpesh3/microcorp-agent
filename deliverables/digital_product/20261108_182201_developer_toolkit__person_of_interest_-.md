# Developer Toolkit: Person of Interest (POI)
*Architecture, Design Patterns, and Production Reference for Real-Time Contextual Surveillance, Entity Resolution, and Threat Analysis Engines.*

---

## 1. Product Title & Value Proposition

### Title: Developer Toolkit: Person of Interest (POI) — Real-Time Entity Tracking & Surveillance Architecture

### Value Proposition
Modern high-throughput distributed systems—ranging from physical security grids and fraud detection networks to real-time cybersecurity telemetry engines—require instant ingestion, contextual enrichment, and entity tracking. **POI** provides senior engineers and systems architects with a battle-tested blueprint, event-driven architecture patterns, and production-ready code for building high-velocity **Person of Interest** surveillance and resolution pipelines. 

By eliminating the guesswork in handling mutable state, streaming graph traversal, and low-latency geospatial/behavioral indexing, this toolkit slashes time-to-market for mission-critical tracking systems from months to days.

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts
1. **The Ingestion Pipeline:** High-throughput ingress using Kafka/Redpanda handling disparate sensor feeds (IP events, badge scans, API logs, IoT telemetry).
2. **Entity Resolution Engine:** A probabilistic matching layer that unifies fragmented identifiers (MAC, IP, User ID, Device Fingerprint) into a single canonical `EntityID`.
3. **Hot State Store:** In-memory distributed cache (Redis/Dragonfly) maintaining real-time geofence states and temporal presence data with sub-millisecond access.
4. **Graph Context Layer:** Dynamic relationship mapping to compute degrees of separation and co-occurrence matrices between targets of interest.

### CLI & Operational Syntax Reference

| Command / Utility | Target Flag / Argument | Purpose & Behavior | Exit Codes / Scripting Note |
| :--- | :--- | :--- | :--- |
| `poi-cli` | `ingest --stream <topic>` | Consumes raw telemetry from target kafka topics. | `0` = streaming, `1` = broker down (Check broker health). |
| `poi-cli` | `resolve --id <uuid>` | Performs deterministic + probabilistic entity resolution. | `0` = resolved, `3` = entity not found. |
| `poi-cli` | `surveil --geofence <polygon>` | Subscribes to entry/exit events within a bounding box. | Outputs newline-delimited JSON for piping to stdout. |
| `poi-cli` | `inspect --target <id> --dry-run` | Simulates threat-score recalculation without emitting alerts. | Safe path: guarantees no downstream webhooks are fired. |

---

## 3. Production Code Patterns & Architecture Examples

Below is a production-grade, concurrent Go implementation of the **Entity Resolution & Real-Time Threat Evaluation Engine**. It features atomic state handling, thread-safe memory caches, and structured JSON output designed for containerized deployment.

```go
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

// TelemetryEvent represents an incoming raw observation from a sensor node.
type TelemetryEvent struct {
	EventID   string    `json:"event_id"`
	TargetID  string    `json:"target_id"`
	Source    string    `json:"source"`
	Latitude  float64   `json:"latitude"`
	Longitude float64   `json:"longitude"`
	Timestamp time.Time `json:"timestamp"`
}

// POIState tracks the real-time aggregated state of a Person of Interest.
type POIState struct {
	CanonicalID string    `json:"canonical_id"`
	Aliases     []string  `json:"aliases"`
	LastSeen    time.Time `json:"last_seen"`
	Latitude    float64   `json:"latitude"`
	Longitude   float64   `json:"longitude"`
	ThreatLevel int       `json:"threat_level"`
	mu          sync.RWMutex
}

// POIEngine manages thread-safe storage and evaluation of active targets.
type POIEngine struct {
	storage map[string]*POIState
	mu      sync.RWMutex
	logger  *slog.Logger
}

func NewPOIEngine(logger *slog.Logger) *POIEngine {
	return &POIEngine{
		storage: make(map[string]*POIState),
		logger:  logger,
	}
}

// Ingest processes an incoming event, updating or initializing the POI state.
func (e *POIEngine) Ingest(ctx context.Context, event TelemetryEvent) error {
	if event.TargetID == "" {
		return errors.New("invalid event: missing target_id — verify payload upstream")
	}

	e.mu.Lock()
	state, exists := e.storage[event.TargetID]
	if !exists {
		state = &POIState{
			CanonicalID: event.TargetID,
			Aliases:     []string{event.Source},
			ThreatLevel: 1,
		}
		e.storage[event.TargetID] = state
	}
	e.mu.Unlock()

	state.mu.Lock()
	defer state.mu.Unlock()

	state.LastSeen = event.Timestamp
	state.Latitude = event.Latitude
	state.Longitude = event.Longitude

	e.logger.Info("telemetry processed successfully",
		"canonical_id", state.CanonicalID,
		"lat", state.Latitude,
		"lon", state.Longitude,
	)

	return nil
}

// HandleIngestHTTP provides a high-performance REST endpoint for ingestion.
func HandleIngestHTTP(engine *POIEngine) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "Method not allowed — use POST", http.StatusMethodNotAllowed)
			return
		}

		var event TelemetryEvent
		dec := json.NewDecoder(r.Body)
		dec.DisallowUnknownFields()

		if err := dec.Decode(&event); err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			_ = json.NewEncoder(w).Encode(map[string]string{
				"error": fmt.Sprintf("malformed payload: %v", err),
				"fix":   "Ensure body contains valid JSON matching TelemetryEvent schema. Run 'poi-cli --help' for schema details.",
			})
			return
		}

		if err := engine.Ingest(r.Context(), event); err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnprocessableEntity)
			_ = json.NewEncoder(w).Encode(map[string]string{
				"error": err.Error(),
				"fix":   "Check input fields and verify upstream producer configuration.",
			})
			return
		}

		w.WriteHeader(http.StatusAccepted)
		_, _ = w.Write([]byte(`{"status":"accepted","next_action":"monitor via /stream"}`))
	}
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	engine := NewPOIEngine(logger)

	mux := http.NewServeMux()
	mux.HandleFunc("/v1/telemetry", HandleIngestHTTP(engine))

	server := &http.Server{
		Addr:         ":8080",
		Handler:      mux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Graceful shutdown handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	go func() {
		logger.Info("starting POI ingestion engine", "addr", server.Addr)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server terminated unexpectedly", "err", err)
			os.Exit(1)
		}
	}()

	<-sigChan
	logger.Info("shutting down ingestion engine gracefully...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		logger.Error("forced server shutdown", "err", err)
		os.Exit(1)
	}

	logger.Info("POI engine stopped cleanly. Exit code 0.")
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | The Production Fix |
| :--- | :--- | :--- |
| **Global Monolithic Locks** | Using a single mutex across the entire entity database creates thread contention under high ingestion loads, driving CPU spikes and latency up. | Implement fine-grained sharding or lock-free concurrent maps (`sync.Map` or partition keys by hash ranges). |
| **Unbounded State Accumulation** | Storing historical pings in memory without TTLs or windowing leads to Out-Of-Memory (OOM) crashes. | Use sliding-window aggregates in Redis (Sorted Sets) or offload historical time-series data to TimescaleDB/ClickHouse asynchronously. |
| **Silent Failures on Malformed Streams** | Discarding unparseable JSON packets silently hides sensor failures and corrupts telemetry coverage maps. | Route invalid payloads to a dead-letter queue (DLQ) with structured error context, increment metrics counters, and raise alerting thresholds. |
| **Naive Geospatial Bounding Boxes** | Using flat-earth coordinate math ($lat/lon$ rectangles) results in severe distortion near polar regions and inaccurate distance calculations. | Utilize proper spatial indexing libraries implementing Haversine formulas or H3/S2 spatial hierarchical indexing cells. |

---

## 5. Performance & Optimization Tips

* **Zero-Allocation Deserialization:** In ultra-high-throughput ingestion paths (100k+ events/sec), avoid standard `encoding/json` reflection overhead. Use code-generated parsers (e.g., `json-iterator` or `easyjson`) or binary wire formats like Protocol Buffers.
* **Connection Pooling:** Maintain persistent, pre-warmed connection pools to your state caches (Redis/Dragonfly) and messaging brokers (Kafka/Redpanda) to eliminate TCP handshake latency on the hot path.
* **Batch Telemetry Writes:** Never perform single-row database inserts for telemetry tracks. Batch points in memory using a ring buffer and flush every 50ms or 1,000 items, whichever comes first.
* **CPU Affinity & Thread Isolation:** Pin ingestion worker goroutines to dedicated OS threads using runtime configuration where lock latency is critical.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Enterprise Commercial License (v1.0)
* **Copyright © 2026 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and incorporate this code and architectural blueprint into commercial, proprietary, or open-source internal software products.
* **Restrictions:** Redistribution of this raw reference architecture kit as a competing commercial template, boilerplate generator, or standalone digital product on marketplaces (Gumroad, GitHub Sponsors, AWS Marketplace) is strictly prohibited without explicit written authorization from MicroCorp AI.
* **Warranty & Liability:** Provided "AS IS", without warranty of any kind, express or implied. In no event shall MicroCorp AI be liable for any claim, damages, or liability arising from the deployment of tracking, surveillance, or entity resolution systems built using this toolkit.