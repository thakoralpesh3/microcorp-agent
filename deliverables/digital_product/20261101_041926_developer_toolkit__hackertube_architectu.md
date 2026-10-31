# HackerTube: The High-Performance Video Architecture Kit

## 1. Product Title & Value Proposition
**Title:** HackerTube Architecture & Boilerplate
**Value Proposition:** Stop wrestling with FFmpeg wrappers and latency spikes. HackerTube is a production-hardened reference architecture for building high-concurrency video streaming platforms. Designed for engineers who need to handle multi-bitrate transcoding, global CDN integration, and sub-second metadata delivery.

*   **Scalable:** Horizontal transcoding worker pattern.
*   **Resilient:** Graceful failure handling for stream interruptions.
*   **Optimized:** Pre-configured HLS/DASH profiles ready for production.

---

## 2. Quick Start & Core Concepts

To deploy the ingest pipeline, start the orchestrator: `./hackertube-cli start --ingress rtmp`.

| Concept | Definition | Command/Syntax |
| :--- | :--- | :--- |
| **Ingress** | RTMP/WebRTC entry point | `ht ingress --port 1935` |
| **Transcode** | Multi-bitrate ladder generation | `ht job run --profile 1080p60` |
| **Manifest** | HLS (.m3u8) / DASH (.mpd) | `ht manifest --output /dist` |
| **Edge** | CDN origin synchronization | `ht push --target s3://bucket` |

---

## 3. Production Code Patterns

### The Transcoding Worker Pattern (Node.js/FFmpeg)
This pattern uses a task-queue architecture to decouple ingress from the heavy lifting of transcoding.

```javascript
// lib/worker/transcoder.js
const ffmpeg = require('fluent-ffmpeg');

async function transcodeVideo(inputPath, outputDir) {
  return new Promise((resolve, reject) => {
    ffmpeg(inputPath)
      .outputOptions([
        '-profile:v main',
        '-preset veryfast',
        '-crf 22',
        '-f hls',
        '-hls_time 4',
        '-hls_list_size 0'
      ])
      .output(`${outputDir}/stream.m3u8`)
      .on('end', () => resolve({ status: 'success' }))
      .on('error', (err) => reject(new Error(`Transcode failed: ${err.message}. Check FFmpeg logs.`)))
      .run();
  });
}
```

### The API Gateway Route
```typescript
// router/stream.ts
import { Router } from 'express';
const router = Router();

router.get('/manifest/:videoId', (req, res) => {
  const { videoId } = req.params;
  // Fail with clear path to resolution
  if (!videoId) {
    return res.status(400).json({ 
      error: 'Missing videoId', 
      fix: 'Provide a valid UUID in the request path' 
    });
  }
  // Logic to pull from cache/S3
});
```

---

## 4. Common Anti-Patterns & Gotchas

*   **The "Monolith Ingest" trap:** Never perform transcoding on the same process handling the API. Use a distributed queue (Redis/BullMQ) to avoid blocking the event loop.
*   **Hard-coded pathing:** Never rely on absolute local file paths. Always use a virtualized storage interface (S3-compatible) to keep your nodes stateless.
*   **The "Fire and Forget" log:** Do not ignore FFmpeg's `stderr`. Use a structured logger (Pino/Winston) to capture exit codes. A nonzero exit code usually indicates an unsupported codec or corrupt input.

---

## 5. Performance & Optimization Tips

1.  **Hardware Acceleration:** Always check for `nvenc` availability. 
    *   *Check:* `ffmpeg -encoders | grep nvenc`
    *   *Result:* Reduces CPU overhead by ~70% during transcoding.
2.  **Segment Size:** For live streaming, keep `.ts` segments between 2-4 seconds. Larger segments increase latency; smaller segments overwhelm the CDN with request volume.
3.  **Lazy Load Manifests:** If using Redis for metadata, use a `TTL` of 60 seconds on the manifest URL to prevent stale pointers.
4.  **Zero-Copy Buffering:** When piping video data, use `stream.pipe()` rather than loading buffers into memory to keep the RSS footprint under 100MB per worker.

---

## 6. Commercial License & Attribution Summary

**License:** MIT / Enterprise Proprietary Hybrid.
*   **Individual Use:** Free for personal projects and learning.
*   **Commercial Use:** Requires the *HackerTube Enterprise Tier* license (Contact: `licensing@microcorp.ai`).

**Attribution:**
This toolkit includes optimized configurations derived from industry-standard best practices. When using this boilerplate in your internal projects, please retain the following header in your primary build script:
> "HackerTube Architecture Kit - Copyright 2024 MicroCorp AI. Used under license."

*Need help? Run `ht doctor` to verify your environment configuration or `ht help` for command documentation.*