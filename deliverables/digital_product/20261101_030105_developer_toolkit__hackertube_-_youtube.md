# HackerTube: YouTube Built from HN Recommendations
**The Developer Reference & Architecture Kit for Curated Video Streaming**

---

## 1. Product Title & Value Proposition

### HackerTube Architecture & Integration Kit
*Build a signal-dense, distraction-free video platform driven entirely by Hacker News community curation, RSS parsing, and zero-algorithm discovery.*

```
 ┌──────────────────────────────────────────────────────────────┐
 │                  HACKERTUBE ARCHITECTURE                     │
 ├───────────────────┬───────────────────┬──────────────────────┤
 │   HN Firebase     │   RSS Feed        │   Metadata Extractor │
 │   API / Algolia   │   Aggregator      │   & Clean Player     │
 └─────────┬─────────┴─────────┬─────────┴──────────┬───────────┘
           │                   │                    │
           └───────────────────┼────────────────────┘
                               ▼
            ┌──────────────────────────────────────┐
            │       Next.js 14 App Router API      │
            │  (Edge Caching + ISR + Tailwind v3)  │
            └──────────────────┬───────────────────┘
                               ▼
            ┌──────────────────────────────────────┐
            │    Client View: Zero Ads, No Recs,   │
            │    Pure Hacker News Discourse        │
            └──────────────────────────────────────┘
```

### Value Proposition
Modern video consumption is plagued by engagement bait, dark patterns, and infinite-scroll algorithmic addiction. **HackerTube** solves this by bridging the gap between high-signal Hacker News submissions and structured video delivery. 

This kit provides senior engineers, indie hackers, and system architects with the production-ready code, data-pipeline patterns, and frontend components required to spin up a curated video aggregator in under an hour. Eliminate algorithmic sludge and deliver a lightning-fast, accessible interface for developer talks, deep-dive demos, and technical showcases.

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts
* **Algolia-Powered Filtering:** Queries the Hacker News Firebase/Algolia search endpoint strictly for domains hosting approved video assets (`youtube.com`, `youtu.be`, `vimeo.com`) combined with keyword density filters (`show hn`, `ask hn`, `architecture`, `postmortem`).
* **Incremental Static Regeneration (ISR):** Feeds are statically generated at the edge and revalidated on background intervals, ensuring sub-50ms TTFB (Time to First Byte) without hitting upstream rate limits.
* **Sanitized Embed Layer:** Wraps standard iframe embeds in lightweight custom facades with deferred hydration to eliminate heavy third-party tracking scripts until direct user interaction occurs.

### Clean Syntax & Configuration Reference Table

| Component Layer | Technology Stack | Primary Responsibility | Performance Target |
| :--- | :--- | :--- | :--- |
| **Data Ingestion** | TypeScript / Algolia API | Fetching & validating HN items matching video domains | `< 200ms` fetch latency |
| **Caching Layer** | Vercel KV / Redis | Storing deduplicated video metadata & HN comment thread IDs | `< 10ms` cache hit |
| **Frontend UI** | Next.js 14 App Router / Tailwind CSS | Rendering responsive, accessible grid systems | `100` Lighthouse Performance |
| **Player Wrapper** | React Custom Facade | Deferring heavy iframe payloads until click-to-play | `0` layout shift (CLS) |
| **Discourse Bridge** | HN Firebase API | Pulling top-level technical comments into the sidebar | Async lazy-loaded |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Algolia & HN Data Ingestion Pipeline (`lib/hackertube.ts`)
*Production-ready TypeScript utility to fetch, filter, and normalize video submissions from Hacker News.*

