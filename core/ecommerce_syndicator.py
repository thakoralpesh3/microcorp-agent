"""
MicroCorp AI - Omnichannel E-Commerce & Marketplace Syndication Engine
Transforms autonomous digital deliverables into publication-ready listings across:
1. Amazon KDP (Kindle Direct Publishing - eBook & Print-on-Demand Paperbacks)
2. Flipkart & Meesho (Physical Reference Manual / USB Developer Kit Bridge with HSN 4901 0% GST)
3. Global Digital Creator Marketplaces (Gumroad & itch.io)
4. Indian Instant-UPI Creator Commerce (Instamojo & Cosmofeed)
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import PAYOUT_UPI_ID, PAYEE_NAME, USD_TO_INR_RATE
from core.pricing_engine import pricing_engine

class EcommerceSyndicator:
    def __init__(self):
        self.payout_upi_id = PAYOUT_UPI_ID
        self.payee_name = PAYEE_NAME
        self.usd_to_inr = USD_TO_INR_RATE

    def generate_amazon_kdp_listing(self, title: str, category: str, markdown_content: str, price_usd: float, price_inr: int) -> Dict[str, Any]:
        """
        Formats technical content into an Amazon Kindle Direct Publishing (KDP) listing.
        Supports both Kindle eBook and Amazon Print-on-Demand (POD) Paperback.
        """
        clean_title = title.split(" - ")[0].strip()
        subtitle = "A Practical Production Engineering Handbook & Architectural Implementation Guide"
        
        # 7 KDP Search Keywords (Amazon max 50 chars per keyword)
        keywords = [
            f"{clean_title.lower()} tutorial",
            "software architecture guide",
            "python developer cheatsheet",
            "production backend microservice",
            "docker deployment patterns",
            "api design best practices",
            "engineering reference manual"
        ][:7]

        # BISAC Subject Codes
        bisac_categories = [
            "COM051010 COMPUTERS / Software Development & Engineering / General",
            "COM060000 COMPUTERS / Web Services & APIs / Distributed Systems"
        ]

        # Amazon Description formatted with allowed HTML tags
        description_html = f"""<h3>Master Modern Software Architecture with {clean_title}</h3>
<p>Stop wasting precious engineering hours troubleshooting elusive edge cases and unoptimized boilerplates. <strong>{clean_title}</strong> is a battle-tested, production-grade technical handbook engineered specifically for software professionals, architects, and builders.</p>

<h4>What You Will Learn & Build:</h4>
<ul>
  <li><strong>Core Architectural Blueprints:</strong> Clear separation of concerns, high-throughput async patterns, and resilient error recovery.</li>
  <li><strong>Production Scaffolding:</strong> Modular configurations, database migration workflows, and containerized Docker recipes.</li>
  <li><strong>Security & Verification:</strong> Zero-trust authentication patterns, rate-limiting algorithms, and comprehensive automated test suites.</li>
  <li><strong>Anti-Patterns Guide:</strong> Critical mistakes to avoid in enterprise production environments.</li>
</ul>

<h4>Who This Book Is For:</h4>
<p>Backend developers, full-stack engineers, technical leads, and DevOps specialists looking for concise, copy-paste ready, and field-tested architectural implementations.</p>

<p><em>Published autonomously under MicroCorp AI Commercial Engineering Press. Commercial use permitted.</em></p>"""

        # Paperback Print Specifications
        paperback_specs = {
            "trim_size": '6" x 9" (15.24 x 22.86 cm)',
            "paper_type": "Black & white interior on white paper",
            "cover_finish": "Matte premium finish",
            "page_count_est": max(32, min(120, len(markdown_content.split()) // 250)),
            "bleed_settings": "No Bleed",
            "suggested_paperback_mrp_inr": max(499, price_inr + 150),
            "suggested_paperback_mrp_usd": max(9.99, price_usd + 5.0)
        }

        markdown_spec = f"""# 📚 Amazon KDP (Kindle & Paperback) Publication Spec

## 1. Book Metadata
- **Book Title:** {clean_title}
- **Subtitle:** {subtitle}
- **Author:** MicroCorp AI Editorial Bureau (Alpesh Thakor, Host Director)
- **Language:** English
- **Primary Marketplace:** Amazon.in (India) / Amazon.com (Worldwide)

---

