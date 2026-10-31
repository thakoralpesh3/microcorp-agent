# HackerTube: YouTube Built from HN Recommendations
**Developer Reference & Architecture Kit**  
*A production-grade blueprint for building a high-performance, minimalist video discovery platform powered entirely by Hacker News discussion metadata, curated APIs, and edge-first delivery.*

---

## 1. Product Title & Value Proposition

### Product Title
**HackerTube: The HN-Curated Video Engine**

### Value Proposition
Modern video consumption platforms are engineered for infinite scroll, dopamine loops, and ad-driven algorithmic sludge. Developers and high-signal learners need high-density, low-noise video curation. 

**HackerTube** solves this by programmatically parsing Hacker News submissions for video links (YouTube, Vimeo, ODDcast, custom hosts), cross-referencing them with community comment sentiment and upvote velocity, and serving them via a lightning-fast, distraction-free interface. 

This kit provides the complete architectural blueprint, database schemas, API ingestion workers, and frontend component patterns required to build, scale, and monetize your own instance of HackerTube in under 48 hours.

---

## 2. Quick Start & Core Concepts

### Core Concepts

```
[ Hacker News Firebase API ] 
         │
         ▼
[ Ingestion Worker (Cron) ] ──( Filter for Video Domains )
         │
         ▼
[ Supabase / PostgreSQL ] ──( Store Metadata & HN Score )
         │
         ▼
[ Next.js Edge Router ] ──( SSR + ISR Caching )
         │
         ▼
[ Tailwind CSS Client ] ──( Distraction-Free Player UI )
```

### System Architecture Syntax Table

| Layer | Technology Choice | Primary Responsibility | Performance Target |
| :--- | :--- | :--- | :--- |
| **Ingestion** | TypeScript / Node.js | Fetching top HN stories, parsing domains, filtering noise. | < 500ms execution per batch |
| **Database** | PostgreSQL / Supabase | Relational storage for submissions, scores, and comment counts. | < 15ms query latency |
| **API / Edge** | Next.js App Router | Edge-cached JSON endpoints and Server-Side Rendered views. | < 50ms TTFB globally |
| **Frontend** | Tailwind CSS / React | Minimalist UI, embed isolation, keyboard-driven navigation. | 100 Lighthouse Performance score |

---

## 3. Production Code Patterns & Architecture Examples

### A. HN Ingestion Worker (`lib/ingestor.ts`)
This script queries the official Hacker News Firebase API, extracts URLs matching video providers, and upserts them into PostgreSQL with their current score and rank.

```typescript
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || '';
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

const HN_TOP_STORIES_URL = 'https://hacker-news.firebaseio.com/v0/topstories.json';
const HN_ITEM_URL = (id: number) => `https://hacker-news.firebaseio.com/v0/item/${id}.json`;

const VIDEO_DOMAINS = ['youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv'];

interface HNItem {
  id: number;
  title: string;
  url?: string;
  score: number;
  by: string;
  time: number;
  descendants?: number;
}

function isVideoUrl(urlStr?: string): boolean {
  if (!urlStr) return false;
  try {
    const { hostname } = new URL(urlStr);
    return VIDEO_DOMAINS.some(domain => hostname.includes(domain));
  } catch {
    return false;
  }
}

export async function ingestHackerTubeFeed(): Promise<void> {
  console.info('🚀 Starting HackerTube ingestion cycle...');
  
  const res = await fetch(HN_TOP_STORIES_URL);
  const storyIds: number[] = await res.json();
  
  // Fetch top 100 stories concurrently (batched)
  const top100Ids = storyIds.slice(0, 100);
  const promises = top100Ids.map(id => fetch(HN_ITEM_URL(id)).then(r => r.json()));
  const items: HNItem[] = await Promise.all(promises);

  const videoItems = items.filter(item => isVideoUrl(item?.url));

  console.info(`📦 Found ${videoItems.length} video items out of 100 top stories.`);

  for (const item of videoItems) {
    const { error } = await supabase
      .from('hackertube_videos')
      .upsert({
        hn_id: item.id,
        title: item.title,
        url: item.url,
        score: item.score,
        author: item.by,
        comment_count: item.descendants || 0,
        submitted_at: new Date(item.time * 1000).toISOString(),
        updated_at: new Date().toISOString()
      }, { onConflict: 'hn_id' });

    if (error) {
      console.error(`❌ Failed to upsert HN item ${item.id}:`, error.message);
    }
  }

  console.info('✨ Ingestion cycle completed successfully.');
}
```

### B. Database Schema (`supabase/migrations/20260330_init.sql`)
Optimized schema with indexes built for sorting by HN community score, time decay algorithms, and fast lookups.

```sql
create table public.hackertube_videos (
    id uuid default gen_random_uuid() primary key,
    hn_id bigint unique not null,
    title text not null,
    url text not null,
    score integer default 0 not null,
    comment_count integer default 0 not null,
    author text not null,
    submitted_at timestamp with time zone not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes for high-performance sorting and lookups
create index idx_hackertube_score on public.hackertube_videos(score desc);
create index idx_hackertube_submitted on public.hackertube_videos(submitted_at desc);
create index idx_hackertube_hn_id on public.hackertube_videos(hn_id);

-- Enable Row Level Security (RLS)
alter table public.hackertube_videos enable row level security;

-- Public read-only policy
create policy "Allow public read access"
    on public.hackertube_videos
    for select
    using (true);
```

### C. Frontend Video Card Component (`components/VideoCard.tsx`)
A pristine, responsive video card with embedded player isolation and zero-layout-shift design.

```tsx
'use client';

import React, { useState } from 'react';

interface VideoCardProps {
  title: string;
  url: string;
  score: number;
  commentCount: number;
  author: string;
  hnId: number;
  submittedAt: string;
}

function extractYouTubeId(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('youtu.be')) {
      return parsed.pathname.slice(1);
    }
    return parsed.searchParams.get('v');
  } catch {
    return null;
  }
}

