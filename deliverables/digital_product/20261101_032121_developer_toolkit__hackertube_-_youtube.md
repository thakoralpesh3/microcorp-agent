# HackerTube: The Developer’s Architecture Kit
**Build your own curated YouTube interface, powered by Hacker News intelligence.**

## 1. Product Title & Value Proposition
**Product:** HackerTube Architecture & Integration Kit  
**Value Prop:** A production-ready blueprint for building a "Signal-to-Noise" focused video aggregator. By scraping Hacker News (HN) for video-based discussions and syncing them with the YouTube Data API, you solve the "YouTube Discovery Problem"—surfacing only high-intellect, community-vetted content for developers.

---

## 2. Quick Start & Core Concepts

To build HackerTube, you need to bridge three disparate data sources.

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Data Fetcher** | Firebase/HN API | Extract top-voted threads containing `youtube.com` links. |
| **Metadata Enricher** | YouTube Data API v3 | Fetch video duration, thumbnail, and channel verification. |
| **Frontend Framework** | Next.js (App Router) | Server-side rendering for SEO and fast initial paints. |
| **State Layer** | React Query | Handling caching and background revalidation of video metadata. |

---

## 3. Production Code Patterns & Architecture Examples

### A. The HN-to-YouTube Adapter (Server Action)
Use this utility to filter HN stories and extract valid YouTube IDs.

```typescript
// app/actions/fetch-hacker-tube.ts
export async function getTopVideoStories() {
  const topStoriesRes = await fetch('https://hacker-news.firebaseio.com/v0/topstories.json');
  const ids = await topStoriesRes.json();
  
  // Parallel fetch metadata for top 10
  const promises = ids.slice(0, 10).map(async (id: number) => {
    const res = await fetch(`https://hacker-news.firebaseio.com/v0/item/${id}.json`);
    return res.json();
  });

  const stories = await Promise.all(promises);
  return stories.filter(s => s.url?.includes('youtube.com/watch'));
}
```

### B. The "Smart" Video Player Component
A wrapper around `react-player` that handles responsive scaling and tracking.

```tsx
// components/VideoPlayer.tsx
import ReactPlayer from 'react-player/youtube';

export const VideoPlayer = ({ url }: { url: string }) => (
  <div className="aspect-video w-full overflow-hidden rounded-xl border border-zinc-800">
    <ReactPlayer 
      url={url} 
      width="100%" 
      height="100%" 
      controls={true}
      config={{ youtube: { playerVars: { origin: 'https://hackertube.com' }}}}
    />
  </div>
);
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1.  **N+1 API Requests:** Never fetch video metadata inside a client-side map loop. Always aggregate IDs and send a single batch request to the YouTube API.
2.  **Ignoring YouTube Quotas:** The YouTube Data API has a strict daily quota. **Implement caching:** Store results in a Redis or local JSON store with a 24-hour TTL (Time-to-Live).
3.  **Title Sanitization:** Hacker News titles are often truncated or formatted poorly. Don't trust the HN title string—always use the `snippet.title` returned by the YouTube API.
4.  **Lack of Error States:** API calls will fail. Ensure you have a fallback UI for videos that have been deleted or privated.

---

## 5. Performance & Optimization Tips

*   **Edge Middleware:** Use Vercel Edge Config to cache the top 50 video IDs globally. This reduces "Time to First Byte" (TTFB) to sub-50ms.
*   **Image Optimization:** Use `next/image` with the YouTube thumbnail CDN (`i.ytimg.com`). Leverage `placeholder="blur"` to prevent layout shifts.
*   **Resource Hints:** Use `<link rel="preconnect" href="https://www.youtube.com" />` in your `layout.tsx` to reduce handshake latency.
*   **Skeleton Loading:** Use shimmer effects for the video feed to maintain a high "Perceived Performance" score.

---

## 6. Commercial License & Attribution Summary

*   **Usage:** This architecture kit is licensed under the **MIT License**. You are free to integrate this code into personal and commercial projects.
*   **Attribution:** While not strictly required, a credit to "HackerTube Architecture Kit" in your footer is appreciated.
*   **Disclaimer:** This software is provided "as-is." Always review the [YouTube Terms of Service](https://www.youtube.com/t/terms) and [Hacker News API Guidelines](https://github.com/HackerNews/API) regarding commercial data usage.
*   **Disclaimer on APIs:** Ensure your API keys are stored in `.env.local` and never committed to public repositories.

---
*Built for the Engineering Division of The Agency. Stay pixel-perfect.* 🖥️