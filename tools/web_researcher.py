"""
MicroCorp AI - Web Researcher & Feed Harvester
Fetches live tech trends, remote gig feeds, and market intelligence for passive income generation.
"""

import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger("MicroCorp.WebResearcher")

class WebResearcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 MicroCorp/1.0"
        }
        self._cache: Dict[str, Any] = {}
        self._last_cache_time: Dict[str, float] = {}

    def _fetch_rss(self, url: str, timeout: int = 7) -> List[Dict[str, str]]:
        now = time.time()
        if url in self._cache and (now - self._last_cache_time.get(url, 0) < 300):
            return self._cache[url]

        results = []
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                root = ET.fromstring(content)
                items = root.findall(".//item")
                for item in items[:15]:
                    title = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")
                    results.append({
                        "title": title.text.strip() if title is not None and title.text else "Untitled",
                        "link": link.text.strip() if link is not None and link.text else "",
                        "description": desc.text.strip() if desc is not None and desc.text else ""
                    })
                self._cache[url] = results
                self._last_cache_time[url] = now
        except Exception as e:
            logger.warning(f"Failed to fetch RSS from {url}: {e}")
            if url in self._cache:
                return self._cache[url]
        return results

    def fetch_trending_tech(self) -> List[Dict[str, str]]:
        """Collects trending developer news from Hacker News & Dev.to."""
        hn_items = self._fetch_rss("https://news.ycombinator.com/rss")
        dev_items = self._fetch_rss("https://dev.to/feed")
        
        combined = []
        for it in hn_items[:8]:
            combined.append({"source": "HackerNews", **it})
        for it in dev_items[:8]:
            combined.append({"source": "Dev.to", **it})
            
        if not combined:
            # Resilient fallback if laptop is offline
            combined = [
                {"source": "LocalRadar", "title": "Local LLM Agents for Micro-SaaS Automation", "link": "https://example.com/ai-agents", "description": "High demand for autonomous local scripts and automation."},
                {"source": "LocalRadar", "title": "FastAPI + SQLite Lightweight Micro-Enterprises", "link": "https://example.com/fastapi-agents", "description": "Building sustainable side businesses running on local hardware."}
            ]
        return combined

    def fetch_remote_gigs(self) -> List[Dict[str, str]]:
        """Collects live freelance / remote gig postings for automated proposal drafting."""
        wwr_jobs = self._fetch_rss("https://weworkremotely.com/categories/remote-programming-jobs.rss")
        
        gigs = []
        for job in wwr_jobs[:10]:
            gigs.append({
                "source": "WeWorkRemotely",
                "title": job["title"],
                "link": job["link"],
                "description": job["description"][:300] if job["description"] else "Remote software opportunity"
            })
            
        if not gigs:
            gigs = [
                {
                    "source": "OpportunityRadar",
                    "title": "Python Web Automation & Agent Integration Specialist",
                    "link": "https://example.com/gig-python",
                    "description": "Looking for developer to build autonomous background web scrapers, API monitors, and alert webhooks."
                }
            ]
        return gigs

    def get_digital_product_opportunities(self) -> List[Dict[str, str]]:
        """Analyzes trending concepts to suggest high-conversion digital products."""
        tech_trends = self.fetch_trending_tech()
        ideas = []
        for item in tech_trends[:6]:
            ideas.append({
                "topic": item["title"],
                "target_audience": "Software Engineers & Creators",
                "product_type": "Developer Cheatsheet & Prompt Kit",
                "suggested_price": "$14.99",
                "source_ref": item["link"]
            })
        return ideas

web_researcher = WebResearcher()