## 2. Categorization & SEO Keywords
### BISAC Categories:
1. `{bisac_categories[0]}`
2. `{bisac_categories[1]}`

### 7 Target Amazon Backend Keywords:
{chr(10).join(f"- `{k}`" for k in keywords)}

---

## 3. Royalty & Pricing Strategy
- **Digital Kindle Price (USD):** ${price_usd:.2f} USD (70% Royalty Tier = ~${price_usd * 0.70:.2f} per sale)
- **Digital Kindle Price (INR):** ₹{price_inr}.00 INR
- **Paperback MRP (INR):** ₹{paperback_specs['suggested_paperback_mrp_inr']}.00 INR
- **Paperback MRP (USD):** ${paperback_specs['suggested_paperback_mrp_usd']:.2f} USD
- **KDP Select Enrollment:** Recommended (Earn royalties per page read on Kindle Unlimited)

---

## 4. Paperback Print-on-Demand Specification
- **Trim Size:** {paperback_specs['trim_size']}
- **Interior:** {paperback_specs['paper_type']}
- **Cover Finish:** {paperback_specs['cover_finish']}
- **Estimated Pages:** ~{paperback_specs['page_count_est']} pages
- **Fulfillment:** 100% Automated by Amazon (Amazon prints and ships physical book to buyer)

---

## 5. Amazon Product Description (Copy & Paste HTML directly into KDP):
```html
{description_html}
```
"""

        return {
            "platform": "Amazon KDP",
            "clean_title": clean_title,
            "subtitle": subtitle,
            "keywords": keywords,
            "bisac_categories": bisac_categories,
            "description_html": description_html,
            "paperback_specs": paperback_specs,
            "price_usd": price_usd,
            "price_inr": price_inr,
            "markdown_spec": markdown_spec
        }

    def generate_flipkart_meesho_spec(self, title: str, category: str, markdown_content: str, price_usd: float, price_inr: int) -> Dict[str, Any]:
        """
        Formats product specifications for Flipkart and Meesho physical commerce.
        Bridges digital content to physical courier delivery:
        - 24-page Spiral Reference Booklet or USB Bootable Developer Kit
        - HSN Code 4901 (Printed Books - 0% GST exempt under Indian GST law)
        """
        clean_title = title.split(" - ")[0].strip()
        product_name = f"[Printed Spiral Guide & Code Kit] {clean_title} Technical Manual"
        
        # Physical parcel specs
        weight_grams = 120
        dimensions_cm = "21 x 15 x 0.8 cm (A5 Notebook Size)"
        hsn_code = "4901.10.10" # Printed books, brochures, leaflets - GST Exempt (0%)
        
        # 5 Flipkart / Meesho Key Feature Bullet Points
        bullet_points = [
            f"PROFESSIONAL DEVELOPER HANDBOOK: In-depth architectural manual for {clean_title} with tested code blueprints.",
            "SPIRAL-BOUND WORKBENCH EDITION: High-quality 80 GSM paper, wire-bound lays completely flat beside keyboard.",
            "INSTANT DIGITAL CODE ACCESS: Embedded high-resolution QR card provides instant ZIP download of all source code files.",
            "COMMERCIAL USE LICENSE: Transferable rights included for professional freelancers, agencies, and enterprise production.",
            "COMPREHENSIVE TESTING & ERROR RECOVERY: Covers production configs, Docker scripts, and unit verification suites."
        ]

        mrp_inr = max(699, round(price_inr * 1.5))
        selling_price_inr = price_inr

        markdown_spec = f"""# 📦 Flipkart & Meesho Marketplace Seller Spec

> [!NOTE]
> **Indian E-Commerce Compliance**: Flipkart & Meesho strictly require physical courier shipment with AWB tracking.
> This package enables you to list this product under **HSN Code 4901.10.10** (Printed Technical Books), which is **0% GST EXEMPT** in India!

---

## 1. Product Listing Details
- **Product Title:** {product_name}
- **Category:** Books > Computing, Internet & Digital Media > Computer Science & Programming
- **Brand / Publisher:** MicroCorp AI Commercial Engineering Press
- **Item Condition:** Brand New (Print-on-Demand)
- **HSN Code:** `{hsn_code}` (0% GST Rate)
- **Country of Origin:** India
- **Manufacturer / Packer:** MicroCorp AI, Ahmedabad, Gujarat, India