```typescript
import { cache } from 'react';

export interface HackerTubeItem {
  objectID: string;
  title: string;
  url: string;
  points: number;
  author: string;
  created_at: string;
  num_comments: number;
  videoId: string;
}

const ALLOWED_DOMAINS = ['youtube.com', 'youtu.be', 'vimeo.com'];

/**
 * Extracts standard video ID from YouTube and Vimeo URLs.
 */
function extractVideoId(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('youtube.com')) {
      return parsed.searchParams.get('v');
    }
    if (parsed.hostname.includes('youtu.be')) {
      return parsed.pathname.slice(1);
    }
    if (parsed.hostname.includes('vimeo.com')) {
      const segments = parsed.pathname.split('/');
      return segments[segments.length - 1] || null;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Fetches top video submissions from Algolia HN Search API with React cache deduplication.
 */
export const getHackerTubeFeed = cache(async (): Promise<HackerTubeItem[]> => {
  const query = encodeURIComponent('video OR show hn OR architecture');
  const endpoint = `https://hn.algolia.com/api/v1/search_by_date?query=${query}&tags=story&numericFilters=points>15`;

  try {
    const res = await fetch(endpoint, { next: { revalidate: 3600 } });
    if (!res.ok) throw new Error(`Algolia API failed with status: ${res.status}`);

    const data = await res.json();
    
    const items: HackerTubeItem[] = data.hits
      .map((hit: any) => {
        if (!hit.url) return null;
        const videoId = extractVideoId(hit.url);
        if (!videoId) return null;

        return {
          objectID: hit.objectID,
          title: hit.title,
          url: hit.url,
          points: hit.points || 0,
          author: hit.author || 'unknown',
          created_at: hit.created_at,
          num_comments: hit.num_comments || 0,
          videoId,
        };
      })
      .filter((item: HackerTubeItem | null): item is HackerTubeItem => item !== null);

    return items;
  } catch (error) {
    console.error('Failed to fetch HackerTube feed:', error);
    return [];
  }
});
```

### Pattern 2: Performant Click-to-Play Video Facade (`components/VideoFacade.tsx`)
*Prevents heavy YouTube tracking scripts from blocking main-thread execution on initial page load.*

```tsx
'client';

import React, { useState } from 'react';
import Image from 'next/image';

interface VideoFacadeProps {
  videoId: string;
  title: string;
}

export const VideoFacade: React.FC<VideoFacadeProps> = ({ videoId, title }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const thumbnailUrl = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

  if (isPlaying) {
    return (
      <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-neutral-900 shadow-2xl">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&modestbranding=1&rel=0`}
          title={title}
          className="absolute top-0 left-0 w-full h-full border-0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  return (
    <div 
      onClick={() => setIsPlaying(true)}
      className="relative w-full aspect-video rounded-xl overflow-hidden bg-neutral-900 cursor-pointer group shadow-lg border border-neutral-800 transition-transform duration-200 hover:scale-[1.01]"
      role="button"
      tabIndex={0}
      aria-label={`Play video: ${title}`}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setIsPlaying(true); }}
    >
      <Image
        src={thumbnailUrl}
        alt={title}
        fill
        sizes="(max-width: 768px) 100vw, 50vw"
        className="object-cover opacity-90 group-hover:opacity-100 transition-opacity"
        priority={false}
      />
      <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/10 transition-colors">
        <div className="w-16 h-12 bg-red-600 rounded-xl flex items-center justify-center shadow-lg group-hover:bg-red-500 group-hover:scale-110 transition-all">
          <svg className="w-6 h-6 text-white translate-x-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
      <div className="absolute bottom-2 left-2 bg-black/75 px-2 py-1 rounded text-xs text-neutral-300 font-mono">
        Click to Load Embed
      </div>
    </div>
  );
};
```

### Pattern 3: Responsive Grid & Feed Component (`app/page.tsx`)
*Server Component rendering the curated HackerTube stream with Tailwind CSS typography and card layouts.*

```tsx
import { getHackerTubeFeed } from '@/lib/hackertube';
import { VideoFacade } from '@/components/VideoFacade';

export const revalidate = 3600; // Revalidate every hour

