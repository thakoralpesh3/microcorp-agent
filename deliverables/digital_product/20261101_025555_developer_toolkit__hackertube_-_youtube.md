# HackerTube: YouTube Built from HN Recommendations — Developer Toolkit & Architecture Kit

---

## 1. Product Title & Value Proposition

### **HackerTube: The HN-Curation Engine Developer Kit**
*Build a high-signal, zero-algorithm video discovery platform driven entirely by curated Hacker News submissions, discussions, and community consensus.*

```
+---------------------------------------------------------------------------+
|                          HACKERTUBE ARCHITECTURE                          |
|                                                                           |
|   +--------------+      +---------------+      +-----------------------+  |
|   | Hacker News  | ---> |  Ingestion &  | ---> |  Semantic Extraction  |  |
|   | Firebase API |      | Filtering Worker|    |     (LLM / Regex)     |  |
|   +--------------+      +---------------+      +-----------------------+  |
|                                                            |              |
|   +--------------+      +---------------+                  v              |
|   |    Client    | <--- |   PostgreSQL  | <---     +------------------+   |
|   |   Frontend   |      |  (Timescale)  |          | YouTube Metadata |   |
|   +--------------+      +---------------+          |       API        |   |
|         ^                                          +------------------+   |
|         |________________ (WebSockets / REST) ______________|             |
+---------------------------------------------------------------------------+
```

### **The Value Proposition**
Modern video platforms are overrun with engagement-bait, sensationalist thumbnails, and opaque recommendation loops designed to maximize screen time rather than cognitive yield. **HackerTube** strips away the noise. It ingests links shared across Hacker News (`Show HN`, `Ask HN`, top-voted submissions) that point to video platforms, matches them against rich community discussions, and presents them in a lightning-fast, distraction-free interface.

This kit provides the complete production-grade blueprint, database schemas, API ingestion workers, and UI component architecture required to spin up an independent, monetization-ready video aggregator in under 48 hours.

---

## 2. Quick Start & Core Concepts

### **Core Concepts**
1. **Signal-to-Noise Filtering:** Instead of raw view counts, ranking is computed using a derivative of the HN Hacker ranking formula combined with comment sentiment and discussion depth.
2. **Deterministic Ingestion:** Polling the Firebase/Algolia HN search API hourly for new submissions matching domains (`youtube.com`, `youtu.be`, `vimeo.com`, `asciinema.org`).
3. **Contextual Enrichment:** Embedding the top 3 HN comment summaries directly beneath the video player to preserve community discourse.

### **Syntax & Configuration Reference**

| Component | Technology | Purpose | Key Configuration Variable |
| :--- | :--- | :--- | :--- |
| **Ingestion Engine** | Node.js / TypeScript | Polls HN APIs & extracts video IDs | `HN_POLL_INTERVAL_MS=3600000` |
| **Metadata Resolver**| Python / FastAPI | Fetches YouTube Data API v3 info | `YOUTUBE_API_KEY=AIzaSy...` |
| **Database** | PostgreSQL + Prisma | Stores items, threads, and scores | `DATABASE_URL=postgresql://...` |
| **Frontend** | Next.js 14 (App Router)| Renders SSR views & media player | `NEXT_PUBLIC_API_BASE=...` |
| **Caching Layer** | Redis | Rate-limiting & feed caching | `REDIS_URL=redis://localhost:6379` |

---

## 3. Production Code Patterns & Architecture Examples

### **Pattern A: Robust Hacker News Video Link Inserter (TypeScript)**
*This worker fetches top stories, filters for video domains, extracts video IDs, and upserts them into PostgreSQL.*

```typescript
// workers/ingestor.ts
import { PrismaClient } from '@prisma/client';
import axios from 'axios';

const prisma = new PrismaClient();
const HN_TOP_STORIES_URL = 'https://hacker-news.firebaseio.com/v0/topstories.json';
const HN_ITEM_URL = (id: number) => `https://hacker-news.firebaseio.com/v0/item/${id}.json`;

