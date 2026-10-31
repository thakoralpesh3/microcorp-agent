# HackerTube: The High-Performance Video Architecture Kit

## 1. Product Title & Value Proposition
**HackerTube** is a reference architecture and production-ready boilerplate for building high-concurrency video processing and streaming platforms. 

**Value Proposition:** Stop reinventing the wheel for FFmpeg pipelines, HLS segmenting, and S3-event-driven architecture. HackerTube provides the structural blueprint to move from upload to globally distributed playback with optimized latency and cost-efficient storage tiers.

---

## 2. Quick Start & Core Concepts

| Concept | Tech Stack Recommendation | Why? |
| :--- | :--- | :--- |
| **Ingestion** | Go + TUS protocol | Resumable uploads for large binary blobs. |
| **Transcoding** | FFmpeg + AWS Lambda/Batch | Auto-scaling compute for parallel encoding. |
| **Delivery** | CloudFront + S3 | Edge-cached HLS (.m3u8) delivery. |
| **Persistence** | PostgreSQL + Redis | Metadata relational integrity + caching. |

### The Pipeline Workflow
1. **Upload:** Client pushes binary to `TUS` server.
2. **Event:** S3 `ObjectCreated` triggers a Lambda function.
3. **Encode:** Worker pulls file, triggers `FFmpeg` multi-resolution output.
4. **Notify:** Service updates DB status to `READY` via Webhook.

---

## 3. Production Code Patterns & Architecture

### A. The Transcoding Engine (Go Implementation)
A robust wrapper for FFmpeg that enforces memory safety and timeout logic.

```go
package processor

import (
	"os/exec"
	"time"
)

// TranscodeVideo enforces strict time limits to prevent hanging processes
func TranscodeVideo(input string, output string) error {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	cmd := exec.CommandContext(ctx, "ffmpeg", 
		"-i", input, 
		"-vf", "scale=1280:720", 
		"-c:v", "libx264", 
		"-f", "hls", 
		output)

	return cmd.Run()
}
```

### B. HLS Master Playlist Pattern
This ensures the player selects the appropriate bitrate based on network conditions.

```m3u8
#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
1080p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1280x720
720p/index.m3u8
```

---

## 4. Common Anti-Patterns & Gotchas

*   **Synchronous Processing:** Never transcode in the request-response cycle. Always offload to an asynchronous queue (SQS/RabbitMQ).
*   **The "One-Size" Transcode:** Avoid shipping a single 4K file. Users on mobile will pay in data costs and latency. **Always** generate a multi-bitrate ladder (360p, 720p, 1080p).
*   **Storage Bloat:** Forgetting to set S3 Lifecycle Policies on original raw uploads. **Fix:** Set a rule to transition raw source files to Glacier Instant Retrieval after 30 days.

---

## 5. Performance & Optimization Tips

1. **Hardware Acceleration:** If hosting on bare metal, ensure `h264_nvenc` or `vaapi` is enabled for hardware-accelerated encoding.
2. **GOP Size:** Set `GOP (Group of Pictures)` to 2 seconds (e.g., `fps * 2`) to ensure smooth seeking in the video player.
3. **CORS Configuration:** Ensure your S3 bucket allows `GET` and `HEAD` from your specific video player domain; otherwise, you will face "Access Denied" errors during HLS segment fetches.
4. **Pre-warming:** If you expect a viral spike, use `CloudFront Origin Shield` to collapse requests at a regional cache before they hit your S3 origin.

---

## 6. Commercial License & Attribution Summary

*   **License:** MIT / Commercial Use Permitted.
*   **Attribution:** You may use the patterns provided in this kit for closed-source commercial projects without attribution. Selling the source code of this boilerplate as-is is prohibited.
*   **Warranty:** This architecture is provided "as is". The user is responsible for ensuring compliance with platform-specific streaming policies (e.g., Apple HLS Guidelines).

---

> **Developer Note:** Need to integrate with a specific player like Video.js or Shaka Player? Refer to our `extras/integration-guides.md` folder for the accompanying client-side bridge implementation.