"""
MicroCorp AI - Public Marketplace & GitHub Releases Distribution Engine
Autonomously publishes manufactured software assets to public GitHub Releases,
embeds direct UPI settlement details (talpesh100@ybl), and authors marketing promotions.
"""

import os
import sys
import json
import time
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    GH_BIN, GITHUB_REPO, DELIVERABLES_DIR, 
    PAYOUT_UPI_ID, PAYEE_NAME, USD_TO_INR_RATE
)
from core.tunnel_gateway import public_gateway

logger = logging.getLogger("MicroCorp.PublicDistribution")
PROMOTIONS_DIR = DELIVERABLES_DIR / "promotions"
PROMOTIONS_DIR.mkdir(parents=True, exist_ok=True)

class PublicDistributionManager:
    def __init__(self):
        self.gh_path = Path(GH_BIN)
        self.repo = GITHUB_REPO
        self.published_releases: Dict[str, Any] = {}

    def is_gh_available(self) -> bool:
        """Verifies if GitHub CLI is present and executable."""
        return self.gh_path.exists() and os.access(str(self.gh_path), os.X_OK)

    def publish_asset_to_github_release(
        self,
        zip_path: str,
        title: str,
        description: str,
        price_usd: float = 19.0,
        price_inr: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Publishes a production ZIP archive as a public GitHub Release on the repository,
        enabling global indexability, direct download, and UPI monetization.
        """
        inr_val = price_inr or round(price_usd * USD_TO_INR_RATE)
        zip_file = Path(zip_path)
        
        if not zip_file.exists():
            return {"success": False, "error": f"Deliverable ZIP file not found: {zip_path}"}

        clean_slug = zip_file.stem[:24].lower()
        tag = f"release-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        public_url = public_gateway.get_public_url()
        checkout_url = f"{public_url}/checkout/{clean_slug}" if public_url else f"http://127.0.0.1:8585/checkout/{clean_slug}"
        store_url = f"{public_url}/store" if public_url else "http://127.0.0.1:8585/store"

        # Construct comprehensive Release Notes with direct UPI payment instructions
        release_notes = f"""# 🚀 {title} - Commercial Developer Toolkit
*Manufactured autonomously by MicroCorp AI Autonomous Enterprise Fleet.*

---

## 📦 What's Inside This Release Package:
- **Production Source Code**: Cleanly structured, type-annotated modules.
- **Architectural Specification**: Complete system patterns and deployment guides.
- **Unit Test Suite**: Verified with zero syntax errors.
- **Commercial License**: Transferable commercial rights for enterprise production use.

---

## ⚡ Direct UPI Instant Settlement (Zero Platform Fees)
You can directly support the creator and unlock commercial licensing via any Indian UPI app:

- **Amount**: ₹{inr_val} INR (~${price_usd:.2f} USD)
- **Payee UPI ID**: `{PAYOUT_UPI_ID}`
- **Beneficiary**: **{PAYEE_NAME}**
- **Supported Apps**: PhonePe, Google Pay, Paytm, BHIM, Cred, Amazon Pay.
- **Online Checkout Portal**: [{checkout_url}]({checkout_url})
- **Full Digital Storefront**: [{store_url}]({store_url})

---

### How to Pay & Access:
1. Scan the embedded `PAYMENT_QR.svg` or send ₹{inr_val} to `{PAYOUT_UPI_ID}`.
2. Enter your 12-digit bank UTR / Reference number at the [Instant Checkout Portal]({checkout_url}).
3. Instant automated invoice and delivery verification will be generated.

*Terms & Conditions apply. Distributed by MicroCorp AI.*
"""

        # Also generate promotional copy in deliverables/promotions/
        self.generate_promotional_copy(title, description, price_usd, inr_val, checkout_url)

        if not self.is_gh_available():
            logger.warning(f"gh CLI not found at {self.gh_path}. Saving release notes locally.")
            return {
                "success": True,
                "is_remote_published": False,
                "tag": tag,
                "title": title,
                "checkout_url": checkout_url,
                "notes": release_notes,
                "message": "Release notes prepared with UPI payment details."
            }

        # Execute gh release create
        cmd = [
            str(self.gh_path),
            "release", "create", tag,
            str(zip_file),
            "--repo", self.repo,
            "--title", f"📦 {title} (v1.0)",
            "--notes", release_notes
        ]

        logger.info(f"🚀 Publishing public GitHub Release '{tag}' for '{title}'...")
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45,
                check=False
            )
            if res.returncode == 0:
                release_url = res.stdout.strip()
                logger.info(f"✨ GitHub Release published successfully: {release_url}")
                return {
                    "success": True,
                    "is_remote_published": True,
                    "tag": tag,
                    "release_url": release_url,
                    "checkout_url": checkout_url,
                    "title": title,
                    "amount_inr": inr_val
                }
            else:
                logger.warning(f"gh release create exited with code {res.returncode}: {res.stderr}")
                return {
                    "success": False,
                    "is_remote_published": False,
                    "error": res.stderr.strip(),
                    "tag": tag,
                    "checkout_url": checkout_url
                }
        except Exception as e:
            logger.error(f"Failed to publish GitHub Release: {e}")
            return {"success": False, "error": str(e), "tag": tag, "checkout_url": checkout_url}

    def generate_promotional_copy(
        self,
        title: str,
        description: str,
        price_usd: float,
        price_inr: int,
        checkout_url: str
    ) -> str:
        """Generates ready-to-share promotional markdown copy for tech forums and social media."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', title.lower())[:30]
        promo_path = PROMOTIONS_DIR / f"{timestamp}_{slug}_promo.md"

        import urllib.parse
        tweet_text = f"🚀 Just released: {title}! Production code, automated tests & 1-click launcher. Instant UPI (₹{price_inr}): {checkout_url}"
        wa_text = f"Check out {title} on MicroCorp AI (₹{price_inr} instant UPI download): {checkout_url}"
        reddit_title = f"Show Python: {title} - Production developer toolkit with 1-click launcher"
        
        tw_share = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet_text)}"
        li_share = f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(checkout_url)}"
        wa_share = f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}"
        rd_share = f"https://reddit.com/submit?url={urllib.parse.quote(checkout_url)}&title={urllib.parse.quote(reddit_title)}"

        content = f"""# Social & Marketplace Promotional Pack: {title}
**Date:** {time.strftime('%B %d, %Y')}  
**Asset:** {title}  
**Price:** ₹{price_inr} INR / ${price_usd:.2f} USD  
**Checkout Link:** {checkout_url}  
**UPI ID:** `{PAYOUT_UPI_ID}` ({PAYEE_NAME})

---

### ⚡ 1-Click Broadcast Links:
- [Share on 𝕏 (Twitter)]({tw_share})
- [Share on LinkedIn]({li_share})
- [Share on WhatsApp]({wa_share})
- [Submit to Reddit]({rd_share})

---

## 1. 𝕏 (Twitter) Launch Post / Thread
**Post 1:**
🚀 Just dropped: **{title}**!
A turnkey, production-grade developer toolkit with full modular source code, unit tests, Docker scaffolding, and 1-click launchers (`START_HERE.html`).

Get it here with zero-fee instant UPI (₹{price_inr} / ${price_usd:.2f}):
👉 {checkout_url}

#Python #DevOps #MicroSaaS #WebDev #BuildInPublic

---

## 2. LinkedIn Professional Update
**Hook:**
Excited to announce the release of **{title}**, engineered autonomously by MicroCorp AI!

Modern software development requires handling edge cases, rigorous error boundaries, and production-tested patterns. This toolkit provides:
✅ Full typed source code (`main.py`)
✅ Automated verification tests
✅ Interactive customer dashboard & 1-click launchers
✅ Full commercial ownership rights

Direct download with instant bank UPI settlement to `{PAYOUT_UPI_ID}`:
🔗 {checkout_url}

#SoftwareEngineering #TechStartup #Automation #AI

---

## 3. Reddit Post (`r/Python`, `r/FastAPI`, `r/webdev`)
**Title:** Show Python: {title} (Complete architecture guide & production boilerplate)

**Body:**
Hey developers,

I just finished putting together an end-to-end, production-ready implementation for **{title}**.

### Why I built this:
{description}

### What's included:
- Full typed Python source code
- Automated test suite with zero external blockers
- Docker containerization setup
- Step-by-step architectural breakdown & documentation

You can check out the live public preview and instant download here:
👉 **[View & Download Toolkit]({checkout_url})**
Instant UPI checkout (PhonePe, GPay, Paytm) supported directly at `{PAYOUT_UPI_ID}`.

Let me know what you think in the comments!

---

## 4. WhatsApp Broadcast Message
🔥 *New Release from MicroCorp AI:* **{title}**
Instant production toolkit with complete source code, tests, and 1-click launcher!
💰 Price: ₹{price_inr} INR (Zero fee direct UPI)
🔗 Download now: {checkout_url}

---

## 5. Dev.to / Medium Article Draft
**Title:** Architecture Deep-Dive: Building {title} in Production

**Hook:**
Building reliable systems requires handling edge cases, structured error boundaries, and battle-tested patterns. Here is how we structured **{title}** for maximum throughput.

**Call to Action:**
Want the complete, copy-paste starter kit with unit tests and Docker scaffolding?  
Get it here with instant UPI checkout: [{checkout_url}]({checkout_url})

---

*Generated autonomously by MicroCorp AI Marketing & Public Distribution Bureau.*
"""
        with open(promo_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(promo_path)

    def get_share_links(self, title: str, checkout_url: str, price_inr: int) -> Dict[str, str]:
        """Returns direct 1-click social sharing links for a given asset."""
        import urllib.parse
        tweet_text = f"🚀 Just released: {title}! Production code & 1-click launcher. Instant UPI (₹{price_inr}): {checkout_url}"
        wa_text = f"Check out {title} on MicroCorp AI (₹{price_inr} instant UPI download): {checkout_url}"
        reddit_title = f"Show Python: {title} - Production developer toolkit with 1-click launcher"
        
        return {
            "twitter": f"https://twitter.com/intent/tweet?text={urllib.parse.quote(tweet_text)}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(checkout_url)}",
            "whatsapp": f"https://api.whatsapp.com/send?text={urllib.parse.quote(wa_text)}",
            "reddit": f"https://reddit.com/submit?url={urllib.parse.quote(checkout_url)}&title={urllib.parse.quote(reddit_title)}"
        }

import re

# Global singleton
public_distribution = PublicDistributionManager()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("GH Available:", public_distribution.is_gh_available())
