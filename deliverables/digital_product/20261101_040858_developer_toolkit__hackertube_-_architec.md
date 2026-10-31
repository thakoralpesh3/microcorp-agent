# HackerTube: The Developer Reference & Architecture Kit

## 1. Product Title & Value Proposition

**Title:** HackerTube Architecture & Boilerplate Kit
**Value Proposition:** Stop wrestling with video streaming complexity. HackerTube provides a production-grade blueprint for high-concurrency, low-latency video distribution. Whether you are building a niche learning platform or a large-scale streaming app, this kit eliminates architectural debt by providing battle-tested patterns for ingestion, transcoding, and delivery.

---

## 2. Quick Start & Core Concepts

HackerTube is built on a **"Decoupled Ingestion & Delivery"** model. 

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Ingestion** | `FFmpeg` / `S3` | Raw file upload and buffer storage. |
| **Transcoding** | `AWS Elemental MediaConvert` | Multi-bitrate HLS/DASH generation. |
| **Delivery** | `CloudFront` / `CDN` | Edge-cached manifest and segment delivery. |
| **Metadata** | `PostgreSQL` / `Redis` | Video state, user auth, and hot-cache. |

### CLI Tool: `htube` (Reference Implementation)
*   `htube init`: Scaffolds the database schema.
*   `htube stream --source <file>`: Triggers transcoding job.
*   `htube manifest --id <vid>`: Outputs valid HLS manifest for playback.

---

## 3. Production Code Patterns & Architecture Examples

### A. The Transcoding Producer (Node.js/TypeScript)
This pattern ensures that transcoding tasks are non-blocking and idempotent.

```typescript
// src/services/transcoder.ts
import { MediaConvert } from '@aws-sdk/client-mediaconvert';

export async function createTranscodeJob(videoKey: string) {
  const client = new MediaConvert({ region: 'us-east-1' });
  
  const params = {
    Settings: {
      OutputGroups: [{
        Name: 'HLS Group',
        OutputGroupSettings: { Type: 'HLS_GROUP_SETTINGS', HlsGroupSettings: { SegmentLength: 6 } }
      }]
    },
    Role: process.env.IAM_ROLE_ARN
  };

  try {
    const job = await client.createJob(params);
    return { status: 'queued', jobId: job.Job?.Id };
  } catch (err) {
    throw new Error(`Transcoding failed: ${err.message}. Ensure IAM_ROLE_ARN is configured.`);
  }
}
```

### B. Scalable Database Schema (PostgreSQL)
```sql
CREATE TABLE videos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status TEXT CHECK (status IN ('uploading', 'processing', 'ready', 'failed')),
  hls_manifest_url TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_videos_status ON videos(status);
```

---

## 4. Common Anti-Patterns & Gotchas

*   **The "Local Transcode" Trap:** Never transcode video on the application server. It will starve your event loop and crash your process. **Always offload to dedicated workers (AWS MediaConvert/FFmpeg-on-ECS).**
*   **The "Monolithic Storage" Error:** Do not serve video files directly from your web server. Use an S3 bucket fronted by a CDN. 
*   **Missing Signed URLs:** Never make your video bucket public. Use CloudFront Signed URLs to prevent content scraping and bandwidth theft.

---

## 5. Performance & Optimization Tips

1.  **HLS Segment Tuning:** Set segment duration to 4–6 seconds. Too short causes excessive HTTP requests; too long causes high latency when seeking.
2.  **CDN Warm-up:** Use `CloudFront` "Cache-Control" headers aggressively (`public, max-age=31536000`) for immutable video segments.
3.  **Database Connection Pooling:** Use `pgbouncer` to handle high-concurrency metadata lookups, as video player clients will hit your API endpoint frequently.
4.  **Graceful Failover:** Always have a fallback fallback (e.g., `480p` stream) if the `1080p` source is still processing.

---

## 6. Commercial License & Attribution Summary

**License:** MIT License
**Attribution:** Provided by The Agency Engineering Division.

*   **Commercial Use:** You are free to modify, distribute, and use this codebase in proprietary products.
*   **Warranty:** This is provided "as is". The Agency is not liable for cloud provider egress costs or transcoding fees incurred by the user.
*   **Support:** For architecture review or custom implementations, contact our consulting arm at `dev-consult@theagency.corp`.

---

> **Developer Note:** *This kit is designed to be version-controlled. Store your environment-specific secrets in `app.toml` and never commit them to source control. Run `htube validate` before every deployment to ensure your S3 bucket policies are non-public.*