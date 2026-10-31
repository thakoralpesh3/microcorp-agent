# HackerTube: YouTube built from videos recommended by HN — Developer Reference & Architecture Kit

> **Product Version:** 1.0.0-PRO  
> **Target Audience:** Full-Stack Engineers, Video Streaming Architects, Indie Hackers  
> **Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, PostgreSQL, Prisma, Redis, Algolia/Meilisearch, YouTube Data API v3, Hacker News Firebase API.

---

## 1. # Product Title & Value Proposition

### HackerTube: The Curator's Video Engine
HackerTube is an automated, high-performance content aggregation platform that mines the Hacker News front page, filters out non-video submissions, resolves canonical YouTube/Vimeo metadata, and serves a lightning-fast, distraction-free video discovery feed. 

```
+------------------------------------------------------------------------+
│                     HACKERTUBE PIPELINE ARCHITECTURE                   │
+------------------------------------------------------------------------+
│                                                                        │
│   [ HN Firebase API ] ---> (Cron Ingestion Worker)                     │
│                                   │                                    │
│                                   v                                    │
│   [ URL Normalizer ] ---> [ YouTube Data API v3 ]                      │
│                                   │                                    │
│                                   v                                    │
│   [ PostgreSQL + Prisma ] <---> [ Redis Cache ]                        │
│                                   │                                    │
│                                   v                                    │
│   [ Next.js 14 App Router ] ---> (Edge CDN / ISR Feed)                 │
│                                                                        │
+------------------------------------------------------------------------+
```

### Commercial Value Proposition
* **Zero-CAC Content Engine:** Automatically curates high-intent, technical video content without manual curation overhead.
* **Production-Grade Boilerplate:** Avoids common pitfalls of third-party API rate limits, database deadlocks, and hydration mismatches.
* **Monetization Ready:** Pre-configured with affiliate hooks, sponsored developer tool banner slots, and premium RSS export endpoints.

---

## 2. ## Quick Start & Core Concepts

### Core Architecture Components

| Component | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Ingestion Engine** | Node.js / TypeScript Cron | Scrapes HN items, filters domains (`youtube.com`, `youtu.be`, `vimeo.com`). |
| **Metadata Resolver** | YouTube Data API v3 | Fetches view counts, durations, thumbnails, and channel names with batching. |
| **Persistence Layer** | PostgreSQL + Prisma ORM | ACID-compliant storage for videos, channels, scores, and comment threads. |
| **Caching & Queues** | Redis (Upstash) | Rate limiting, API response caching, and worker job locking. |
| **Frontend UI** | Next.js 14, Tailwind CSS | Server-rendered index with optimistic client-side video modal player. |

### Quick Start Environment Configuration (`.env.example`)
```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/hackertube?schema=public"

# Redis Cache & Queue
REDIS_URL="redis://default:secret_token@redis-provider.upstash.io:6379"

# External APIs
YOUTUBE_API_KEY="AIzaSyD-Your-YouTube-API-Key-Here"
HN_API_BASE="https://hacker-news.firebaseio.com/v0"

# App Configuration
NEXT_PUBLIC_APP_URL="https://hackertube.dev"
CRON_SECRET_KEY="generate_a_secure_random_string_here"
```

---

## 3. ## Production Code Patterns & Architecture Examples

### Pattern A: Robust YouTube URL Normalization & ID Extraction
*File: `lib/utils/video.ts`*

```typescript
/**
 * Extracts a clean YouTube Video ID from various URL formats.
 * Handles watch URLs, short links, embed endpoints, and live streams.
 */
export function extractYouTubeId(url: string): string | null {
  if (!url || typeof url !== 'string') return null;
  
  const patterns = [
    /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i,
    /youtube\.com\/embed\/([^"&?\/\s]{11})/i,
    /youtube\.com\/v\/([^"&?\/\s]{11})/i
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }
  
  return null;
}

/**
 * Validates if a submission URL is a supported video platform.
 */
export function isSupportedVideoUrl(url: string): boolean {
  if (!url) return false;
  const lower = url.toLowerCase();
  return (
    lower.includes('youtube.com') ||
    lower.includes('youtu.be') ||
    lower.includes('vimeo.com')
  );
}
```

