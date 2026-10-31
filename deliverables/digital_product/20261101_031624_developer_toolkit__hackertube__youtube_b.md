# HackerTube: The HN-Curation Video Pipeline & Architecture Kit

> **Turn high-signal Hacker News discussions into an ad-free, distraction-free, terminal-inspired video streaming environment.**

---

## 1. Product Title & Value Proposition

### Product Title
**HackerTube Developer Kit: Building a Curated YouTube Frontend from Hacker News Intelligence**

### Value Proposition
Modern video consumption is plagued by engagement bait, algorithmic rabbit holes, and intrusive monetization. **HackerTube** solves this by programmatically bridging the gap between high-signal developer discourse on Hacker News (Algolia API) and programmatic media playback (YouTube IFrame API / Invidious instances). 

This architecture kit provides production-grade schemas, state management models, and performance patterns to build, deploy, and monetize a lightning-fast, privacy-first video dashboard tailored specifically for engineers, researchers, and tech enthusiasts.

```
+------------------+     +-------------------+     +---------------------+
| Hacker News APIs | --> | Content Curators  | --> | HackerTube Frontend |
| (Algolia / Firebase)   | (Scoring/Filters) |     | (Vanilla/React/Solid)|
+------------------+     +-------------------+     +---------------------+
```

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts

| Concept | Description | Implementation Strategy |
| :--- | :--- | :--- |
| **Signal Extraction** | Fetching top submissions containing YouTube domains. | Query Algolia HN Search API filtering by `url:*youtube.com*` or `url:*youtu.be*`. |
| **Decoupled Playplayer** | Zero-bloat video rendering without tracking cookies. | Use lightweight HTML5 wrappers around the YouTube Embed API or fallback to privacy-respecting instances (Invidious). |
| **Curated Ranking** | Sorting videos by community velocity (points-to-time ratio). | Implement custom ranking algorithms blending HN score, comment count, and freshness decay. |
| **Edge Caching** | Minimizing external API roundtrips for trending items. | Cache query responses at the CDN edge (Cloudflare Workers / Vercel Edge) with a 15-minute TTL. |

### Quick Start Installation

```bash
# Clone the reference architecture kit
git clone https://github.com/microcorp-ai/hackertube-kit.git
cd hackertube-kit

# Install dependencies (Zero-dependency vanilla core + Vite tooling)
npm install

# Run local development environment with mock HN stream
npm run dev
```

---

## 3. Production Code Patterns & Architecture Examples

### A. Hacker News Algolia API Fetcher & Normalizer (`src/services/hn.ts`)
Production-ready TypeScript module to query, filter, and normalize video submissions from Hacker News.

```typescript
export interface HNVideoItem {
  objectID: string;
  title: string;
  url: string;
  points: number;
  author: string;
  createdAt: string;
  numComments: number;
  videoId: string;
}

const YOUTUBE_REGEX = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/i;

export function extractYouTubeId(url: string): string | null {
  const match = url.match(YOUTUBE_REGEX);
  return match ? match[1] : null;
}

export async function fetchHackerTubeFeed(limit = 30): Promise<HNVideoItem[]> {
  const endpoint = `https://hn.algolia.com/api/v1/search?query=youtube&tags=story&numericFilters=points>20&hitsPerPage=${limit * 2}`;
  
  try {
    const response = await fetch(endpoint);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    
    const data = await response.json();
    
    const processedItems: HNVideoItem[] = data.hits
      .filter((hit: any) => hit.url && extractYouTubeId(hit.url))
      .map((hit: any) => ({
        objectID: hit.objectID,
        title: hit.title,
        url: hit.url,
        points: hit.points || 0,
        author: hit.author,
        createdAt: hit.created_at,
        numComments: hit.num_comments || 0,
        videoId: extractYouTubeId(hit.url)!,
      }))
      .slice(0, limit);

    return processedItems;
  } catch (error) {
    console.error("Failed to fetch HackerTube feed:", error);
    return [];
  }
}
```

### B. High-Performance Client-Side State & Local Storage Caching (`src/hooks/useHackerTube.ts`)
Custom reactive hook implementing stale-while-revalidate caching patterns.

```typescript
import { useState, useEffect } from 'react';
import { fetchHackerTubeFeed, HNVideoItem } from '../services/hn';

interface UseHackerTubeReturn {
  videos: HNVideoItem[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const CACHE_KEY = 'hackertube_cache_v1';
const CACHE_TTL = 15 * 60 * 1000; // 15 minutes

export function useHackerTube(): UseHackerTubeReturn {
  const [videos, setVideos] = useState<HNVideoItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadFeed = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);

    try {
      if (!forceRefresh) {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          const { timestamp, data } = JSON.parse(cached);
          if (Date.now() - timestamp < CACHE_TTL) {
            setVideos(data);
            setLoading(false);
            return;
          }
        }
      }

      const freshData = await fetchHackerTubeFeed();
      setVideos(freshData);
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        timestamp: Date.now(),
        data: freshData,
      }));
    } catch (err: any) {
      setError(err.message || 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeed();
  }, []);

  return { videos, loading, error, refresh: () => loadFeed(true) };
}
```

### C. Zero-Bloat Terminal UI Component (`src/components/VideoGrid.tsx`)
Responsive CSS Grid layout styled with a clean, developer-focused aesthetic.

```tsx
import React from 'react';
import { HNVideoItem } from '../services/hn';

