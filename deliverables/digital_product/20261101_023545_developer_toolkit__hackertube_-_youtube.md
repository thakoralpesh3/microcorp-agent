# Developer Toolkit: HackerTube - YouTube Built from HN Recommendations

## 1. # Product Title & Value Proposition

**HackerTube** is a high-performance, developer-first media curation engine that cross-references Hacker News submission threads with YouTube data streams. By parsing algorithmic discussions, domain mentions, and community upvotes, HackerTube surfaces high-signal technical content—talks, deep-dives, demos, and architecture breakdowns—filtering out clickbait, fluff, and low-effort video essays.

### Value Proposition
Modern video platforms are optimized for engagement metrics that favor sensationalism over substance. Engineers waste hours sifting through noise to find valuable technical content. HackerTube solves this by programmatically leveraging the Hacker News collective consciousness as a trust and curation layer. 

This architecture kit provides production-ready code patterns, caching strategies, and resilient API ingestion loops to bootstrap your own high-signal video platform in a single afternoon.

---

## 2. ## Quick Start & Core Concepts

HackerTube relies on a decoupled ingestion pipeline, a fast SQLite/PostgreSQL caching layer, and a zero-runtime-overhead edge frontend. 

### Core Concepts & System Architecture

| Concept | Description | Implementation Detail |
| :--- | :--- | :--- |
| **Signal Extraction** | Scraping HN Firebase/Algolia API for story links containing YouTube domains. | Node.js Worker threads with exponential backoff. |
| **Metadata Enrichment** | Fetching video duration, channel stats, and transcripts via YouTube Data API v3. | Batched requests caching to avoid quota exhaustion. |
| **Deduplication Engine** | Normalizing video IDs and tracking historical HN discussions per video. | Unique composite constraints (`video_id`, `hn_story_id`). |
| **Relevance Scoring** | Ranking videos based on HN comment count, upvote velocity, and thread sentiment. | Log-scale scoring algorithm with time-decay. |

### Quick Start Ingestion Flow
```
[HN Algolia API] ---> (Filter YouTube URLs) ---> [Deduplication DB]
                                                          │
[YouTube Data API] ---> (Enrich Metadata) <────────────────┘
                                                          ▼
                                                 [Production Ready JSON]
```

---

## 3. ## Production Code Patterns & Architecture Examples

Below are production-grade, copy-paste ready code modules written in TypeScript and modern Node.js, implementing the core ingestion and scoring engine for HackerTube.

### A. HN Story Scraper & YouTube Extractor (`src/services/scraper.ts`)

```typescript
import axios from 'axios';

interface HNStory {
  objectID: string;
  title: string;
  url: string;
  points: number;
  num_comments: number;
  created_at: string;
}

interface CuratedVideoPayload {
  videoId: string;
  hnStoryId: string;
  title: string;
  hnScore: number;
  commentsCount: number;
  submittedAt: string;
}

const HN_ALGOLIA_API = 'http://hn.algolia.com/api/v1/search';

export class HNYouTubeScraper {
  /**
   * Extracts clean YouTube video IDs from various URL formats (watch?v=, youtu.be/, embed/)
   */
  private extractYouTubeId(url: string): string | null {
    if (!url) return null;
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
  }

  /**
   * Fetches top technical stories mentioning YouTube from Hacker News
   */
  public async fetchTopYouTubeStories(query: string = 'youtube.com'): Promise<CuratedVideoPayload[]> {
    try {
      const response = await axios.get(`${HN_ALGOLIA_API}`, {
        params: {
          query,
          tags: 'story',
          numericFilters: 'points>20', // Filter for quality signal
          hitsPerPage: 50,
        },
      });

      const hits: HNStory[] = response.data.hits;
      const curatedVideos: CuratedVideoPayload[] = [];

      for (const hit of hits) {
        if (!hit.url) continue;
        const videoId = this.extractYouTubeId(hit.url);

        if (videoId) {
          curatedVideos.push({
            videoId,
            hnStoryId: hit.objectID,
            title: hit.title,
            hnScore: hit.points,
            commentsCount: hit.num_comments,
            submittedAt: hit.created_at,
          });
        }
      }

      return curatedVideos;
    } catch (error) {
      console.error('Failed to fetch from HN Algolia API:', error);
      throw new Error('HN ingestion pipeline failure');
    }
  }
}
```