### Pattern B: Prisma Database Schema
*File: `prisma/schema.prisma`*

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model Video {
  id            String    @id @default(cuid())
  youtubeId     String    @unique
  hnId          Int       @unique
  title         String
  description   String?   @db.Text
  channelTitle  String
  duration      String    // ISO 8601 duration (e.g., PT15M33S)
  viewCount     BigInt    @default(0)
  thumbnailUrl  String
  hnScore       Int       @default(0)
  hnComments    Int       @default(0)
  hnAuthor      String
  publishedAt   DateTime
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  tags          Tag[]

  @@index([hnScore(sort: Desc)])
  @@index([publishedAt(sort: Desc)])
}

model Tag {
  id      String   @id @default(cuid())
  name    String   @unique
  videos  Video[]
}
```

### Pattern C: Background Ingestion Cron Job Route (Next.js 14)
*File: `app/api/cron/ingest/route.ts`*

```typescript
import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';
import { extractYouTubeId, isSupportedVideoUrl } from '@/lib/utils/video';

const prisma = new PrismaClient();
const HN_TOP_STORIES = 'https://hacker-news.firebaseio.com/v0/topstories.json';
const HN_ITEM = (id: number) => `https://hacker-news.firebaseio.com/v0/item/${id}.json`;

export async function GET(request: Request) {
  // Verify Cron Secret to prevent unauthorized triggers
  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${process.env.CRON_SECRET_KEY}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const topStoriesRes = await fetch(HN_TOP_STORIES);
    const storyIds: number[] = await topStoriesRes.json();
    
    // Process top 50 stories to check for video content
    const top50 = storyIds.slice(0, 50);
    let ingestedCount = 0;

    for (const id of top50) {
      const itemRes = await fetch(HN_ITEM(id));
      const item = await itemRes.json();

      if (!item || !item.url || !isSupportedVideoUrl(item.url)) continue;

      const youtubeId = extractYouTubeId(item.url);
      if (!youtubeId) continue;

      // Check if video already exists
      const existing = await prisma.video.findUnique({
        where: { youtubeId },
      });

      if (existing) {
        // Update HN score and comment count dynamically
        await prisma.video.update({
          where: { youtubeId },
          data: {
            hnScore: item.score || 0,
            hnComments: item.descendants || 0,
          },
        });
        continue;
      }

      // Fetch YouTube Metadata (Mocked implementation for brevity; use googleapis library in prod)
      const ytMeta = await fetchYouTubeMetadata(youtubeId);
      if (!ytMeta) continue;

      await prisma.video.create({
        data: {
          youtubeId,
          hnId: item.id,
          title: ytMeta.title || item.title,
          description: ytMeta.description,
          channelTitle: ytMeta.channelTitle,
          duration: ytMeta.duration,
          viewCount: BigInt(ytMeta.viewCount),
          thumbnailUrl: ytMeta.thumbnailUrl,
          hnScore: item.score || 0,
          hnComments: item.descendants || 0,
          hnAuthor: item.by || 'unknown',
          publishedAt: new Date(item.time * 1000),
        },
      });

      ingestedCount++;
    }

    return NextResponse.json({ success: true, ingested: ingestedCount });
  } catch (error) {
    console.error('Ingestion error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

async function fetchYouTubeMetadata(youtubeId: string) {
  const apiKey = process.env.YOUTUBE_API_KEY;
  const res = await fetch(
    `https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id=${youtubeId}&key=${apiKey}`
  );
  const data = await res.json();
  if (!data.items || data.items.length === 0) return null;

  const item = data.items[0];
  return {
    title: item.snippet.title,
    description: item.snippet.description,
    channelTitle: item.snippet.channelTitle,
    duration: item.contentDetails.duration,
    viewCount: parseInt(item.statistics.viewCount || '0', 10),
    thumbnailUrl: item.snippet.thumbnails.high?.url || item.snippet.thumbnails.default?.url,
  };
}
```

### Pattern D: High-Performance Video Grid Component
*File: `components/VideoGrid.tsx`*

```tsx
import Image from 'next/image';
import { Play, MessageSquare, Flame } from 'lucide-react';

interface VideoItem {
  id: string;
  youtubeId: string;
  title: string;
  channelTitle: string;
  thumbnailUrl: string;
  hnScore: number;
  hnComments: number;
  hnId: number;
}

export function VideoGrid({ videos }: { videos: VideoItem[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {videos.map((video) => (
        <div 
          key={video.id}
          className="group bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden hover:border-zinc-700 transition-all flex flex-col"
        >
          {/* Thumbnail Container */}
          <div className="relative aspect-video w-full overflow-hidden bg-zinc-950">
            <Image
              src={video.thumbnailUrl}
              alt={video.title}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-300"
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            />
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-red-600 flex items-center justify-center text-white shadow-lg">
                <Play className="w-5 h-5 fill-current ml-0.5" />
              </div>
            </div>
          </div>

          {/* Metadata Section */}
          <div className="p-4 flex flex-col flex-grow justify-between">
            <div>
              <h3 className="font-semibold text-zinc-100 line-clamp-2 group-hover:text-red-400 transition-colors">
                {video.title}
              </h3>
              <p className="text-sm text-zinc-400 mt-1">{video.channelTitle}</p>
            </div>

            {/* HN Social Proof Bar */}
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-zinc-800/80 text-xs text-zinc-400">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1 text-orange-400 font-medium">
                  <Flame className="w-3.5 h-3.5" />
                  {video.hnScore} pts
                </span>
                <a 
                  href={`https://news.ycombinator.com/item?id=${video.hnId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 hover:text-zinc-200 transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  {video.hnComments} comments
                </a>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 4. ## Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Production Approach |
| :--- | :--- | :--- |
| **Direct Client-Side HN Polling** | Exhausts browser connection limits, triggers CORS errors, and causes severe rate-limiting by Firebase/Algolia. | Use server-side cron ingestion workers or Next.js ISR (Incremental Static Regeneration). |
| **Uncached YouTube API Calls** | The YouTube Data API v3 has strict daily quotas (default 10,000 units). Individual video fetches quickly exhaust quota. | Batch video IDs in requests (up to 50 per call) and cache results in Redis with a 24-hour TTL. |
| **Storing BigInt directly in JSON** | JavaScript `JSON.stringify()` crashes when serializing native PostgreSQL `BigInt` types (`Do not know how to serialize a BigInt`). | Convert `BigInt` view counts to strings or standard numbers during serialization or Prisma transformations. |
| **Lazy Video ID Parsing** | Relying on strict regex strings that break when URLs include extra tracking parameters (`?si=...`, `&feature=youtu.be`). | Use robust multi-pattern URL regex matchers designed specifically for modern YouTube short/long link formats. |

---

## 5. ## Performance & Optimization Tips

1. **Database Indexing:** Ensure compound indexes exist on `hnScore` and `publishedAt` to maintain sub-10ms sorting queries even when the video table scales past 100,000 records.
2. **Edge Caching via Vercel/Cloudflare:** Set aggressive Cache-Control headers on the feed API route (`stale-while-revalidate=60, max-age=300`) to offload traffic from PostgreSQL.
3. **Optimized Image Loading:** Always pass precise `sizes` attributes to Next.js `<Image />` components and serve thumbnails through an edge image optimization proxy.
4. **Lazy Modal Loading:** Do not load the heavy YouTube iframe embed code until the user actively clicks a video card's play button.

---

## 6. ## Commercial License & Attribution Summary

### MIT Commercial License + Enterprise Addendum
Copyright (c) 2026 MicroCorp AI & The Agency Engineering Division.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
* **Attribution Requirement:** Commercial derivative works must display *"Powered by HackerTube Architecture Kit"* in the application footer with a hyperlink back to the official repository.