---

## 2. Pricing & Margin Strategy
- **MRP:** ₹{mrp_inr}.00 INR
- **Selling Price:** ₹{selling_price_inr}.00 INR
- **Flipkart / Meesho Referral Fee:** ~12-15% (₹{round(selling_price_inr * 0.15)} INR)
- **Courier Shipping (National):** ~₹45 - ₹60 INR (Meesho offers free zero-commission shipping)
- **Print Cost (Local Print Shop A5 Spiral 24-page):** ~₹35 - ₹45 INR
- **Estimated Net Profit per Order:** ~₹{round(selling_price_inr * 0.70)} INR

---

## 3. Package & Courier Specifications
- **Package Dimensions:** {dimensions_cm}
- **Package Weight:** {weight_grams} grams
- **Box Type:** Padded bubble mailer envelope
- **Package Contents:** 
  1. 1x High-Resolution Spiral-Bound {clean_title} Manual (A5 Format)
  2. 1x Instant Access Digital Code Card with QR Code and Verified License Key
  3. 1x Official Commercial Tax Invoice with UPI Payee `{self.payout_upi_id}`

---

## 4. 5 Key Product Highlights (Paste into Flipkart / Meesho bullet points):
{chr(10).join(f"- {bp}" for bp in bullet_points)}

---

## 5. Detailed Product Description:
Looking to level up your engineering capabilities with {clean_title}? 
This official spiral-bound reference handbook gives you an uncluttered, distraction-free physical desk reference featuring battle-tested software patterns, copy-paste production code, and foolproof configuration recipes. 

Simply scan the access card inside the front cover to immediately unlock the digital companion ZIP package containing the full source code repository, Docker environment, and automated test suite.
"""

        return {
            "platform": "Flipkart & Meesho",
            "product_name": product_name,
            "hsn_code": hsn_code,
            "weight_grams": weight_grams,
            "dimensions_cm": dimensions_cm,
            "mrp_inr": mrp_inr,
            "selling_price_inr": selling_price_inr,
            "bullet_points": bullet_points,
            "markdown_spec": markdown_spec
        }

    def generate_gumroad_listing(self, title: str, category: str, markdown_content: str, price_usd: float, price_inr: int) -> Dict[str, Any]:
        """Formats digital product listing for Gumroad and itch.io."""
        clean_title = title.split(" - ")[0].strip()
        tags = ["python", "development", "architecture", "cheatsheet", "fastapi", "docker", "ai"]

        markdown_spec = f"""# 🌐 Gumroad & itch.io Digital Product Listing

## 1. Product Setup
- **Name:** {clean_title}
- **Suggested Price:** ${price_usd:.2f} USD (Allow customers to pay what they want: Yes, minimum ${price_usd:.2f})
- **Currency:** USD (Gumroad automatically converts to INR, EUR, GBP)
- **Category:** Software & Developer Tools

---

## 2. Product Summary & Description (Copy into Gumroad):
> **The Definitive Production Engineering Kit for {clean_title}**

Stop debugging boilerplate. This comprehensive toolkit provides everything you need to build, test, and ship production-grade architectures with zero friction.

### 📦 What You Get:
- ⚡ **Complete Reference Handbook & Cheat Sheet** (Markdown & Printable HTML)
- 🛠️ **Production-Ready Source Code & Boilerplate** (Fully typed, cleanly commented)
- 🐳 **Containerized Deployment Scaffolding** (Production Dockerfile & Compose setup)
- 🧪 **Automated Test Suite** (Pre-configured unit and integration checks)
- 📜 **Commercial Product License** (Personal and enterprise commercial use permitted)
- 🇮🇳 **Direct Indian UPI Payment Option**: Instant settlement to `{self.payout_upi_id}` ({self.payee_name})

### 🏷️ Tags:
`{", ".join(tags)}`
"""
        return {
            "platform": "Gumroad",
            "title": clean_title,
            "price_usd": price_usd,
            "tags": tags,
            "markdown_spec": markdown_spec
        }

    def generate_instamojo_spec(self, title: str, category: str, markdown_content: str, price_usd: float, price_inr: int) -> Dict[str, Any]:
        """Formats Indian creator commerce listing for Instamojo, Cosmofeed, and Razorpay Payment Pages."""
        clean_title = title.split(" - ")[0].strip()
        markdown_spec = f"""# 🇮🇳 Instamojo & Cosmofeed (Indian Creator Commerce) Spec