interface VideoGridProps {
  videos: HNVideoItem[];
  onSelect: (video: HNVideoItem) => void;
}

export const VideoGrid: React.FC<VideoGridProps> = ({ videos, onSelect }) => {
  return (
    <div style={styles.grid}>
      {videos.map((video) => (
        <div key={video.objectID} style={styles.card} onClick={() => onSelect(video)}>
          <div style={styles.thumbnailWrapper}>
            <img 
              src={`https://img.youtube.com/vi/${video.videoId}/hqdefault.jpg`} 
              alt={video.title} 
              style={styles.thumbnail}
              loading="lazy"
            />
            <span style={styles.badge}>▲ {video.points}</span>
          </div>
          <div style={styles.meta}>
            <h3 style={styles.title}>{video.title}</h3>
            <p style={styles.subtext}>by {video.author} | {video.numComments} comments</p>
          </div>
        </div>
      ))}
    </div>
  );
};

const styles = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '1.5rem',
    padding: '1rem 0',
  } as React.CSSProperties,
  card: {
    background: '#121212',
    border: '1px solid #2a2a2a',
    borderRadius: '6px',
    overflow: 'hidden',
    cursor: 'pointer',
    transition: 'transform 0.2s ease, border-color 0.2s ease',
  } as React.CSSProperties,
  thumbnailWrapper: {
    position: 'relative' as const,
    width: '100%',
    aspectRatio: '16/9',
    background: '#000',
  },
  thumbnail: {
    width: '100%',
    height: '100%',
    objectFit: 'cover' as const,
  },
  badge: {
    position: 'absolute' as const,
    bottom: '8px',
    right: '8px',
    background: 'rgba(255, 102, 0, 0.9)',
    color: '#fff',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 'bold',
  },
  meta: {
    padding: '1rem',
  },
  title: {
    fontSize: '0.95rem',
    color: '#e0e0e0',
    margin: '0 0 0.5rem 0',
    lineHeight: '1.4',
  },
  subtext: {
    fontSize: '0.8rem',
    color: '#888',
    margin: 0,
  },
};
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

*   **Anti-Pattern 1: Uncached Algolia Polling**
    *   *The Mistake:* Querying the Algolia API on every single client component mount without rate-limiting or persistence.
    *   *The Fix:* Always implement edge-caching or local storage TTL layers (as shown in Section 3B) to avoid HTTP 429 Rate Limit responses.
*   **Anti-Pattern 2: Heavy Embedded Players (`iframe` overload)**
    *   *The Mistake:* Rendering heavy YouTube `<iframe>` elements for every item in a list view, destroying browser performance and leaking memory.
    *   *The Fix:* Use static thumbnails (`img.youtube.com/vi/{id}/hqdefault.jpg`) and instantiate the player dynamically only when a user explicitly clicks a card.
*   **Anti-Pattern 3: Fragile URL Parsing**
    *   *The Mistake:* Relying on `split('?v=')[1]` which fails on short links (`youtu.be/...`), embedded URLs, or URLs with additional query parameters (like `&t=120s`).
    *   *The Fix:* Use robust Regular Expressions or dedicated URI parsing libraries designed for YouTube's shifting URL patterns.

---

## 5. Performance & Optimization Tips

1.  **Preconnect to External Media Hosts:**
    Add resource hints in your HTML `<head>` to speed up DNS resolution and TLS handshakes for YouTube imagery and framing:
    ```html
    <link rel="preconnect" href="https://www.youtube.com">
    <link rel="preconnect" href="https://img.youtube.com">
    <link rel="dns-prefetch" href="https://hn.algolia.com">
    ```
2.  **Virtualize Long Lists:**
    If rendering more than 50 items simultaneously, integrate windowing libraries like `@tanstack/react-virtual` to maintain a strict 60 FPS scrolling budget.
3.  **Use Privacy-Enhanced Embeds:**
    When embedding active players, load them from `https://www.youtube-nocookie.com/embed/{id}` to prevent unnecessary cookie drops and improve GDPR compliance.

---

## 6. Commercial License & Attribution Summary

### MicroCorp AI Commercial License (MIT-Compatible Enterprise Grade)

Copyright (c) 2025 MicroCorp AI. All rights reserved.

*   **Grant of Rights:** Purchaser is granted a perpetual, non-exclusive, worldwide license to use, modify, copy, and distribute this architecture kit within commercial and non-commercial software products.
*   **Restrictions:** You may not resell this kit as a standalone developer template or boilerplate package without explicit written authorization from MicroCorp AI.
*   **Warranty Disclaimer:** Provided "as is", without warranty of any kind, express or implied. MicroCorp AI shall not be held liable for any claims, damages, or liabilities arising from the deployment of this code.