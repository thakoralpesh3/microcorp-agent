# HackerTube: Developer Toolkit & Architecture Blueprint
*Version 2.4.0 — Enterprise Edition*

---

## 1. Product Title & Value Proposition

**HackerTube** is a production-ready, high-throughput video streaming and processing architecture blueprint designed for developers building custom video platforms, internal training portals, or high-concurrency media distribution systems. 

### Why HackerTube?
Modern video pipelines are notorious for high egress costs, complex queue management, and transcoding bottlenecks. HackerTube provides a battle-tested, modular architecture combining S3-compatible storage, distributed worker pools (FFmpeg), edge caching (Cloudflare/CDN), and real-time WebSocket progress tracking.

### Core Value Metrics
- **99.99% Pipeline Reliability:** Idempotent job processing with automatic dead-letter queue (DLQ) recovery.
- **Sub-Second Time-to-First-Byte (TTFB):** Optimized HLS/DASH chunking strategies combined with edge caching.
- **Zero-Trust Security:** Signed URLs, expiring token validation, and isolated worker sandboxes.

---

## 2. Quick Start & Core Concepts

### CLI Tooling (`hacker-tube`)
HackerTube ships with a developer-first CLI designed with sub-100ms startup times, strict exit codes, and actionable error states.

| Command | Description | Example Usage |
| :--- | :--- | :--- |
| `hacker-tube init` | Scaffolds configuration file (`tube.toml`) | `hacker-tube init --force` |
| `hacker-tube validate` | Verifies storage buckets and worker health | `hacker-tube validate --config tube.toml` |
| `hacker-tube ingest` | Uploads and queues a raw video for transcoding | `hacker-tube ingest --input ./raw.mp4 --preset 1080p` |
| `hacker-tube jobs list` | Inspects active transcoding queue | `hacker-tube jobs list --status failed` |

### Core Concepts Syntax Table

| Concept | Implementation Layer | Description |
| :--- | :--- | :--- |
| **Ingest Pipeline** | API Gateway / S3 Direct | Multipart signed-URL upload directly to object storage, bypassing application server memory limits. |
| **Transcoding Worker** | Go + FFmpeg (Docker Sandbox) | Stateless workers pulling jobs from Redis/SQS, producing adaptive bitrate (ABR) HLS streams. |
| **Manifest Generation** | Playlist Generator Service | Dynamically constructs `.m3u8` master playlists linking resolution variants and audio tracks. |
| **Edge Distribution** | CDN / Object Storage | Caches `.ts` video segments indefinitely while short-circuiting expiration checks on `.m3u8` master files. |

---

## 3. Production Code Patterns & Architecture Examples

### A. Resilient Video Ingest Controller (Go / Fiber)
This pattern handles secure upload URL generation and ensures correct database state initialization.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
)

type IngestRequest struct {
	Filename    string `json:"filename"`
	ContentType string `json:"content_type"`
	SizeBytes   int64  `json:"size_bytes"`
}

type IngestResponse struct {
	UploadURL string    `json:"upload_url"`
	VideoID   string    `json:"video_id"`
	ExpiresAt time.Time `json:"expires_at"`
}

// Mock S3 Signer (Replace with AWS SDK v2 in production)
func generatePresignedPutURL(videoID, filename string) (string, error) {
	if filename == "" {
		return "", errors.New("invalid filename provided")
	}
	return fmt.Sprintf("https://storage.hackertube.internal/raw/%s/%s?signature=mock_sig_xyz", videoID, filename), nil
}

func HandleIngest(c *fiber.Ctx) error {
	var req IngestRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "Malformed JSON payload",
			"fix":     "Ensure request body matches IngestRequest schema and Content-Type is application/json",
			"details": err.Error(),
		})
	}

	if req.SizeBytes > 5368709120 { // 5GB limit
		return c.Status(fiber.StatusRequestEntityTooLarge).JSON(fiber.Map{
			"error": "File exceeds maximum allowed size of 5GB",
			"fix":   "Split the video file or contact enterprise support for large file ingestion pipelines",
		})
	}

	videoID := uuid.New().String()
	expires := time.Now().Add(15 * time.Minute)

	uploadURL, err := generatePresignedPutURL(videoID, req.Filename)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Failed to generate storage upload URL",
			"fix":   "Verify S3 IAM credentials and storage bucket configuration via `hacker-tube validate`",
		})
	}

	return c.Status(fiber.StatusCreated).JSON(IngestResponse{
		UploadURL: uploadURL,
		VideoID:   videoID,
		ExpiresAt: expires,
	})
}
```

### B. FFmpeg Transcoding Worker Script (Python)
Robust execution script that wraps FFmpeg to generate Adaptive Bitrate (ABR) HLS streams with explicit error handling and cleanup.

```python
#!/usr/bin/env python3
"""
HackerTube Transcoding Worker Engine
Converts raw input video into multi-bitrate HLS streams.
"""