## 1. Product Configuration
- **Title:** {clean_title} - Commercial Developer Toolkit
- **Price:** ₹{price_inr}.00 INR (Fixed Price)
- **Payment Modes:** UPI (PhonePe, Google Pay, Paytm, BHIM), NetBanking, Credit/Debit Cards
- **Product Type:** Digital File Download (Instant ZIP delivery upon successful payment)
- **Payee Bank / UPI:** `{self.payout_upi_id}` ({self.payee_name})

---

## 2. Product Description (Paste into Instamojo / Cosmofeed):
### 🚀 Instant Access Developer Toolkit
Get immediate access to the complete source code, architectural patterns, and commercial license for **{clean_title}**. 

**Key Benefits:**
- Instant ZIP download unlocked immediately upon payment.
- 100% Commercial rights included.
- Compatible with all Indian UPI apps and major banks.
"""
        return {
            "platform": "Instamojo & Cosmofeed",
            "title": clean_title,
            "price_inr": price_inr,
            "markdown_spec": markdown_spec
        }

    def generate_all_marketplace_packages(
        self,
        asset_id: str,
        title: str,
        category: str,
        markdown_content: str,
        custom_price_usd: Optional[float] = None,
        custom_price_inr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generates full multi-channel e-commerce syndication specifications
        for Amazon KDP, Flipkart/Meesho, Gumroad, and Instamojo.
        """
        pricing = pricing_engine.get_pricing_for_asset(
            title=title,
            category=category,
            custom_price_usd=custom_price_usd,
            custom_price_inr=custom_price_inr
        )
        price_usd = pricing["price_usd"]
        price_inr = pricing["price_inr"]

        amazon = self.generate_amazon_kdp_listing(title, category, markdown_content, price_usd, price_inr)
        flipkart_meesho = self.generate_flipkart_meesho_spec(title, category, markdown_content, price_usd, price_inr)
        gumroad = self.generate_gumroad_listing(title, category, markdown_content, price_usd, price_inr)
        instamojo = self.generate_instamojo_spec(title, category, markdown_content, price_usd, price_inr)

        return {
            "asset_id": asset_id,
            "title": title,
            "category": category,
            "pricing": pricing,
            "channels": {
                "amazon_kdp": amazon,
                "flipkart_meesho": flipkart_meesho,
                "gumroad": gumroad,
                "instamojo": instamojo
            }
        }

    def export_syndication_folder(
        self,
        target_dir: Path,
        asset_id: str,
        title: str,
        category: str,
        markdown_content: str,
        custom_price_usd: Optional[float] = None,
        custom_price_inr: Optional[float] = None
    ) -> Dict[str, str]:
        """
        Writes all marketplace listing sheets into an ECOMMERCE_LISTINGS directory
        for bundling into ZIP packages.
        """
        out_dir = target_dir / "ECOMMERCE_LISTINGS"
        out_dir.mkdir(parents=True, exist_ok=True)

        bundle = self.generate_all_marketplace_packages(
            asset_id=asset_id,
            title=title,
            category=category,
            markdown_content=markdown_content,
            custom_price_usd=custom_price_usd,
            custom_price_inr=custom_price_inr
        )

        channels = bundle["channels"]
        files = {
            "amazon": out_dir / "AMAZON_KDP_LISTING.md",
            "flipkart_meesho": out_dir / "FLIPKART_MEESHO_SPEC.md",
            "gumroad": out_dir / "GUMROAD_LISTING.md",
            "instamojo": out_dir / "INSTAMOJO_UPI_SPEC.md"
        }

        files["amazon"].write_text(channels["amazon_kdp"]["markdown_spec"], encoding="utf-8")
        files["flipkart_meesho"].write_text(channels["flipkart_meesho"]["markdown_spec"], encoding="utf-8")
        files["gumroad"].write_text(channels["gumroad"]["markdown_spec"], encoding="utf-8")
        files["instamojo"].write_text(channels["instamojo"]["markdown_spec"], encoding="utf-8")

        return {k: str(v) for k, v in files.items()}

# Global singleton
ecommerce_syndicator = EcommerceSyndicator()
