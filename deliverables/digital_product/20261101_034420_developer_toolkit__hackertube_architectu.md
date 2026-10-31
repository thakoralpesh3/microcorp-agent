# Developer Toolkit: HackerTube Architecture & Boilerplate

## 1. Product Title & Value Proposition
**Title:** HackerTube: High-Performance Video Distribution Architecture Kit
**Value Proposition:** Stop wrestling with FFmpeg orchestration and low-level storage logic. This kit provides a battle-tested, modular architecture for building scalable video-on-demand (VOD) platforms. It handles transcoding queues, CDN distribution, and secure stream management so you can focus on building your product's unique value.

---

## 2. Quick Start & Core Concepts
HackerTube is designed around the **"Ingest-Transcode-Deliver"** pipeline.

| Concept | Responsibility | Tech Stack Recommendation |
| :--- | :--- | :--- |
| **Ingest** | Securely receive raw video uploads | S3 Pre-signed URLs + Multipart |
| **Transcode** | Generate ABR (Adaptive Bitrate) HLS/DASH | BullMQ + FFmpeg Worker Nodes |
| **Storage** | Highly available object storage | AWS S3 / R2 (Cloudflare) |
| **Delivery** | Edge caching and stream acceleration | CloudFront / Fastly |

---

## 3. Production Code Patterns & Architecture
### The Transcoder Worker (Node.js/BullMQ)
*The heartbeat of the system. Offload video processing from the main web API to dedicated workers.*

```typescript
// worker.ts - Process raw upload to HLS segments
import ffmpeg from 'fluent-ffmpeg';

export const processVideo = async (job) => {
  const { inputKey, outputFolder } = job.data;

  return new Promise((resolve, reject) => {
    ffmpeg(inputKey)
      .outputOptions([
        '-profile:v baseline',
        '-level 3.0',
        '-start_number 0',
        '-hls_time 10',
        '-hls_list_size 0',
        '-f hls'
      ])
      .output(`${outputFolder}/playlist.m3u8`)
      .on('end', () => resolve({ status: 'completed' }))
      .on('error', (err) => reject(err))
      .run();
  });
};
```

### Secure Stream Access (Fastify/JWT)
*Ensure your media is protected by requiring time-limited signed URLs.*

```typescript
// middleware.ts - Protect your S3 assets
const getProtectedUrl = (key: string) => {
  const command = new GetObjectCommand({ Bucket: 'my-video-bucket', Key: key });
  // Expire link in 1 hour
  return getSignedUrl(s3Client, command, { expiresIn: 3600 });
};
```

---

## 4. Common Anti-Patterns & Gotchas
*   **The "Monolith Transcode" Trap:** Never trigger transcoding during the request/response cycle. Always use a message queue (BullMQ/RabbitMQ). **Fix:** Use asynchronous job workers.
*   **Exposing Raw Storage:** Never make your S3 buckets public. **Fix:** Use Origin Access Control (OAC) to ensure traffic *only* comes through your CDN.
*   **Ignoring ABR:** Hosting a single 4K file kills mobile user retention. **Fix:** Always generate 480p, 720p, and 1080p variants (Adaptive Bitrate Streaming).

---

## 5. Performance & Optimization Tips
1.  **GOP Alignment:** Ensure all your FFmpeg outputs have aligned Keyframe intervals. This allows the client player to switch between quality levels seamlessly without stuttering.
2.  **Edge Pre-warming:** If you expect a viral spike, use CDN API hooks to "warm" the cache for the new video segments across global POPs.
3.  **Database Indexing:** Use a `video_status` index in your Postgres/Mongo DB. Queries like `find({ status: 'ready' })` must be O(log n) or faster.
4.  **Graceful Degration:** If a user’s bandwidth drops, the client-side player (e.g., Video.js or HLS.js) should automatically fall back to lower-bitrate segments. Configure your player initialization to handle `level-switch` events.

---

## 6. Commercial License & Attribution
*   **License:** MIT License. You are free to integrate this architecture into proprietary commercial software.
*   **Attribution:** While not required, linking back to `HackerTube-Toolkit` is appreciated.
*   **Warranty:** This boilerplate is provided "as is." The responsibility for security audits and infrastructure costs rests with the implementer.
*   **Support:** For enterprise architectural consulting or custom worker implementation, contact `engineering@microcorp-ai.dev`.