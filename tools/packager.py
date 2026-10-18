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
from config import DELIVERABLES_DIR

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
    def generate_marketplace_listing(title: str, category: str, markdown_content: str) -> str:
        """Generates a complete ready-to-paste marketplace listing (Gumroad/ProductHunt/GitHub)."""
        summary_snippet = markdown_content[:250].replace("#", "").strip()
        tags = ["development", "cheatsheet", "automation", "python", "developer-tools", "ai"]
        if "async" in title.lower() or "concurrency" in title.lower():
            tags.extend(["concurrency", "performance"])
        if "prompt" in title.lower():
            tags.extend(["prompt-engineering", "llm"])

        listing = f"""# Marketplace Listing Copy & Product Sheet
**Product Title:** {title}
**Suggested Retail Price:** $14.99 - $24.99 USD
**Category:** {category.replace('_', ' ').title()}
**License:** Commercial & Personal Use Included

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

### Target Tags / Keywords:
`{", ".join(tags)}`

---
*Generated autonomously by MicroCorp AI Enterprise.*
"""
        return listing

    @staticmethod
    def save_deliverable(category: str, title: str, markdown_content: str, create_zip: bool = True) -> Dict[str, Any]:
        """
        Saves a deliverable as Markdown and HTML, archives into a ZIP file with Terms and Marketplace listing.
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
        
        # 1. Save Markdown
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # 2. Save Marketplace Listing
        marketplace_copy = Packager.generate_marketplace_listing(title, category, markdown_content)
        with open(listing_file, "w", encoding="utf-8") as f:
            f.write(marketplace_copy)
            
        # 3. Render & Save HTML
        html_body = simple_markdown_to_html(markdown_content)
        rendered_html = HTML_TEMPLATE.format(
            title=title,
            category=category.replace("_", " ").title(),
            timestamp=datetime.now().strftime("%B %d, %Y %H:%M"),
            safe_slug=base_filename,
            html_body=html_body
        )
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(rendered_html)
            
        # 4. Create ZIP package with Terms and Conditions & License
        zip_path_str = ""
        terms_text = Packager._get_terms_and_conditions_text()
        if create_zip:
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(md_file, arcname=f"{safe_slug}/README.md")
                zf.write(html_file, arcname=f"{safe_slug}/index.html")
                zf.write(listing_file, arcname=f"{safe_slug}/MARKETPLACE_LISTING.md")
                
                # License text
                license_text = f"COMMERCIAL PRODUCT LICENSE\nProduct: {title}\nProduced By: MicroCorp AI\nCommercial and Personal Use Permitted.\nHost Owner retains 100% distribution rights."
                zf.writestr(f"{safe_slug}/LICENSE.txt", license_text)
                
                # Terms and Conditions
                zf.writestr(f"{safe_slug}/TERMS_AND_CONDITIONS.txt", terms_text)
            zip_path_str = str(zip_file)
            
            # Copy zip to ready_to_monetize for instant access
            try:
                import shutil
                ready_zip = ready_dir / f"{base_filename}.zip"
                shutil.copy2(zip_file, ready_zip)
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
            "size_bytes": md_file.stat().st_size
        }

packager = Packager()
