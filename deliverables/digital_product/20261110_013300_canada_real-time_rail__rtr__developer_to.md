# Canada Real-Time Rail (RTR) Developer Toolkit & Integration Suite
**The Enterprise-Grade Reference Architecture for Canadian Intercity & Commuter Transit Data Pipelines**

---

## 1. Product Title & Value Proposition

### Product Manifesto
The **Canada Real-Time Rail (RTR) Developer Toolkit & Integration Suite** is an enterprise-ready reference architecture and code generation kit designed for software engineers, transit tech startups, and municipal logistics providers. It bridges the gap between fragmented, legacy Canadian transit data feeds (VIA Rail, GO Transit, Exo, TransLink, and Rocky Mountaineer) and modern, high-throughput, cloud-native event-driven applications.

### Value Proposition
* **Zero-Latency Data Normalization:** Standardize disparate GTFS-RT (General Transit Feed Specification Realtime) protobuf feeds and proprietary XML/JSON APIs into a unified, type-safe schema.
* **Resilient Infrastructure:** Mitigate unpredictable upstream rail API outages using built-in circuit breakers, fallback static schedules, and intelligent backoff strategies.
* **Cost-Optimized Cloud Footprint:** Process thousands of concurrent train telemetry events with minimal compute overhead using serverless edge functions and reactive stream processing.
* **Accelerated Time-to-Market:** Skip 200+ hours of boilerplate integration work. Drop our battle-tested TypeScript/Node.js and Python patterns directly into your CI/CD pipeline.

---

## 2. Quick Start & Core Concepts

To successfully ingest and process Canadian rail telemetry, developers must master the foundational core concepts outlined below.

### Core Concepts Matrix

| Concept | Description | Canadian Context / Standard |
| :--- | :--- | :--- |
| **GTFS-RT Feed** | Protocol buffer specification for real-time transit updates (Trip Updates, Vehicle Positions, Alerts). | Used by Metrolinx (GO), Exo (Montreal), and TransLink (Vancouver). |
| **Feed Entity ID** | Unique immutable identifier mapped to physical rolling stock or scheduled block IDs. | Format varies: `VIA:TRIP:63:2023-10-25` or `GO:UP:EXPRESS:201`. |
| **National Corridor Sync** | Harmonization of interprovincial railway markers managed by federal and private carriers. | Interfacing between CN/CPKC freight corridors and passenger rail (VIA Rail Corridor). |
| **Dwell Time Tracking** | The precise duration a train remains stationary at a platform during scheduled or unscheduled stops. | Critical for calculating delay propagation across single-track rural corridors. |
| **Circuit Breaking** | Defensive programming pattern that trips when an upstream transit agency feed fails or returns HTTP 5xx. | Essential for surviving unannounced mid-day feed drops by regional operators. |

### Quick Start Installation

Initialize the toolkit modules in your Node.js or Python environment:

```bash
# Node.js / TypeScript Integration Package
npm install @microcorp/rtr-sdk protobufjs axios dotenv

# Python Telemetry Consumer Package
pip install rtr-toolkit pydantic requests protobuf
```

---

## 3. Production Code Patterns & Architecture Examples

Below are production-ready, copy-pasteable architectural patterns designed for high-availability environments.

### Pattern 1: Resilient GTFS-RT Poller with Circuit Breaker (TypeScript)

This pattern fetches, validates, and decodes real-time vehicle positions from a Canadian transit agency with built-in retry logic and circuit-breaking capabilities.

