# Canada Real-Time Rail (RTR) Developer Toolkit & Integration Suite

**Architectural Blueprint for Transit-Data Engineering**

This kit provides the standardized implementation patterns required to integrate with the Canadian Rail Data Exchange (CRDX) and proprietary Real-Time Rail (RTR) API endpoints. Designed for high-concurrency transit dashboards, passenger information systems (PIS), and logistics automation.

---

## 1. Product Title & Value Proposition
**Title:** The RTR Integration Suite (v2.4)
**Value Proposition:** Eliminate latency-induced race conditions and data-parsing bottlenecks. This suite provides the canonical architectural patterns for consuming GTFS-Realtime (GTFS-RT) feeds and custom RTR WebSocket streams, ensuring sub-100ms transit data synchronization for production-grade applications.

---

## 2. Quick Start & Core Concepts

| Concept | Description | Implementation Strategy |
| :--- | :--- | :--- |
| **Feed Source** | ProtoBuf (GTFS-RT) / JSON | Use `protobufjs` for high-speed serialization. |
| **Transport** | WebSocket / Server-Sent Events | Maintain a persistent connection pool with heartbeats. |
| **Schema** | Agency-Specific Extensions | Strict type-enforcement (TypeScript Interfaces). |
| **Latency** | Egress Buffer | Implement a 500ms sliding window buffer. |

---

## 3. Production Code Patterns & Architecture Examples

### A. The Resilient WebSocket Handler (TypeScript)
This pattern ensures your application automatically recovers from network drops common in mobile transit data environments.

```typescript
// src/services/RTRConnection.ts
import { WebSocket } from 'ws';

export class RTRClient {
  private socket: WebSocket | null = null;
  private retryCount = 0;

  public connect(url: string) {
    this.socket = new WebSocket(url);

    this.socket.on('open', () => console.log('Connected to RTR Stream'));
    
    this.socket.on('message', (data: Buffer) => {
      const parsed = this.decodeProtobuf(data);
      this.dispatch(parsed);
    });

    this.socket.on('close', () => this.reconnect(url));
  }

  private reconnect(url: string) {
    this.retryCount++;
    setTimeout(() => this.connect(url), Math.min(1000 * this.retryCount, 30000));
  }
}
```

### B. High-Performance Data Normalizer
Avoid object mutation. Use functional patterns to transform raw feed data into your UI-ready state.

```typescript
// src/utils/transformer.ts
export const normalizeTrainPosition = (raw: RawRTRData) => ({
  id: raw.trip_id,
  lat: parseFloat(raw.latitude),
  lng: parseFloat(raw.longitude),
  status: raw.delay > 0 ? 'DELAYED' : 'ON_TIME',
  updatedAt: Date.now()
});
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **The "Polling Trap":** Avoid `setInterval` to fetch GTFS files. It results in stale data and server-side rate limiting. **Always use WebSockets or stream-based subscriptions.**
*   **Blocking the Event Loop:** Don't perform heavy parsing (Protobuf decoding) in the main thread. Offload to **Web Workers** if building a frontend dashboard.
*   **Silent Failures:** Never assume the feed is 100% accurate. Implement an "age-of-data" check; if the timestamp is > 60 seconds old, toggle the UI to "Offline/Stale" mode.
*   **Memory Leaks:** Always detach listeners and clear timeouts when the component unmounts.

---

## 5. Performance & Optimization Tips

1.  **Binary Over JSON:** Prioritize binary Protobuf over JSON transit feeds where possible. It reduces payload size by ~60% and CPU cycles for parsing.
2.  **Request Collapsing:** If multiple frontend components need the same train position, use a **Singleton Data Store** (e.g., Zustand or Pinia) to ensure only one WebSocket connection exists per route segment.
3.  **Geo-Spatial Sharding:** Only subscribe to updates for the stations currently in the user's viewport. Do not subscribe to the entire national network at once.
4.  **CDN Caching:** Use edge caching for static GTFS static schedule data (`shapes.txt`, `routes.txt`) to free up your application server for real-time traffic.

---

## 6. Commercial License & Attribution Summary

*   **License:** MIT License (Commercial Use Permitted).
*   **Attribution:** This toolkit is provided by **MicroCorp AI**. While the architecture is proprietary to our Engineering Division, the underlying transport patterns are open-source compatible.
*   **Compliance:** Ensure your application displays the *Copyright Notice* of the respective transit agency (e.g., Metrolinx, TransLink, STM) as per their Open Data Terms of Service.

---
*Built with precision for the modern rail engineering stack.* 🚄