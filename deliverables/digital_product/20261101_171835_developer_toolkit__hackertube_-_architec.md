# HackerTube: Enterprise Architecture & Implementation Guide
*Version 2.4.0 — Production Reference Kit*

---

## 1. Product Title & Value Proposition

### **HackerTube Developer Toolkit: Scalable Video Streaming & Real-Time Processing Pipeline**

Building a high-concurrency, resilient video platform requires navigating complex distributed systems problems: adaptive bitrate (ABR) transcoding, low-latency WebSockets for live chat, resilient edge caching, and scalable object storage management. 

The **HackerTube Architecture & Implementation Guide** gives senior full-stack and systems engineers a battle-tested blueprint. This toolkit eliminates months of trial and error by providing production-ready TypeScript/Node.js microservice patterns, optimized FFmpeg transcoding pipelines, robust database schemas, and caching strategies designed to handle millions of concurrent streams without breaking a sweat.

### **What’s Included in This Kit:**
*   **End-to-End Architecture Blueprints:** Event-driven microservices layout for ingestion, processing, and delivery.
*   **Copy-Paste Production Code:** Complete TypeScript modules for job queue orchestration, HLS chunk management, and WebSocket message routing.
*   **Operational Hardening:** Proven guardrails against common bottleneck traps (e.g., memory exhaustion during video slicing, thundering herd problems on viral video loads).

---

## 2. Quick Start & Core Concepts

### **System Architecture Overview**
HackerTube operates on an decoupled, asynchronous architecture. Videos ingested via chunked uploads are placed into an object storage bucket, triggering an event-driven transcoding worker pool via message brokers.

| Component | Technology Stack | Primary Responsibility | Scalability Vector |
| :--- | :--- | :--- | :--- |
| **API Gateway** | Node.js, Fastify, JWT | Rate limiting, auth verification, routing | Horizontal (Load Balanced) |
| **Ingestion Service** | Express, AWS S3 Multipart | Secure chunked video upload handling | Horizontal (Stateless Pods) |
| **Transcoding Engine**| Python, FFmpeg, Docker | Generating multi-bitrate HLS/DASH manifests | CPU-Bound (Auto-scaled Workers) |
| **Job Orchestrator** | Redis, BullMQ | Managing transcode queue priority & retries | In-Memory / Clustered Redis |
| **Metadata DB** | PostgreSQL, Prisma ORM | ACID compliance for users, videos, channels | Read Replicas + Connection Pooling |
| **Caching Layer** | Redis Enterprise | Video metadata caching, rate-limit counters | Distributed Cluster |
| **Edge Delivery** | Cloudflare CDN / S3 | Low-latency global delivery of HLS segments | Global Edge Network |

---

## 3. Production Code Patterns & Architecture Examples

### **Pattern A: Resilient Video Processing Worker (BullMQ + FFmpeg)**
This TypeScript module handles asynchronous video processing tasks, pulling jobs from a Redis-backed queue, executing multi-resolution FFmpeg transcoding, and publishing status events.

```typescript
import { Worker, Job } from 'bullmq';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs/promises';
import * as path from 'path';

const execAsync = promisify(exec);

interface TranscodeJobData {
  videoId: string;
  inputPath: string;
  outputDir: string;
}

const REDIS_CONNECTION = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379', 10),
};

export const transcodeWorker = new Worker<TranscodeJobData>(
  'video-transcode-queue',
  async (job: Job<TranscodeJobData>) => {
    const { videoId, inputPath, outputDir } = job.data;
    console.info(`[Job ${job.id}] Starting transcode for video: ${videoId}`);

    try {
      await fs.mkdir(outputDir, { recursive: true });
      
      // Master HLS Playlists configuration for adaptive streaming
      // Generating 1080p, 720p, and 480p variants
      const ffmpegCommand = `
        ffmpeg -i ${inputPath} \
        -filter_complex \
        "[0:v]split=3[v1][v2][v3]; \
         [v1]scale=w=1920:h=1080[v1out]; \
         [v2]scale=w=1280:h=720[v2out]; \
         [v3]scale=w=854:h=480[v3out]" \
        -map "[v1out]" -c:v:0 libx264 -b:v:0 5M -maxrate:v:0 5.35M -bufsize:v:0 7.5M \
        -map "[v2out]" -c:v:1 libx264 -b:v:1 3M -maxrate:v:1 3.21M -bufsize:v:1 4.5M \
        -map "[v3out]" -c:v:2 libx264 -b:v:2 1.5M -maxrate:v:2 1.61M -bufsize:v:2 2.25M \
        -map 0:a -c:a aac -b:a:0 192k -b:a:1 128k -b:a:2 96k \
        -f hls \
        -hls_time 6 \
        -hls_playlist_type vod \
        -hls_segment_filename "${outputDir}/%v/segment_%03d.ts" \
        -master_pl_name master.m3u8 \
        "${outputDir}/%v/playlist.m3u8"
      `;

      await job.updateProgress(10);
      await execAsync(ffmpegCommand);
      await job.updateProgress(100);

      console.info(`[Job ${job.id}] Transcoding complete for video: ${videoId}`);
      return { success: true, manifestPath: path.join(outputDir, 'master.m3u8') };

    } catch (error: any) {
      console.error(`[Job ${job.id}] Transcoding failed: ${error.message}`);
      throw new Error(`FFmpeg processing failed: ${error.stderr || error.message}`);
    }
  },
  { 
    connection: REDIS_CONNECTION,
    concurrency: 2 // Bound CPU-heavy threads per node
  }
);

transcodeWorker.on('completed', (job) => {
  console.info(`Job ${job.id} successfully processed.`);
});

transcodeWorker.on('failed', (job, err) => {
  console.error(`Job ${job?.id} failed with error: ${err.message}`);
});
```