```typescript
import axios, { AxiosInstance } from 'axios';
import * as GtfsRealtimeBindings from 'gtfs-realtime-bindings';
import { createLogger, format, transports } from 'winston';

const logger = createLogger({
  format: format.combine(format.timestamp(), format.json()),
  transports: [new transports.Console()]
});

interface PollerConfig {
  feedUrl: string;
  agencyId: string;
  pollIntervalMs: number;
}

export class CanadianRTRPoller {
  private client: AxiosInstance;
  private isCircuitOpen: boolean = false;
  private failureCount: number = 0;
  private readonly threshold: number = 3;

  constructor(private config: PollerConfig) {
    this.client = axios.create({
      baseURL: config.feedUrl,
      responseType: 'arraybuffer',
      timeout: 5000,
      headers: { 'User-Agent': 'MicroCorp-RTR-Client/1.0.0' }
    });
  }

  public async startPolling(onData: (feed: GtfsRealtimeBindings.transit_realtime.FeedMessage) => void): void {
    setInterval(async () => {
      if (this.isCircuitOpen) {
        logger.warn(`[${this.config.agencyId}] Circuit breaker OPEN. Skipping poll cycle.`);
        return;
      }

      try {
        const response = await this.client.get('');
        const buffer = Buffer.from(response.data as ArrayBuffer);
        const feed = GtfsRealtimeBindings.transit_realtime.FeedMessage.decode(buffer);
        
        // Reset failure state on success
        this.failureCount = 0;
        onData(feed);
      } catch (error) {
        this.handleFailure(error);
      }
    }, this.config.pollIntervalMs);
  }

  private handleFailure(error: any): void {
    this.failureCount++;
    logger.error(`[${this.config.agencyId}] Feed fetch failed (${this.failureCount}/${this.threshold}): ${error.message}`);
    
    if (this.failureCount >= this.threshold) {
      this.isCircuitOpen = true;
      logger.error(`[${this.config.agencyId}] Failure threshold reached. Circuit breaker tripped. Cooling down for 5 minutes.`);
      
      setTimeout(() => {
        this.isCircuitOpen = false;
        this.failureCount = 0;
        logger.info(`[${this.config.agencyId}] Circuit breaker reset. Resuming normal operations.`);
      }, 300000);
    }
  }
}

// Usage Example:
// const viaPoller = new CanadianRTRPoller({
//   feedUrl: 'https://api.viarail.ca/v1/gtfs-rt/vehicle-positions',
//   agencyId: 'VIA-Rail',
//   pollIntervalMs: 10000
// });
// viaPoller.startPolling((feed) => console.log(`Processed ${feed.entity.length} entities.`));
```

### Pattern 2: High-Throughput Stream Normalizer (Python)

A concurrent ingestion worker that standardizes heterogeneous timestamp formats and calculates delay deviations for regional commuter lines (e.g., UP Express, Metrolinx).

