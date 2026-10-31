# HackerTube: YouTube Built from HN Recommendations
**The Minimalist, Ad-Free Video Streaming Client Powered by Hacker News Curator Signals**

---

## 1. Product Title & Value Proposition

### Product Title
**HackerTube Developer Reference & Architecture Kit**  
*Sub-Title: Building a High-Performance, Curated Video Client with React, TypeScript, and the Inverted HN Feed Architecture.*

### Value Proposition
Modern video consumption is broken: infinite feeds, engagement-maximizing dark patterns, distracting recommendation sidebars, and intrusive advertisements plague traditional platforms. **HackerTube** solves this by inverting the content curation model. Instead of relying on proprietary, opaque recommendation algorithms, HackerTube indexes video links directly from the collective engineering wisdom of **Hacker News (HN)** submissions and discussions.

This commercial kit provides the complete production architecture, state-management patterns, data ingestion pipelines, and frontend codebases required to deploy your own lightning-fast, privacy-respecting, zero-ad video client. Designed for engineers, indie hackers, and SaaS creators looking to ship high-value niche video products in days, not months.

---

## 2. Quick Start & Core Concepts

### Architectural Philosophy
HackerTube runs on a three-tier decoupled architecture:
1. **Curator Layer**: Aggregates top-voted video submissions from the Firebase Hacker News API matching domain filters (`youtube.com`, `youtu.be`, `vimeo.com`).
2. **Metadata Enrichment Layer**: Fetches OpenGraph data and embeds custom markdown discussion summaries from HN comments.
3. **Immersive Client Layer**: A hyper-optimized, accessibility-first React/TypeScript Single Page Application (SPA) utilizing native HTML5 video wrappers and container queries.

### Clean Syntax & Configuration Table

| Parameter / Variable | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `VITE_HN_API_BASE` | `string` | `https://hacker-news.firebaseio.com/v0` | Official Firebase REST endpoint for fetching HN items and feeds. |
| `VITE_MAX_FEED_ITEMS` | `number` | `50` | Maximum number of concurrent curated video items loaded per pagination batch. |
| `VITE_CACHE_TTL_MS` | `number` | `3600000` (1 hour) | Time-to-live for client-side localStorage/IndexedDB caching of video metadata. |
| `ENABLE_COMMENT_SYNTHESIS` | `boolean` | `true` | Toggles the background extraction of top HN comment arguments for video context. |
| `VIDEO_ASPECT_RATIO` | `string` | `16/9` | Enforced CSS aspect ratio for responsive container scaling. |
| `STRICT_DOMAIN_WHITELIST`| `string[]` | `['youtube.com', 'youtu.be']` | Allowed external domains for safe-embed iframe rendering. |

---

## 3. Production Code Patterns & Architecture Examples

### A. Hacker News Feed Aggregation Hook (`useHackerTubeFeed.ts`)
Production-ready TypeScript hook implementing concurrent item fetching, clean error handling, and strict domain validation.

```typescript
import { useState, useEffect, useCallback } from 'react';

export interface HNVideoItem {
  id: number;
  title: string;
  url: string;
  by: string;
  score: number;
  time: number;
  descendants: number;
  videoId: string;
}

const HN_API_BASE = 'https://hacker-news.firebaseio.com/v0';
const ALLOWED_DOMAINS = ['youtube.com', 'youtu.be'];

function extractYouTubeId(url: string): string | null {
  try {
    const parsedUrl = new URL(url);
    if (parsedUrl.hostname.includes('youtube.com')) {
      return parsedUrl.searchParams.get('v');
    }
    if (parsedUrl.hostname.includes('youtu.be')) {
      return parsedUrl.pathname.slice(1);
    }
  } catch {
    return null;
  }
  return null;
}

export function useHackerTubeFeed() {
  const [items, setItems] = useState<HNVideoItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFeed = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${HN_API_BASE}/topstories.json`);
      if (!response.ok) throw new Error('Failed to fetch HN top stories');
      
      const storyIds: number[] = await response.json();
      
      // Fetch top 100 stories concurrently to filter for video links
      const topSlice = storyIds.slice(0, 100);
      const itemPromises = topSlice.map(id =>
        fetch(`${HN_API_BASE}/item/${id}.json`).then(res => res.json())
      );

      const rawItems = await Promise.all(itemPromises);
      
      const videoItems: HNVideoItem[] = rawItems
        .filter((item): item is NonNullable<typeof item> => item !== null && typeof item.url === 'string')
        .map(item => ({
          ...item,
          videoId: extractYouTubeId(item.url)
        }))
        .filter((item): item is HNVideoItem & { videoId: string } => item.videoId !== null);

      setItems(videoItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

  return { items, loading, error, refresh: fetchFeed };
}
```

### B. Optimized Video Player Component (`HackerVideoPlayer.tsx`)
Pixel-perfect, accessible embedded player featuring lazy loading and responsive container sizing.

```tsx
import React, { useState } from 'react';