interface HNItem {
  id: number;
  title: string;
  url?: string;
  score: number;
  by: string;
  time: number;
  descendants?: number;
}

function extractVideoId(url: string): { platform: 'youtube' | 'vimeo' | 'asciinema'; id: string } | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('youtube.com') || parsed.hostname.includes('youtu.be')) {
      const videoId = parsed.hostname.includes('youtu.be')
        ? parsed.pathname.slice(1)
        : parsed.searchParams.get('v');
      return videoId ? { platform: 'youtube', id: videoId } : null;
    }
    if (parsed.hostname.includes('vimeo.com')) {
      const id = parsed.pathname.split('/')[1];
      return id ? { platform: 'vimeo', id } : null;
    }
    if (parsed.hostname.includes('asciinema.org')) {
      const id = parsed.pathname.split('/')[1];
      return id ? { platform: 'asciinema', id } : null;
    }
  } catch {
    // Invalid URL formatting
  }
  return null;
}

export async function ingestTopStories() {
  console.log('🔄 Starting HN ingestion cycle...');
  const { data: topIds } = await axios.get<number[]>(HN_TOP_STORIES_URL);
  
  // Process top 50 stories to prevent rate-limiting and overhead
  const sample = topIds.slice(0, 50);

  for (const id of sample) {
    try {
      const { data: item } = await axios.get<HNItem>(HN_ITEM_URL(id));
      if (!item || !item.url) continue;

      const videoMeta = extractVideoId(item.url);
      if (!videoMeta) continue;

      await prisma.video.upsert({
        where: { hnId: item.id },
        update: {
          score: item.score,
          commentsCount: item.descendants || 0,
        },
        create: {
          hnId: item.id,
          title: item.title,
          url: item.url,
          platform: videoMeta.platform,
          videoId: videoMeta.id,
          score: item.score,
          commentsCount: item.descendants || 0,
          author: item.by,
          publishedAt: new Date(item.time * 1000),
        },
      });
      console.log(`✅ Upserted video: [${videoMeta.platform}] ${item.title}`);
    } catch (err) {
      console.error(`❌ Failed processing item ${id}:`, err);
    }
  }
  console.log('✨ Ingestion cycle complete.');
}
```

---

### **Pattern B: Prisma Database Schema**
*Optimized relational schema supporting videos, discussions, tags, and vote metrics.*

```prisma
// prisma/schema.prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

enum Platform {
  youtube
  vimeo
  asciinema
}

model Video {
  id             String      @id @default(uuid())
  hnId           Int         @unique
  title          String
  url            String
  platform       Platform
  videoId        String
  score          Int         @default(0)
  commentsCount  Int         @default(0)
  author         String
  duration       Int?        // in seconds
  thumbnailUrl   String?
  publishedAt    DateTime
  createdAt      DateTime    @default(now())
  updatedAt      DateTime    @updatedAt
  discussions    Comment[]
  tags           Tag[]       @relation("VideoTags")

  @@index([score(sort: Desc)])
  @@index([publishedAt(sort: Desc)])
}

model Comment {
  id        String   @id @default(uuid())
  hnCommentId Int    @unique
  videoId   String
  video     Video    @relation(fields: [videoId], references: [id], onDelete: Cascade)
  author    String
  text      String
  upvotes   Int      @default(0)
  createdAt DateTime
}

model Tag {
  id      String   @id @default(uuid())
  name    String   @unique
  videos  Video[]  @relation("VideoTags")
}
```

---

### **Pattern C: Next.js 14 Video Feed Component with Tailwind CSS**
*A clean, high-performance card grid rendering ingested HackerTube metadata.*

```tsx
// app/components/VideoGrid.tsx
import React from 'react';
import Image from 'next/image';
import { MessageSquare, ThumbsUp, ExternalLink } from 'lucide-react';

interface VideoCardProps {
  id: string;
  title: string;
  platform: string;
  videoId: string;
  score: number;
  commentsCount: number;
  author: string;
  publishedAt: string;
}