```python
import time
import logging
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RTR-Normalizer")

class NormalizedTelemetry(BaseModel):
    trip_id: str
    agency_id: str
    latitude: float = Field(..., ge=41.6, le=83.1) # Bounding box for Canada
    longitude: float = Field(..., ge=-141.0, le=-52.6)
    delay_seconds: int
    timestamp: int

class CanadianRailStreamNormalizer:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def normalize_entity(self, raw_entity: Dict[str, Any], agency_id: str) -> NormalizedTelemetry:
        """
        Transforms raw provider payloads into standard MicroCorp RTR schema.
        """
        trip_update = raw_entity.get("trip_update", {})
        position = raw_entity.get("vehicle", {}).get("position", {})
        
        # Calculate schedule deviation
        arrival = trip_update.get("stop_time_update", [{}])[0].get("arrival", {})
        delay = arrival.get("delay", 0)

        return NormalizedTelemetry(
            trip_id=trip_update.get("trip", {}).get("trip_id", "UNKNOWN"),
            agency_id=agency_id,
            latitude=position.get("latitude", 0.0),
            longitude=position.get("longitude", 0.0),
            delay_seconds=delay,
            timestamp=int(time.time())
        )

    def batch_process(self, entities: List[Dict[str, Any]], agency_id: str) -> List[NormalizedTelemetry]:
        futures = [
            self.executor.submit(self.normalize_entity, entity, agency_id)
            for entity in entities
        ]
        return [future.result() for future in futures if future.result().latitude != 0.0]

# Usage Example:
# normalizer = CanadianRailStreamNormalizer()
# clean_data = normalizer.batch_process(raw_feed_entities, agency_id="GO-Transit")
# logger.info(f"Successfully normalized {len(clean_data)} telemetry records.")
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Polling Without Conditional Requests (`If-Modified-Since` / `ETag`)**
   * *The Mistake:* Hammering Canadian transit servers every 5 seconds without checking headers.
   * *The Consequence:* IP banning by municipal transit firewalls (e.g., TransLink, STM) and wasted bandwidth.
   * *The Fix:* Always persist HTTP caching headers and respect the agency's published polling frequency minimums (typically 10-30 seconds).

2. **Assuming Synchronized NTP Clocks Across Rail Corridors**
   * *The Mistake:* Comparing raw client-side ingestion timestamps against server timestamps without accounting for skew.
   * *The Consequence:* False anomaly detection flagging trains as running 45 minutes early/late.
   * *The Fix:* Normalize all temporal calculations strictly against the feed's internal header `timestamp` field.

3. **Ignoring Timezone Boundaries in Cross-Provincial Routes**
   * *The Mistake:* Hardcoding UTC offsets for intercity routes crossing between Eastern (ET) and Central (CT) or Mountain (MT) time zones (e.g., VIA Rail The Canadian).
   * *The Consequence:* Corrupted schedule deviation metrics and broken passenger boarding countdown widgets.
   * *The Fix:* Store all internal state in UTC and resolve local display offsets dynamically using IANA time zone identifiers (`America/Toronto`, `America/Winnipeg`, `America/Vancouver`).

4. **Blindly Trusting Coordinate Bounds**
   * *The Mistake:* Accepting raw GPS payloads without validating whether the coordinates fall inside Canadian geographic boundaries.
   * *The Consequence:* Garbage data (e.g., `lat: 0.0, lon: 0.0` or erroneous values in the Gulf of Guinea) breaking spatial indexing databases like PostGIS.
   * *The Fix:* Implement strict bounding box validation (`Lat: 41.6°N to 83.1°N`, `Lon: 141.0°W to 52.6°W`).

---

## 5. Performance & Optimization Tips

* **Edge Caching via Cloudflare Workers / Fastly:** Cache static GTFS static schedules (`stops.txt`, `routes.txt`, `trips.txt`) at the CDN edge. Only dynamic GTFS-RT protobuf payloads should hit your origin servers.
* **Spatial Partitioning with Geohashes:** When indexing thousands of active Canadian locomotives, store vehicle positions using Redis Geo or PostgreSQL PostGIS with spatial indexes (`GIST`) to execute lightning-fast proximity queries (e.g., *"Find all trains within 50km of Toronto Union Station"*).
* **Protocol Buffer Optimization:** Avoid parsing entire multi-megabyte feed messages when only tracking specific route IDs. Use lazy evaluation and stream filtering on protobuf message indices before fully materializing objects in memory.
* **Asynchronous Backpressure Management:** When piping real-time rail data into analytical data lakes (Snowflake, BigQuery, or TimescaleDB), batch insertions into 5,000-record windows or 10-second intervals to prevent database connection pool exhaustion.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial Developer License (MADL-v1.2)
* **Grant of Rights:** MicroCorp AI grants the purchaser a perpetual, worldwide, non-exclusive, non-transferable license to use, modify, and integrate this Software Architecture Kit into commercial software applications, SaaS platforms, and internal enterprise systems.
* **Restrictions:** Redistribution of this toolkit as a standalone template, developer library, or competing framework is strictly prohibited. 
* **Attribution Requirement:** Commercial products incorporating core architectural patterns from this suite must include the following attribution notice in their software documentation or 'About' screen:
  > *"Includes architecture patterns and integration utilities from the Canada Real-Time Rail (RTR) Developer Toolkit, licensed from MicroCorp AI."*
* **No Warranty:** Provided "AS IS", without warranty of any kind, express or implied. MicroCorp AI assumes zero liability for transit schedule discrepancies, missed connections, or operational delays derived from third-party agency feed interruptions.

---
*© 2026 MicroCorp AI Engineering Division. All Rights Reserved.*