export const VideoCard: React.FC<VideoCardProps> = ({
  title,
  url,
  score,
  commentCount,
  author,
  hnId,
  submittedAt,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const ytId = extractYouTubeId(url);

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden hover:border-neutral-700 transition-all flex flex-col justify-between">
      <div className="relative aspect-video bg-neutral-950 flex items-center justify-center">
        {isPlaying && ytId ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${ytId}?autoplay=1`}
            title={title}
            className="w-full h-full absolute inset-0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        ) : (
          <div 
            onClick={() => ytId && setIsPlaying(true)}
            className="cursor-pointer group w-full h-full flex items-center justify-center bg-cover bg-center relative"
            style={{ backgroundImage: ytId ? `url(https://img.youtube.com/vi/${ytId}/hqdefault.jpg)` : 'none' }}
          >
            <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 transition-colors" />
            <div className="z-10 bg-orange-600 text-white p-3 rounded-full shadow-lg group-hover:scale-110 transition-transform">
              <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </div>
        )}
      </div>

      <div className="p-5 flex flex-col flex-grow justify-between space-y-4">
        <div>
          <div className="flex items-center space-x-2 text-xs text-neutral-400 mb-2">
            <span className="text-orange-500 font-semibold">▲ {score} pts</span>
            <span>•</span>
            <span>by {author}</span>
            <span>•</span>
            <time>{new Date(submittedAt).toLocaleDateString()}</time>
          </div>
          <h3 className="text-white font-medium text-base line-clamp-2 leading-snug">
            {title}
          </h3>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-neutral-800 text-xs">
          <a
            href={`https://news.ycombinator.com/item?id=${hnId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-orange-400 transition-colors flex items-center space-x-1"
          >
            <span>💬 {commentCount} HN Comments</span>
          </a>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-white transition-colors"
          >
            Original Link ↗
          </a>
        </div>
      </div>
    </div>
  );
};
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Direct Client-Side Polling of HN Firebase API
* **The Mistake:** Making hundreds of browser-side fetches directly to `hacker-news.firebaseio.com` to render the feed.
* **Why it fails:** CORS restrictions, rate-limiting, and horrendous client latency.
* **The Fix:** Ingest data via a secure backend cron worker into a dedicated database, and serve clients through your own optimized API/Edge layer.

### ❌ Anti-Pattern 2: Uncached YouTube Embeds Causing Bloat
* **The Mistake:** Loading standard `youtube.com/embed` with heavy tracking cookies and recommended videos from external channels.
* **Why it fails:** Destroys privacy, triggers heavy JS execution, and distracts users with algorithmic rabbit holes.
* **The Fix:** Always use `youtube-nocookie.com` domains and isolate the iframe inside a clean aspect-ratio wrapper with click-to-load mechanics.

### ❌ Anti-Pattern 3: Ignoring Hacker News Score Velocity
* **The Mistake:** Sorting videos strictly by raw historical score (all-time top).
* **Why it fails:** Stale links from 2018 dominate the feed, completely missing today's vital engineering talks.
* **The Fix:** Implement a recency-weighted ranking algorithm or offer distinct tab views: *Trending (24h)*, *Top (Week)*, and *All-Time*.

---

## 5. Performance & Optimization Tips

1. **Edge ISR (Incremental Static Regeneration):** Configure Next.js pages to revalidate every 300 seconds (`revalidate = 300`). This ensures lightning-fast static delivery while automatically picking up newly ingested videos.
2. **Database Connection Pooling:** Use **Supabase PgBouncer** (Transaction Mode) for all ingestion cron jobs to prevent connection exhaustion under high concurrency.
3. **Optimized Thumbnail Loading:** Instead of fetching full video payloads, pre-compute YouTube thumbnail URLs directly from parsed IDs (`https://img.youtube.com/vi/{id}/hqdefault.jpg`), saving bandwidth and eliminating third-party API dependencies.
4. **CSS Containment:** Apply `content-visibility: auto` to video grid cards rendered below the fold to drastically reduce initial DOM painting overhead on mobile devices.

---

## 6. Commercial License & Attribution Summary

### License Type: **MicroCorp AI Commercial Developer License v1.0**

* **Permitted Use:** You are free to use, modify, fork, and commercialize this codebase to build proprietary applications, SaaS products, internal tools, or client deliverables.
* **Restrictions:** You may not resell, re-license, or redistribute this specific architectural reference kit as an isolated developer template or boilerplate on marketplaces (e.g., Gumroad, ThemeForest, GitHub Marketplace) without express written consent from MicroCorp AI.
* **Attribution:** Inclusion of copyright headers in source files is appreciated but not mandatory for deployed commercial applications.
* **Warranty:** Provided *"as is"* without warranty of any kind. MicroCorp AI disclaims all liability for API changes made by third-party services (such as Hacker News or YouTube).