export function VideoCard({
  title,
  platform,
  videoId,
  score,
  commentsCount,
  author,
  publishedAt,
}: VideoCardProps) {
  const thumbUrl = platform === 'youtube' 
    ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`
    : '/placeholder-thumb.jpg';

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden hover:border-orange-500 transition-all duration-200 flex flex-col justify-between">
      <div>
        <div className="relative aspect-video w-full bg-neutral-950">
          <Image
            src={thumbUrl}
            alt={title}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, 33vw"
          />
          <span className="absolute top-2 left-2 bg-neutral-950/80 text-orange-400 text-xs font-mono px-2 py-1 rounded uppercase tracking-wider backdrop-blur-sm">
            {platform}
          </span>
        </div>
        <div className="p-4">
          <h3 className="text-neutral-100 font-semibold text-base line-clamp-2 hover:text-orange-400 cursor-pointer">
            {title}
          </h3>
          <p className="text-neutral-400 text-xs mt-1">
            Submitted by <span className="text-neutral-300">{author}</span> • {new Date(publishedAt).toLocaleDateString()}
          </p>
        </div>
      </div>
      
      <div className="px-4 py-3 bg-neutral-950/50 border-t border-neutral-800/60 flex items-center justify-between text-xs text-neutral-400">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1 text-orange-400 font-medium">
            <ThumbsUp className="w-3.5 h-3.5" />
            <span>{score}</span>
          </span>
          <span className="flex items-center space-x-1 hover:text-neutral-200 cursor-pointer">
            <MessageSquare className="w-3.5 h-3.5" />
            <span>{commentsCount} discussion</span>
          </span>
        </div>
        <ExternalLink className="w-3.5 h-3.5 hover:text-white cursor-pointer" />
      </div>
    </div>
  );
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Production Approach |
| :--- | :--- | :--- |
| **Direct Client-Side HN Fetching** | Exposes rate limits, causes CORS errors, and floods the Firebase API with thousands of redundant requests. | Ingest items server-side via a cron worker into a dedicated SQL read-model. |
| **Ignoring YouTube Embed Policies** | Embedding videos with `autoplay=1` or missing `allowfullscreen` breaks mobile UX and violates terms. | Use strict sandboxed iframe attributes (`allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"`). |
| **Relying Solely on Video Titles** | HN submissions often have renamed or editorialized titles that differ from the actual YouTube video title, causing user confusion. | Store both the `hnTitle` and `resolvedVideoTitle` to preserve community intent while offering accurate video identification. |
| **Unindexed SQL Queries on Feed Sorting** | Sorting millions of rows by `score` or `publishedAt` without compound database indexes collapses API latency. | Maintain explicit single-column and multi-column indexes (`@@index([score(sort: Desc)])`). |

---

## 5. Performance & Optimization Tips

1. **Incremental Static Regeneration (ISR):** Serve the main HackerTube feed via Next.js ISR with a revalidate timer (`export const revalidate = 900; // 15 mins`). This ensures instant TTFB (Time to First Byte) while keeping data fresh.
2. **Edge Caching via Cloudflare:** Cache immutable video metadata responses at the edge, invalidating only when the cron worker registers a new ingestion batch.
3. **Lazy Hydration of Comments:** Do not load Hacker News discussion trees synchronously on initial page load. Fetch them lazily when the user expands the "HN Discussion" accordion pane.
4. **Thumbnail Optimization:** Use Next.js `<Image />` component with custom domains configured to leverage WebP/AVIF transformations, slashing bandwidth costs by up to 60%.

---

## 6. Commercial License & Attribution Summary

### **MicroCorp AI Commercial License (v1.0)**

* **Copyright (c) 2025 MicroCorp AI. All rights reserved.**
* **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, adapt, and deploy this codebase for internal, commercial, and client-facing projects.
* **Restrictions:** Redistribution of this exact source code package or derivative kits as a competing developer template, boilerplate store, or open-source commercial framework is strictly prohibited without written consent from MicroCorp AI.
* **Warranty Disclaimer:** This software is provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claim, damages, or liabilities arising from the deployment of this architecture.