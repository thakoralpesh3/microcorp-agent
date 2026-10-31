# HackerTube: The HN-Curation Engine — Developer Reference & Architecture Kit

---

## 1. Product Title & Value Proposition

### **HackerTube: HN-Curated Video Engine**
*Build, scale, and monetize an algorithmic video discovery platform powered by Hacker News discussion velocity.*

```
+-----------------------------------------------------------------------+
|                    HACKERTUBE ARCHITECTURE PIPELINE                   |
|                                                                       |
|  [Hacker News API] ---> [Filter: YouTube URLs] ---> [NLP / Scoring]   |
|                                                          |            |
|  [Edge Client] <--- [Optimized CDN] <--- [Redis / PostgreSQL Cache]   |
+-----------------------------------------------------------------------+
```

### **The Value Proposition**
Modern developers suffer from severe video-feed fatigue. Traditional algorithmic feeds optimize for endless scroll and rage-bait. **HackerTube** solves this by programmatically extracting, scoring, and streaming YouTube video links that organically trend on Hacker News (*Show HN*, *Ask HN*, and high-velocity submissions). 

This kit provides the complete production-grade blueprint—spanning automated ingestion pipelines, real-time caching layers, edge-optimized frontends, and monetization hooks—reducing time-to-market for a niche media startup from 3 months to 3 days.

---

## 2. Quick Start & Core Concepts

### **Core Concepts**
1. **Ingestion Polling**: Cron-driven workers polling the official Firebase-backed Hacker News API (`/v0/topstories.json`).
2. **Regex URL Normalization**: Deterministic extraction and cleaning of YouTube identifiers (handling `youtube.com/watch?v=`, `youtu.be/`, and `youtube.com/embed/` formats).
3. **Velocity Scoring Algorithm**: Ranking videos not just by upvotes, but by comment velocity decay rate ($Score = \frac{Points + 2 \times Comments}{(Hours + 2)^{1.8}}$).
4. **Edge-First Delivery**: Static generation mixed with Incremental Static Regeneration (ISR) to keep server bills near zero while maintaining sub-100ms global TTFB.

### **Syntax & Configuration Reference**

| Component | Technology | Primary Role | Configuration / Syntax Flag |
| :--- | :--- | :--- | :--- |
| **Ingestion Engine** | TypeScript / Node.js | Fetching & Parsing HN Items | `fetchMaxRetries: 3`, `timeoutMs: 5000` |
| **Data Persistence** | PostgreSQL + Prisma | Storing Metadata & Scores | `@@index([score, createdAt(sort: Desc)])` |
| **Cache Layer** | Redis / Upstash | Rate-limiting & Hot Feeds | `EXPIRE feed:trending 300` |
| **Frontend UI** | Next.js 14 (App Router)| Client Rendering & Routing | `export const revalidate = 3600` |
| **Video Player** | React-Player / Lite-YT | Zero-bloat Video Embedding | `loading="lazy"`, `nocookie: true` |

---

## 3. Production Code Patterns & Architecture Examples

### **Pattern A: Robust YouTube URL Normalizer & Extractor**
*Utility function to reliably parse raw Hacker News submission text/URLs into canonical YouTube video IDs.*

```typescript
// src/utils/youtube-parser.ts
import { URL } from 'node:url';

interface ParsedVideoResult {
  videoId: string | null;
  isValid: boolean;
}

export function extractYouTubeId(rawUrl: string): ParsedVideoResult {
  if (!rawUrl || typeof rawUrl !== 'string') {
    return { videoId: null, isValid: false };
  }

  try {
    const parsedUrl = new URL(rawUrl);
    let videoId: string | null = null;

    // Handle youtu.be/<id>
    if (parsedUrl.hostname === 'youtu.be') {
      videoId = parsedUrl.pathname.slice(1);
    } 
    // Handle youtube.com/watch?v=<id> or embed/<id> or shorts/<id>
    else if (parsedUrl.hostname.includes('youtube.com')) {
      if (parsedUrl.pathname.startsWith('/watch')) {
        videoId = parsedUrl.searchParams.get('v');
      } else if (
        parsedUrl.pathname.startsWith('/embed/') ||
        parsedUrl.pathname.startsWith('/shorts/')
      ) {
        videoId = parsedUrl.pathname.split('/')[2];
      }
    }

    // Validate YouTube ID format (11 characters, alphanumeric + underscore/hyphen)
    const isValidId = videoId ? /^[a-zA-Z0-9_-]{11}$/.test(videoId) : false;

    return {
      videoId: isValidId ? videoId : null,
      isValid: isValidId,
    };
  } catch (error) {
    // Malformed URL caught safely
    return { videoId: null, isValid: false };
  }
}
```

---

### **Pattern B: Hacker News Ingestion Worker**
*Backend synchronization service that fetches top HN stories, filters for YouTube links, and computes trend scores.*