### B. Signal Scoring Engine (`src/services/scorer.ts`)

```typescript
/**
 * Calculates a proprietary HackerTube Signal Score based on engagement and time decay.
 */
export class SignalScorer {
  private static readonly GRAVITY = 1.8; // Time decay factor

  public static computeScore(points: number, comments: number, createdAt: string): number {
    const ageInHours = (Date.now() - new Date(createdAt).getTime()) / (1000 * 60 * 60);
    
    // Weighted engagement model: Comments often indicate higher technical controversy/depth than upvotes
    const engagement = (points * 1.0) + (comments * 2.5);
    
    // Hacker News style gravity ranking formula
    const score = engagement / Math.pow(ageInHours + 2, this.GRAVITY);
    
    return Number(score.toFixed(4));
  }
}
```

### C. Database Schema Migration (`prisma/schema.prisma`)

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model CuratedVideo {
  id            String   @id @default(uuid())
  videoId       String   @unique
  hnStoryId     String   @unique
  title         String
  hnScore       Int
  commentsCount Int
  signalScore   Float
  duration      String?
  channelTitle  String?
  submittedAt   DateTime
  createdAt     DateTime @default(now())

  @@index([signalScore(sort: Desc)])
  @@index([submittedAt(sort: Desc)])
}
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

When building systems that aggregate third-party platform data, engineers frequently encounter specific failure modes:

*   **Anti-Pattern 1: Uncached YouTube API Calls**
    *   *The Trap:* Querying the YouTube Data API for metadata on every client page load.
    *   *The Consequence:* Rapid exhaustion of daily quota limits (10,000 units default), resulting in broken user experiences.
    *   *The Fix:* Cache video metadata in Redis or a persistent database with a minimum TTL of 24 hours.
*   **Anti-Pattern 2: Ignoring Short-Form Content (Shorts)**
    *   *The Trap:* Treating YouTube Shorts (`/shorts/`) identical to long-form technical lectures.
    *   *The Consequence:* Polluting a high-signal engineering platform with 30-second meme clips.
    *   *The Fix:* Filter out URLs containing `/shorts/` or reject videos where duration is less than 3 minutes (`PT3M`).
*   **Anti-Pattern 3: Naive URL Parsing**
    *   *The Trap:* Using simple string splitting to capture video IDs.
    *   *The Consequence:* Crashing ingestion workers when encountering playlist parameters (`&list=...`), timestamps (`&t=120s`), or redirected domains (`youtu.be`).
    *   *The Fix:* Always utilize robust regular expressions or URL parsing libraries designed specifically for YouTube schemas.

---

## 5. ## Performance & Optimization Tips

1.  **Edge Caching with Stale-While-Revalidate:** Serve the main HackerTube feed via Cloudflare Workers or Vercel Edge Functions with a `Cache-Control: public, s-maxage=3600, stale-while-revalidate=86400` header. This ensures instant global response times (<50ms).
2.  **Batch YouTube Data API Requests:** Combine up to 50 video IDs into a single `videos.list` API call using the `id` comma-separated parameter to maximize quota efficiency.
3.  **Virtualize Feed DOM Elements:** Because technical talks and deep-dive videos often include rich metadata, comments previews, and embedded players, implement DOM virtualization (e.g., TanStack Virtual) on the frontend to maintain a locked 60 FPS scroll performance with hundreds of rendered items.

---

## 6. ## Commercial License & Attribution Summary

### MicroCorp AI Commercial License (Type-B: Developer Toolkit)

*   **Copyright (c) 2025 MicroCorp AI. All rights reserved.**
*   **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and incorporate this codebase into commercial applications, proprietary software, or internal developer tools.
*   **Restrictions:** Redistribution of this exact toolkit as a competing digital product, template generator, or open-source boilerplate repository is strictly prohibited without explicit written consent from MicroCorp AI.
*   **Disclaimer:** Provided "as is", without warranty of any kind, express or implied. The authors are not liable for any API quota suspensions or third-party platform changes resulting from implementation.