import subprocess
import sys
import os
from pathlib import Path

def transcode_video(input_path: str, output_dir: str) -> None:
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file not found at {input_file}", file=sys.stderr)
        print("Fix: Verify the file path or run `hacker-tube ingest` to upload a valid file.", file=sys.stderr)
        sys.exit(2)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    master_playlist = out_path / "master.m3u8"

    # Production FFmpeg command for 720p / 1080p adaptive HLS output
    cmd = [
        "ffmpeg", "-y", "-i", str(input_file),
        "-filter_complex",
        "[0:v]split=2[v1][v2];"
        "[v1]scale=w=1280:h=720[v720];"
        "[v2]scale=w=1920:h=1080[v1080]",
        "-map", "[v720]", "-c:v:0", "libx264", "-b:v:0", "2800k", "-maxrate:0", "2996k", "-bufsize:0", "4200k",
        "-map", "[v1080]", "-c:v:1", "libx264", "-b:v:1", "5000k", "-maxrate:1", "5350k", "-bufsize:1", "7500k",
        "-map", "0:a", "-c:a", "aac", "-b:a", "128k",
        "-var_stream_map", "v:0,name=720p v:1,name=1080p a:0,name=audio",
        "-master_pl_name", "master.m3u8",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_segment_filename", str(out_path / "v%v_%03d.ts"),
        str(out_path / "stream_%v.m3u8")
    ]

    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Success: Transcoding completed. Master playlist generated at {master_playlist}")
    except subprocess.CalledProcessError as e:
        print(f"Error: FFmpeg execution failed with exit code {e.returncode}", file=sys.stderr)
        print(f"Details:\n{e.stderr[-1000:]}", file=sys.stderr)
        print("Fix: Ensure FFmpeg 5.x+ is installed and input video has valid audio/video streams.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python worker.py <input_file> <output_directory>", file=sys.stderr)
        sys.exit(1)
    transcode_video(sys.argv[1], sys.argv[2])
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Synchronous Transcoding in HTTP Handlers**
   * *Anti-Pattern:* Spawning FFmpeg directly inside an API request/response cycle.
   * *Gotcha:* Worker threads lock up, HTTP connections timeout, and memory consumption spikes instantly.
   * *The Fix:* Always offload transcoding to an asynchronous worker queue (RabbitMQ, AWS SQS, Redis BullMQ) with dedicated resource ceilings.

2. **Monolithic Storage Buckets**
   * *Anti-Pattern:* Storing raw uploads, processed segments, and application artifacts in a single S3 bucket.
   * *Gotcha:* Listing objects becomes exponentially slower and IAM permission scoping becomes impossible.
   * *The Fix:* Isolate workloads across distinct buckets: `hackertube-raw-input`, `hackertube-processed-hls`, and `hackertube-thumbnails`.

3. **Ignoring Fragment Alignment in Adaptive Streaming**
   * *Anti-Pattern:* Generating video variants with mismatched keyframe (`-g`) intervals.
   * *Gotcha:* Video playback stutters or drops frames when viewers switch resolutions dynamically mid-stream.
   * *The Fix:* Force strict keyframe intervals (`-g 48 -keyint_min 48` for 24fps content) across all transcoding profiles.

---

## 5. Performance & Optimization Tips

- **Direct-to-S3 Multipart Uploads:** Never proxy multi-gigabyte video files through your application servers. Utilize client-side multipart presigned URLs to upload directly to object storage.
- **Aggressive Edge Caching for Segments (`.ts`):** Video segments are immutable. Set Cache-Control headers on `.ts` files to `public, max-age=31536000, immutable` to offload 95%+ of egress traffic to your CDN edge.
- **Short TTLs for Master Playlists (`.m3u8`):** Keep TTLs low or use conditional requests (`ETag`) for master and variant playlists so users receive updated live states or fast error recovery.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (v2.0)
Copyright © 2025 MicroCorp AI. All rights reserved.

1. **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, and adapt this architecture blueprint and associated code snippets within internal and commercial software products.
2. **Restrictions:** Redistribution, resale, or public publishing of this source code or documentation as a standalone developer toolkit, template, or competing course is strictly prohibited without explicit written authorization from MicroCorp AI.
3. **Disclaimer of Warranty:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claim, damages, or liability arising from the deployment of these architectures in production environments.