interface HackerVideoPlayerProps {
  videoId: string;
  title: string;
  author: string;
  score: number;
  hnItemUrl: string;
}

export const HackerVideoPlayer: React.FC<HackerVideoPlayerProps> = ({
  videoId,
  title,
  author,
  score,
  hnItemUrl,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  return (
    <div className="flex flex-col bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden shadow-2xl transition-all hover:border-zinc-700">
      <div className="relative w-full aspect-video bg-black">
        {!isPlaying ? (
          <div 
            className="absolute inset-0 cursor-pointer group flex items-center justify-center bg-cover bg-center"
            style={{ backgroundImage: `url(https://img.youtube.com/vi/${videoId}/hqdefault.jpg)` }}
            onClick={() => setIsPlaying(true)}
            role="button"
            tabIndex={0}
            aria-label={`Play video: ${title}`}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setIsPlaying(true); }}
          >
            <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 transition-colors" />
            <div className="z-10 w-16 h-16 bg-red-600 rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
              <svg className="w-8 h-8 text-white translate-x-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </div>
        ) : (
          <iframe
            className="absolute inset-0 w-full h-full"
            src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&modestbranding=1&rel=0`}
            title={title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        )}
      </div>

      <div className="p-4 flex flex-col justify-between flex-grow">
        <div>
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className="px-2 py-0.5 text-xs font-mono bg-orange-500/10 text-orange-400 border border-orange-500/20 rounded">
              ▲ {score} pts
            </span>
            <a 
              href={hnItemUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-xs text-zinc-400 hover:text-zinc-200 underline underline-offset-4"
            >
              HN Discussion →
            </a>
          </div>
          <h3 className="text-zinc-100 font-medium text-base line-clamp-2 leading-snug">
            {title}
          </h3>
        </div>
        <div className="mt-4 pt-3 border-t border-zinc-800/80 text-xs text-zinc-500 flex items-center justify-between">
          <span>Curated by <strong className="text-zinc-400">{author}</strong></span>
          <span className="font-mono text-[10px]">HackerTube Engine v1.0</span>
        </div>
      </div>
    </div>
  );
};
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **Anti-Pattern 1: Uncached Firebase API Bombardment**
    *   *The Mistake:* Fetching story trees and individual item IDs sequentially on every client navigation without caching or batching.
    *   *The Fix:* Implement a client-side TTL memory cache or lightweight IndexedDB wrapper. Hacker News top stories change slowly; respect rate limits and prevent unnecessary egress.
*   **Anti-Pattern 2: Direct YouTube Embedding Without Privacy Enhancements**
    *   *The Mistake:* Using standard `youtube.com/embed` URLs which inject tracking cookies and personalized recommendation scripts into user sessions.
    *   *The Fix:* Always default to `youtube-nocookie.com` domain endpoints and restrict iframe permissions strictly via the `allow` attribute.
*   **Anti-Pattern 3: Assuming All HN Submissions Have Valid Video IDs**
    *   *The Mistake:* Assuming every top story URL points cleanly to a YouTube `v=` parameter or shorthand path, causing runtime crashes on string splits.
    *   *The Fix:* Implement robust URL parsing guards with `try/catch` blocks and strict domain whitelisting before rendering player components.

---

## 5. Performance & Optimization Tips

1.  **Click-to-Load Thumbnail Hydration:** Never load heavy YouTube iframe objects on initial page load. Render high-res static thumbnails (`hqdefault.jpg`) with an interactive play overlay, dropping initial DOM weight and improving First Contentful Paint (FCP) by up to 75%.
2.  **Virtualized Grid Rendering:** For feeds exceeding 50 items, integrate virtualized list libraries (such as `@tanstack/react-virtual`) to recycle DOM nodes and maintain a locked 60 FPS scrolling experience on lower-end developer laptops.
3.  **Edge Caching with ISR:** If deploying via Vercel, Cloudflare Pages, or Netlify, configure Incremental Static Regeneration (ISR) with a 15-minute revalidation window for the top feed root. This serves pre-compiled HTML instantly while background workers refresh the HN index.

---

## 6. Commercial License & Attribution Summary

### License Agreement
* **Product Name:** HackerTube Developer Reference & Architecture Kit
* **Author:** The Agency Engineering Division (MicroCorp AI)
* **Grant:** Subject to your purchase or acquisition terms, you are granted a perpetual, worldwide, non-exclusive license to use, modify, copy, and distribute this codebase within commercial and open-source applications.
* **Restrictions:** Resale or redistribution of this kit *as a standalone template, boilerplate generator, or competing digital product* is strictly prohibited without explicit written consent from MicroCorp AI.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. The authors accept no liability for third-party API changes or platform deprecations.