export default async function HackerTubeHomePage() {
  const videos = await getHackerTubeFeed();

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-orange-500 selection:text-white">
      <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-orange-600 rounded-lg flex items-center font-bold text-lg justify-hidden text-white shadow">
              <span className="m-auto font-mono">HT</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight">HackerTube</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-neutral-800 text-orange-400 font-mono border border-orange-500/20">
              HN Curated
            </span>
          </div>
          <p className="text-xs text-neutral-400 font-mono hidden sm:block">
            Zero Ads. No Algorithms. Pure Technical Signal.
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {videos.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-neutral-400 font-mono">No active video submissions discovered in current HN window.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {videos.map((item) => (
              <article key={item.objectID} className="flex flex-col bg-neutral-900/60 border border-neutral-800 rounded-2xl p-4 space-y-4 hover:border-neutral-700 transition-colors">
                <VideoFacade videoId={item.videoId} title={item.title} />
                
                <div className="flex-1 flex flex-col justify-between space-y-2">
                  <h2 className="font-semibold text-base leading-snug line-clamp-2 text-neutral-100 hover:text-orange-400 transition-colors">
                    <a href={item.url} target="_blank" rel="noopener noreferrer">
                      {item.title}
                    </a>
                  </h2>

                  <div className="flex items-center justify-between text-xs text-neutral-400 font-mono pt-2 border-t border-neutral-800/80">
                    <div className="flex items-center space-x-3">
                      <span className="text-orange-400 font-semibold">▲ {item.points} pts</span>
                      <span>by {item.author}</span>
                    </div>
                    <a 
                      href={`https://news.ycombinator.com/item?id=${item.objectID}`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="hover:text-white underline underline-offset-2"
                    >
                      {item.num_comments} comments
                    </a>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

* **Anti-Pattern 1: Direct Uncached Algolia Queries in Client Components**
  * *Why:* Exposes rate limits, risks burning API quotas instantly, and creates unpredictable client waterfall loading states.
  * *Correction:* Always query upstream APIs inside Server Components, Next.js Route Handlers, or centralized caching layers (`React.cache`, Vercel KV).
* **Anti-Pattern 2: Eagerly Loading YouTube Iframes in Multi-Column Grids**
  * *Why:* Loading 12+ YouTube embeds simultaneously pulls down massive JavaScript bundles, heavy iframe documents, and tracking cookies, tanking your Lighthouse performance score.
  * *Correction:* Implement the `VideoFacade` pattern shown in Section 3 to defer iframe mounting until explicit user interaction.
* **Anti-Pattern 3: Trusting Raw User-Submitted URLs Without Validation**
  * *Why:* HN submissions often point to malformed URLs, redirect chains, or non-video assets that will crash standard string manipulation functions.
  * *Correction:* Use robust `try/catch` URL parsers and strict domain allowlists before attempting video ID extraction.

---

## 5. Performance & Optimization Tips

1. **Edge Caching via ISR:** Configure `revalidate = 3600` (1 hour) on list views. Because HN submission velocity for top video threads is relatively stable, serving cached HTML from edge nodes reduces origin compute to zero for repeat visitors.
2. **Next.js Image Optimization:** Pass YouTube thumbnail URLs (`i.ytimg.com`) through Next.js `<Image />` component with explicit sizing attributes to prevent cumulative layout shift (CLS) and leverage WebP/AVIF output formats.
3. **Resource Hints & DNS Prefetching:** Add DNS prefetch tags for YouTube domains to your root layout head to accelerate TLS handshakes when users click-to-play:
   ```html
   <link rel="preconnect" href="https://www.youtube-nocookie.com" />
   <link rel="preconnect" href="https://i.ytimg.com" />
   ```

---

## 6. Commercial License & Attribution Summary

### HackerTube Commercial Developer License v1.0
* **Granted Rights:** You are free to use, modify, fork, and adapt this architecture kit for personal, internal enterprise, or commercial SaaS applications. You may bundle these patterns into client deliverables.
* **Restrictions:** You may not resell this reference document or code boilerplate as a competing standalone "Developer Kit" or template product without explicit written authorization from MicroCorp AI.
* **Disclaimer:** Provided "as-is" without warranty of any kind, express or implied. Upstream API availability (Hacker News Algolia / Firebase) remains subject to third-party uptime.
* **Attribution:** Built by Engineering Division @ MicroCorp AI. Powered by the Hacker News community discourse.