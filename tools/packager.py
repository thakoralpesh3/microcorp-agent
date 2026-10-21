"""
MicroCorp AI - Deliverables Packager
Formats, renders HTML previews, and packages deliverables into publish-ready ZIP archives.
"""

import os
import zipfile
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DELIVERABLES_DIR, PAYOUT_UPI_ID, PAYEE_NAME, USD_TO_INR_RATE
from core.upi_payment import upi_gateway
from core.pricing_engine import pricing_engine
from core.ecommerce_syndicator import ecommerce_syndicator

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #1e293b;
            background: #f8fafc;
            padding: 40px 20px;
            margin: 0;
        }}
        .container {{
            max-width: 820px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px 50px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }}
        .header {{
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .badge {{
            display: inline-block;
            background: #eff6ff;
            color: #2563eb;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}
        h1 {{ color: #0f172a; margin-top: 5px; font-size: 28px; }}
        h2 {{ color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-top: 30px; }}
        h3 {{ color: #334155; margin-top: 24px; }}
        code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.9em;
            color: #0f172a;
        }}
        pre {{
            background: #0f172a;
            color: #f8fafc;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{ background: transparent; color: inherit; padding: 0; }}
        blockquote {{
            border-left: 4px solid #3b82f6;
            margin: 0;
            padding-left: 16px;
            color: #475569;
            background: #f8fafc;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #64748b;
            display: flex;
            justify-content: space-between;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">{category}</span>
            <h1>{title}</h1>
            <small style="color: #64748b;">Generated autonomously by MicroCorp AI • {timestamp}</small>
        </div>
        <div class="content">
            {html_body}
        </div>
        <div class="payment-box" style="margin-top: 35px; padding: 24px; background: #f0fdf4; border: 2px solid #86efac; border-radius: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="background: #16a34a; color: #fff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase;">Instant UPI Settlement</span>
                    <h3 style="margin: 6px 0 2px 0; color: #166534; font-size: 18px;">Commercial Access & License Purchase</h3>
                    <p style="margin: 0; color: #15803d; font-size: 13px;">To obtain full commercial distribution rights, send payment directly to official enterprise UPI ID.</p>
                </div>
                <div style="text-align: right;">
                    <span style="font-size: 22px; font-weight: 800; color: #15803d;">₹{amount_inr}</span>
                    <small style="color: #4b5563; display: block; font-size: 12px;">(~${price_usd:.2f} USD)</small>
                </div>
            </div>
            
            <div style="display: flex; gap: 20px; align-items: center; margin-top: 16px; flex-wrap: wrap;">
                <div style="width: 140px; height: 140px; background: #ffffff; padding: 6px; border-radius: 8px; border: 1px solid #bbf7d0; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                    {qr_svg_inline}
                </div>
                <div style="flex: 1; min-width: 220px;">
                    <div style="font-size: 13px; color: #1f2937; margin-bottom: 6px;">
                        <strong>Payee UPI ID:</strong> <code style="font-size: 14px; background: #ffffff; color: #15803d; border: 1px solid #86efac; padding: 3px 8px; border-radius: 4px;">{payout_upi_id}</code>
                    </div>
                    <div style="font-size: 12px; color: #4b5563; margin-bottom: 4px;">
                        <strong>Payee Name:</strong> {payee_name}
                    </div>
                    <div style="font-size: 12px; color: #4b5563; margin-bottom: 12px;">
                        <strong>Accepted Apps:</strong> PhonePe, Google Pay, Paytm, BHIM, Cred
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <a href="{upi_uri}" style="display: inline-block; background: #16a34a; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600;">
                            ⚡ Pay with UPI App
                        </a>
                        <a href="/checkout/{safe_slug}" style="display: inline-block; background: #ffffff; color: #166534; border: 1px solid #16a34a; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600;">
                            Verify UTR / Download
                        </a>
                    </div>
                </div>
            </div>
        </div>
        <div class="footer">
            <span>Asset ID: {safe_slug}</span>
            <span>MicroCorp AI Autonomous Venture</span>
        </div>
    </div>
</body>
</html>
"""

def simple_markdown_to_html(md_text: str) -> str:
    """Lightweight markdown to HTML converter without external dependencies."""
    html = md_text
    # Escape HTML special chars (except when in backticks, but basic replacement is safe)
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Headers
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Blockquotes
    html = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # Bold and Italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # Code blocks
    def code_block_repl(m):
        code_content = m.group(1).strip()
        return f"<pre><code>{code_content}</code></pre>"
    html = re.sub(r'```(?:\w+)?\n([\s\S]*?)```', code_block_repl, html)
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Unordered Lists
    lines = html.split("\n")
    in_list = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            if not in_list:
                new_lines.append("<ul>")
                in_list = True
            item_text = line.strip()[2:]
            new_lines.append(f"<li>{item_text}</li>")
        else:
            if in_list:
                new_lines.append("</ul>")
                in_list = False
            if line.strip() and not line.strip().startswith("<"):
                new_lines.append(f"<p>{line}</p>")
            else:
                new_lines.append(line)
    if in_list:
        new_lines.append("</ul>")
        
    return "\n".join(new_lines)

class Packager:
    @staticmethod
    def _get_terms_and_conditions_text() -> str:
        terms_file = Path(__file__).parent.parent / "TERMS_AND_CONDITIONS.md"
        if terms_file.exists():
            try:
                return terms_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return "MicroCorp AI - Standard Commercial Usage Permitted. 100% Host Owner Copyright."

    @staticmethod
    def generate_marketplace_listing(title: str, category: str, markdown_content: str, price_usd: float = 19.0) -> str:
        """Generates a complete ready-to-paste marketplace listing (Gumroad/ProductHunt/GitHub)."""
        tags = ["development", "cheatsheet", "automation", "python", "developer-tools", "ai"]
        if "async" in title.lower() or "concurrency" in title.lower():
            tags.extend(["concurrency", "performance"])
        if "prompt" in title.lower():
            tags.extend(["prompt-engineering", "llm"])

        price_inr = round(price_usd * USD_TO_INR_RATE)

        listing = f"""# Marketplace Listing Copy & Product Sheet
**Product Title:** {title}
**Suggested Retail Price:** ${price_usd:.2f} USD (~₹{price_inr} INR)
**Category:** {category.replace('_', ' ').title()}
**License:** Commercial & Personal Use Included
**Direct Payout UPI:** `{PAYOUT_UPI_ID}` ({PAYEE_NAME})

---

## 📌 Direct Purchase via UPI (Zero Platform Fees)
To purchase directly with instant download rights:
1. Transfer **₹{price_inr} INR** via any UPI app (PhonePe, Google Pay, Paytm, BHIM) to:
   - **UPI ID:** `{PAYOUT_UPI_ID}`
   - **Payee:** {PAYEE_NAME}
   - **Transaction Note:** `{title[:30]}`
2. Submit your 12-digit bank UTR to `/checkout/{re.sub(r'[^a-zA-Z0-9_\-]', '_', title.lower())[:30]}` to unlock download.

---

## 📌 One-Line Tagline
> The definitive production-tested developer guide and pattern toolkit for {title.split('-')[0].strip()}.

## 📝 Product Description (Paste directly into Gumroad / Etsy / itch.io)
Stop wasting hours debugging boilerplate and syntax quirks. 
This professional toolkit provides battle-tested production patterns, clean architectural cheat sheets, 
and practical implementation guides designed for modern engineers and builders.

### What is Included:
- ⚡ **Full Reference Documentation & Cheat Sheet** (Markdown & Styled HTML)
- 🛠️ **Production-Ready Code Snippets** (Tested, copy-paste ready)
- ⚠️ **Anti-Patterns & Edge Cases Guide**
- 📜 **Commercial Usage License & Full Terms**
- 💳 **Direct UPI Payment QR & Verified Invoice**

### Target Tags / Keywords:
`{", ".join(tags)}`

---
*Generated autonomously by MicroCorp AI Enterprise with Direct Payout to {PAYOUT_UPI_ID}.*
"""
        return listing

    @staticmethod
    def save_deliverable(
        category: str,
        title: str,
        markdown_content: str,
        create_zip: bool = True,
        custom_price_usd: Optional[float] = None,
        custom_price_inr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Saves a deliverable as Markdown and HTML, archives into a ZIP file with Terms,
        Marketplace listing, instant UPI QR code, and payment instructions.
        Returns paths and metadata.
        """
        category_dir = DELIVERABLES_DIR / category
        ready_dir = DELIVERABLES_DIR / "ready_to_monetize"
        for d in [category_dir, ready_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', title.lower())[:40].strip('_')
        base_filename = f"{timestamp}_{safe_slug}"
        
        md_file = category_dir / f"{base_filename}.md"
        html_file = category_dir / f"{base_filename}.html"
        zip_file = category_dir / f"{base_filename}.zip"
        listing_file = category_dir / f"{base_filename}_LISTING.md"
        qr_file = category_dir / f"{base_filename}_QR.svg"
        payment_file = category_dir / f"{base_filename}_PAYMENT.md"

        # 0. Calculate Dynamic Tier Pricing
        pricing = pricing_engine.get_pricing_for_asset(
            title=title,
            category=category,
            custom_price_usd=custom_price_usd,
            custom_price_inr=custom_price_inr
        )
        price_usd = pricing["price_usd"]
        custom_inr = pricing["price_inr"]

        checkout_pkg = upi_gateway.create_checkout_package(
            asset_id=safe_slug,
            title=title,
            category=category,
            price_usd=price_usd,
            custom_price_inr=custom_inr
        )
        amount_inr = checkout_pkg["amount_inr"]
        qr_svg_str = checkout_pkg["qr_svg"]
        payment_instructions_md = checkout_pkg["payment_instructions_md"]

        with open(qr_file, "w", encoding="utf-8") as f:
            f.write(qr_svg_str)

        with open(payment_file, "w", encoding="utf-8") as f:
            f.write(payment_instructions_md)
        
        # 1. Save Markdown
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # 2. Save Marketplace Listing
        marketplace_copy = Packager.generate_marketplace_listing(title, category, markdown_content, price_usd=price_usd)
        with open(listing_file, "w", encoding="utf-8") as f:
            f.write(marketplace_copy)
            
        # 3. Render & Save HTML with embedded UPI QR & checkout
        html_body = simple_markdown_to_html(markdown_content)
        rendered_html = HTML_TEMPLATE.format(
            title=title,
            category=category.replace("_", " ").title(),
            timestamp=datetime.now().strftime("%B %d, %Y %H:%M"),
            safe_slug=base_filename,
            html_body=html_body,
            amount_inr=int(amount_inr),
            price_usd=price_usd,
            payout_upi_id=PAYOUT_UPI_ID,
            payee_name=PAYEE_NAME,
            upi_uri=checkout_pkg["upi_uri"],
            qr_svg_inline=qr_svg_str
        )
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        # 3b. Generate Multi-Channel E-Commerce Marketplace Listings
        ecom_files = {}
        try:
            ecom_files = ecommerce_syndicator.export_syndication_folder(
                target_dir=category_dir,
                asset_id=safe_slug,
                title=title,
                category=category,
                markdown_content=markdown_content,
                custom_price_usd=custom_price_usd,
                custom_price_inr=custom_price_inr
            )
        except Exception:
            ecom_files = {}
            
        # 4. Create ZIP package with Terms, Payment QR, and Instructions
        zip_path_str = ""
        terms_text = Packager._get_terms_and_conditions_text()
        if create_zip:
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(md_file, arcname=f"{safe_slug}/README.md")
                zf.write(html_file, arcname=f"{safe_slug}/index.html")
                zf.write(listing_file, arcname=f"{safe_slug}/MARKETPLACE_LISTING.md")
                zf.write(qr_file, arcname=f"{safe_slug}/PAYMENT_QR.svg")
                zf.write(payment_file, arcname=f"{safe_slug}/PAYMENT_INSTRUCTIONS.md")
                
                # License text
                license_text = f"COMMERCIAL PRODUCT LICENSE\nProduct: {title}\nProduced By: MicroCorp AI\nCommercial and Personal Use Permitted.\nPayee UPI ID: {PAYOUT_UPI_ID} ({PAYEE_NAME})\nHost Owner retains 100% distribution rights."
                zf.writestr(f"{safe_slug}/LICENSE.txt", license_text)
                
                # Terms and Conditions
                zf.writestr(f"{safe_slug}/TERMS_AND_CONDITIONS.txt", terms_text)

                # Invoice text
                invoice_text = f"MICROCORP AI COMMERCIAL INVOICE\nItem: {title}\nPrice: ₹{amount_inr:.2f} INR (~${price_usd:.2f} USD)\nPayee UPI ID: {PAYOUT_UPI_ID}\nPayee Name: {PAYEE_NAME}\nStatus: Verified For Instant Delivery\n"
                zf.writestr(f"{safe_slug}/INVOICE.txt", invoice_text)

                # Embed Multi-Channel E-Commerce Marketplace Listings
                for ch_name, ch_path_str in ecom_files.items():
                    ch_path = Path(ch_path_str)
                    if ch_path.exists():
                        zf.write(ch_path, arcname=f"{safe_slug}/ECOMMERCE_LISTINGS/{ch_path.name}")

            zip_path_str = str(zip_file)
            
            # Copy zip and html preview to ready_to_monetize for instant access and previews
            try:
                import shutil
                ready_zip = ready_dir / f"{base_filename}.zip"
                shutil.copy2(zip_file, ready_zip)
                ready_html = ready_dir / f"{base_filename}.html"
                if html_file.exists():
                    shutil.copy2(html_file, ready_html)
            except Exception:
                pass
            
        return {
            "title": title,
            "category": category,
            "markdown_path": str(md_file),
            "html_path": str(html_file),
            "zip_path": zip_path_str,
            "primary_path": zip_path_str or str(html_file),
            "listing_path": str(listing_file),
            "qr_path": str(qr_file),
            "payment_path": str(payment_file),
            "payout_upi_id": PAYOUT_UPI_ID,
            "amount_inr": amount_inr,
            "price_usd": price_usd,
            "upi_uri": checkout_pkg["upi_uri"],
            "size_bytes": md_file.stat().st_size,
            "ecommerce_listings": ecom_files
        }

packager = Packager()