```typescript
// src/services/ingestion.ts
import { extractYouTubeId } from '../utils/youtube-parser';

interface HNItem {
  id: number;
  title: string;
  url?: string;
  score: number;
  descendants?: number;
  time: number;
  type: string;
}

const HN_API_BASE = 'https://hacker-news.firebaseio.com/v0';

async function fetchHNItem(id: number): Promise<HNItem | null> {
  try {
    const res = await fetch(`${HN_API_BASE}/item/${id}.json`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function ingestHackerTubeFeed(): Promise<Array<{ videoId: string; rankScore: number; title: string }>> {
  const topStoriesRes = await fetch(`${HN_API_BASE}/topstories.json`);
  const storyIds: number[] = await topStoriesRes.json();
  
  // Take top 100 for processing to stay within rate-limits
  const sliceIds = storyIds.slice(0, 100);
  const items = await Promise.all(sliceIds.map(id => fetchHNItem(id)));

  const validVideos = [];
  const now = Math.floor(Date.now() / 1000);

  for (const item of items) {
    if (!item || !item.url) continue;

    const { videoId, isValid } = extractYouTubeId(item.url);
    if (!isValid || !videoId) continue;

    // Hacker News Gravity Scoring Formula (Gravity = 1.8)
    const ageInHours = (now - item.time) / 3600;
    const comments = item.descendants || 0;
    const points = item.score;
    
    const rankScore = (points + (comments * 2)) / Math.pow(ageInHours + 2, 1.8);

    validVideos.push({
      videoId,
      title: item.title,
      rankScore,
      hnId: item.id,
      points,
      comments,
      createdAt: new Date(item.time * 1000),
    });
  }

  // Sort descending by calculated score
  return validVideos.sort((a, b) => b.rankScore - a.rankScore);
}
```

---

### **Pattern C: Optimized Next.js Client Component with Lazy Video Embed**
*High-performance UI component preventing layout shift (CLS) and optimizing page load speeds.*

```tsx
// src/components/VideoCard.tsx
'use client';

import React, { useState } from 'react';

interface VideoCardProps {
  videoId: string;
  title: string;
  points: number;
  comments: number;
  rankScore: number;
}

export const VideoCard: React.FC<VideoCardProps> = ({
  videoId,
  title,
  points,
  comments,
  rankScore,
}) => {
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <div className="flex flex-col bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-lg transition hover:border-zinc-700">
      <div className="relative w-full aspect-video bg-zinc-950">
        {!isLoaded ? (
          <div 
            onClick={() => setIsLoaded(true)}
            className="absolute inset-0 cursor-pointer group flex items-center justify-center bg-cover bg-center"
            style={{ backgroundImage: `url(https://i.ytimg.com/vi/${videoId}/hqdefault.jpg)` }}
          >
            <div className="w-12 h-12 bg-red-600 rounded-full flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform">
              <div className="w-0 h-0 border-y-8 border-y-transparent border-l-12 border-l-white ml-1" />
            </div>
          </div>
        ) : (
          <iframe
            className="absolute inset-0 w-full h-full"
            src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`}
            title={title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        )}
      </div>

      <div className="p-4 flex flex-col flex-grow justify-between">
        <h3 className="text-zinc-100 font-medium text-base line-clamp-2 mb-3">
          {title}
        </h3>
        <div className="flex items-center justify-between text-xs text-zinc-400 font-mono">
          <span className="flex items-center gap-1">▲ {points} pts</span>
          <span className="flex items-center gap-1">💬 {comments} comments</span>
          <span className="text-emerald-400">Score: {rankScore.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
};
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* **❌ Anti-Pattern 1: Direct Client-Side Polling of Firebase HN API**
  * *Why*: Fetching 100+ separate item records directly from client browsers triggers CORS issues, blasts rate limits, and tanks battery life on mobile devices.
  * *Fix*: Execute ingestion on a centralized cron worker (e.g., Vercel Cron or AWS Lambda) and persist to a managed database or Redis cache.
* **❌ Anti-Pattern 2: Heavy YouTube iframe Embeds on Initial Page Load**
  * *Why*: Embedding 20+ active YouTube iframes on a single page feed will initiate dozens of heavy JavaScript payloads, trackers, and media requests, causing Lighthouse performance scores to plummet.
  * *Fix*: Use the "Facade Pattern" (Thumbnail image with click-to-load iframe state, as demonstrated in Pattern C).
* **❌ Anti-Pattern 3: Ignoring YouTube URL Parameter Variances**
  * *Why*: Assuming URLs only arrive as `youtube.com/watch?v=XYZ` leads to missed submissions from mobile shares (`youtu.be/XYZ`) and embedded references.
  * *Fix*: Always pass raw submission strings through a robust normalization parser supporting all known URL variants.

---

## 5. Performance & Optimization Tips

1. **Database Indexing**: Ensure compound indexes are active on your sorting parameters to maintain sub-10ms query execution times under heavy concurrent loads:
   ```sql
   CREATE INDEX idx_videos_score_time ON "Video" (rankScore DESC, createdAt DESC);
   ```
2. **Aggressive Cache Control**: Set appropriate caching headers on API endpoints serving the feed:
   ```typescript
   // In Next.js Route Handlers
   export const revalidate = 900; // Revalidate every 15 minutes
   ```
3. **CDN Asset Offloading**: Cache YouTube thumbnail images at your edge provider or serve them via optimized image components with WebP/AVIF conversions enabled.
4. **Virtualization**: For feeds exceeding 50 items per view, implement windowing libraries (like `@tanstack/react-virtual`) to limit DOM node bloat.

---

## 6. Commercial License & Attribution Summary

### **MicroCorp AI Commercial License (Permissive Tier 1)**
*Copyright (c) 2025 MicroCorp AI. All rights reserved.*

* **Grant of Rights**: You are free to use, modify, adapt, and compile this architecture kit into commercial software applications, internal developer tools, or SaaS products.
* **Restrictions**: You may **not** resell, re-license, or redistribute this specific documentation markdown or standalone architecture kit as a competing template package on digital marketplaces (e.g., Gumroad, ThemeForest, GitHub Marketplace) without explicit written consent from MicroCorp AI.
* **No Warranty**: Provided "as is", without warranty of any kind, express or implied. The authors shall not be held liable for any claim, damages, or liability arising from the execution or deployment of code contained herein.

---
*Built with precision by **Frontend Developer 🖥️**, The Engineering Division of The Agency for MicroCorp AI.*