### **Pattern B: High-Throughput Real-Time Chat WebSocket Gateway**
Designed for live streaming interactive chat, utilizing Redis Pub/Sub to scale horizontally across multi-instance Node.js clusters.

```typescript
import { WebSocketServer, WebSocket } from 'ws';
import { createClient } from 'redis';
import { IncomingMessage } from 'http';

interface ClientSession extends WebSocket {
  userId: string;
  roomId: string;
  isAlive: boolean;
}

export class ChatGateway {
  private wss: WebSocketServer;
  private pubClient;
  private subClient;

  constructor(server: any) {
    this.wss = new WebSocketServer({ server, path: '/ws/chat' });
    
    const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
    this.pubClient = createClient({ url: redisUrl });
    this.subClient = createClient({ url: redisUrl });

    this.initRedis();
    this.initWebSocketServer();
  }

  private async initRedis() {
    await this.pubClient.connect();
    await this.subClient.connect();

    await this.subClient.pSubscribe('chat:room:*', (message, channel) => {
      const roomId = channel.split(':')[2];
      this.broadcastToRoom(roomId, message);
    });
  }

  private initWebSocketServer() {
    this.wss.on('connection', (ws: ClientSession, req: IncomingMessage) => {
      const urlParams = new URLSearchParams(req.url?.split('?')[1]);
      ws.userId = urlParams.get('userId') || 'anonymous';
      ws.roomId = urlParams.get('roomId') || 'general';
      ws.isAlive = true;

      ws.on('pong', () => { ws.isAlive = true; });

      ws.on('message', async (data: string) => {
        try {
          const payload = JSON.parse(data);
          const chatMessage = JSON.stringify({
            userId: ws.userId,
            text: payload.text,
            timestamp: Date.now()
          });

          // Publish to Redis to reach instances across the cluster
          await this.pubClient.publish(`chat:room:${ws.roomId}`, chatMessage);
        } catch (err) {
          ws.send(JSON.stringify({ error: 'Invalid message structure' }));
        }
      });

      ws.on('close', () => {
        // Clean up tracking maps if necessary
      });
    });

    // Heartbeat mechanism to drop stale connections
    setInterval(() => {
      this.wss.clients.forEach((ws: any) => {
        if (!ws.isAlive) return ws.terminate();
        ws.isAlive = false;
        ws.ping();
      });
    }, 30000);
  }

  private broadcastToRoom(roomId: string, message: string) {
    this.wss.clients.forEach((client: any) => {
      if (client.roomId === roomId && client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  }
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   ❌ **Anti-Pattern 1: Synchronous Ingestion & Transcoding**
    *   *The Trap:* Running FFmpeg inside the HTTP POST route handler when a user uploads a video.
    *   *The Consequence:* Immediate server thread starvation, dropped connections, and Gateway Timeout (504) errors under minimal concurrent load.
    *   *The Fix:* Always use an asynchronous job queue (e.g., BullMQ, RabbitMQ) and respond to the client immediately with a `202 Accepted` status.

*   ❌ **Anti-Pattern 2: Storing Binary Files in the Primary Database**
    *   *The Trap:* Saving video blobs directly into PostgreSQL/MySQL columns (`BYTEA` or `BLOB`).
    *   *The Consequence:* Database bloat, massive replication lag, ruined query optimization paths, and staggering storage costs.
    *   *The Fix:* Store raw and processed files in Object Storage (S3 / MinIO / GCS) and persist only metadata strings and CDN URL references in the database.

*   ❌ **Anti-Pattern 3: Ignoring CDN Cache Invalidation Policies**
    *   *The Trap:* Setting infinite TTLs on `.m3u8` master playlists while updating stream manifest segments.
    *   *The Consequence:* Users experience infinite loading states or watch outdated versions of edited/replaced video assets.
    *   *The Fix:* Use short TTLs (e.g., 2–5 seconds) for playlist files (`.m3u8`), while utilizing immutable file names and long-term caching (1 year) for individual segment files (`.ts` / `.m4s`).

---

## 5. Performance & Optimization Tips

1.  **Hardware Acceleration (GPU Transcoding):**
    Offload CPU-heavy H.264/HEVC encoding to dedicated hardware by passing NVIDIA NVENC or Intel QuickSync flags to FFmpeg (`-c:v h264_nvenc`). This reduces transcoding duration by up to 70% and frees compute nodes for application routing.

2.  **Adaptive Bitrate Chunk Tuning:**
    Keep HLS/DASH segment durations between **4 to 6 seconds**. Shorter segments (e.g., 2s) increase metadata overhead and manifest requests; longer segments (e.g., 10s+) increase latency during stream scrubbing and adaptation shifts.

3.  **Database Connection Pooling:**
    Configure PgBouncer in transaction pooling mode between your Node.js application services and PostgreSQL. Video platforms experience rapid bursts of metadata requests (likes, comments, view-count increments); proper connection pooling prevents database connection exhaustion.

---

## 6. Commercial License & Attribution Summary

### **Enterprise Commercial License Agreement**

*   **Copyright (c) 2026 MicroCorp AI. All Rights Reserved.**
*   **Permitted Use:** This architecture kit is licensed for internal development, modification, and deployment within commercial products owned by the purchasing entity.
*   **Restrictions:** Redistribution, resale, public posting, or inclusion of these source patterns within open-source repositories or competing developer template stores is strictly prohibited.
*   **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any direct or indirect damages arising from the deployment of these architectures in production environments.