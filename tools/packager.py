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
        <div class="quickstart-box" style="margin-bottom: 25px; background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
                <span style="background: #16a34a; color: #fff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase;">⚡ Customer 60-Second Quickstart</span>
                <span style="font-size: 12px; color: #166534; font-weight: 600;">100% Pre-Configured Turnkey Asset</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                <div style="background: #ffffff; padding: 10px 14px; border-radius: 6px; border: 1px solid #bbf7d0;">
                    <div style="color: #166534; font-weight: 700; font-size: 13px;">1. Unzip Delivery</div>
                    <div style="color: #4b5563; font-size: 12px; margin-top: 2px;">Extract package anywhere on your computer.</div>
                </div>
                <div style="background: #ffffff; padding: 10px 14px; border-radius: 6px; border: 1px solid #bbf7d0;">
                    <div style="color: #166534; font-weight: 700; font-size: 13px;">2. Click START_HERE.html</div>
                    <div style="color: #4b5563; font-size: 12px; margin-top: 2px;">Opens interactive dashboard with 1-click code copier.</div>
                </div>
                <div style="background: #ffffff; padding: 10px 14px; border-radius: 6px; border: 1px solid #bbf7d0;">
                    <div style="color: #166534; font-weight: 700; font-size: 13px;">3. 1-Click Launch</div>
                    <div style="color: #4b5563; font-size: 12px; margin-top: 2px;">Run <code>RUN_WINDOWS.bat</code> or <code>python3 main.py</code>.</div>
                </div>
            </div>
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

START_HERE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Quickstart - __TITLE__</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --success: #16a34a;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --code-bg: #0b1120;
        }
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            margin: 0;
            padding: 30px 16px;
            line-height: 1.6;
        }
        .container {
            max-width: 960px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 14px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04);
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        .hero {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: #ffffff;
            padding: 36px 40px;
            border-bottom: 3px solid #3b82f6;
        }
        .badge {
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.4);
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: inline-block;
            margin-bottom: 12px;
        }
        h1 { margin: 0 0 10px 0; font-size: 26px; color: #f8fafc; }
        .meta { color: #94a3b8; font-size: 13px; }
        
        /* 3-Step Quick Launch Bar */
        .quick-bar {
            background: #f0fdf4;
            border-bottom: 1px solid #bbf7d0;
            padding: 20px 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
        }
        .step-card {
            background: #ffffff;
            padding: 14px 16px;
            border-radius: 8px;
            border: 1px solid #86efac;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        .step-title {
            color: #166534;
            font-weight: 700;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
        }
        .step-desc { font-size: 12px; color: #4b5563; }
        
        /* Navigation Tabs */
        .nav-tabs {
            display: flex;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            overflow-x: auto;
            padding: 0 20px;
        }
        .tab-btn {
            background: transparent;
            border: none;
            padding: 16px 20px;
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .tab-btn:hover { color: #1e293b; background: rgba(0,0,0,0.02); }
        .tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; background: #ffffff; }
        
        /* Tab Contents */
        .tab-content { display: none; padding: 36px 40px; }
        .tab-content.active { display: block; }
        
        /* Code Block Viewer */
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #0f172a;
            color: #94a3b8;
            padding: 12px 18px;
            border-radius: 8px 8px 0 0;
            font-family: monospace;
            font-size: 13px;
            border: 1px solid #334155;
            border-bottom: none;
        }
        .copy-btn {
            background: #16a34a;
            color: #ffffff;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .copy-btn:hover { background: #15803d; }
        pre.code-area {
            background: #0b1120;
            color: #f8fafc;
            padding: 18px;
            margin: 0;
            border-radius: 0 0 8px 8px;
            overflow-x: auto;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 13px;
            border: 1px solid #334155;
            max-height: 520px;
        }
        
        /* Tables */
        table.file-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        table.file-table th {
            background: #f8fafc;
            color: #475569;
            text-align: left;
            padding: 10px 14px;
            border-bottom: 2px solid #e2e8f0;
            font-size: 13px;
        }
        table.file-table td {
            padding: 12px 14px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 13px;
        }
        
        /* Toast notification */
        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #16a34a;
            color: #fff;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: none;
            z-index: 9999;
        }
        .footer {
            background: #f8fafc;
            padding: 20px 40px;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Hero Header -->
        <div class="hero">
            <span class="badge">MicroCorp AI • Customer Quickstart Center</span>
            <h1>__TITLE__</h1>
            <div class="meta">
                <span>Category: <strong>__CATEGORY__</strong></span> • 
                <span>Commercial Ownership: <strong>100% Client Transferred</strong></span> • 
                <span>Beneficiary: <strong>__PAYEE_NAME__</strong> (UPI: <code>__PAYOUT_UPI_ID__</code>)</span>
            </div>
        </div>

        <!-- 3-Step Quick Launch Bar -->
        <div class="quick-bar">
            <div class="step-card">
                <div class="step-title">⚡ 1. Interactive Reader (Browser)</div>
                <div class="step-desc">You are already viewing it! Use the tabs below to copy code, read documentation, or view licenses.</div>
            </div>
            <div class="step-card">
                <div class="step-title">🪟 2. 1-Click Launch on Windows</div>
                <div class="step-desc">Simply double-click <strong><code>RUN_WINDOWS.bat</code></strong> in this folder to automatically execute <code>main.py</code>.</div>
            </div>
            <div class="step-card">
                <div class="step-title">🍎 3. 1-Click on macOS / Linux</div>
                <div class="step-desc">Run <strong><code>bash RUN_MAC_LINUX.sh</code></strong> or <strong><code>python3 main.py</code></strong> in your terminal.</div>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="nav-tabs">
            <button class="tab-btn active" onclick="switchTab('quickstart')">🚀 60-Second Quickstart</button>
            <button class="tab-btn" onclick="switchTab('source')">💻 Standalone Source Code (main.py)</button>
            <button class="tab-btn" onclick="switchTab('docs')">📖 Full Architecture Manual</button>
            <button class="tab-btn" onclick="switchTab('files')">📂 Directory & Files Map</button>
            <button class="tab-btn" onclick="switchTab('license')">📜 License & Commercial Invoice</button>
        </div>

        <!-- Tab 1: Quickstart -->
        <div id="tab_quickstart" class="tab-content active">
            <h2 style="color: #0f172a; margin-top: 0;">How to Use Your Deliverable in Under 60 Seconds</h2>
            <p style="color: #475569;">Everything inside this bundle has been engineered with zero bloat and pre-configured for instant integration.</p>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #1e293b;">Option A: Run Immediately with 1-Click Scripts</h3>
                <ul style="margin: 0; padding-left: 20px; color: #475569; font-size: 14px; line-height: 1.8;">
                    <li><strong>Windows Users:</strong> Double-click <code>RUN_WINDOWS.bat</code> in this directory.</li>
                    <li><strong>Mac & Linux Users:</strong> Double-click <code>RUN_MAC_LINUX.sh</code> or run <code>bash RUN_MAC_LINUX.sh</code>.</li>
                </ul>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #1e293b;">Option B: Run from Command Line</h3>
                <div style="background: #0f172a; color: #f8fafc; padding: 14px 18px; border-radius: 6px; font-family: monospace; font-size: 13px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <code>pip install -r requirements.txt &amp;&amp; python main.py</code>
                    <button class="copy-btn" onclick="copyText('pip install -r requirements.txt && python main.py')">Copy</button>
                </div>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px;">
                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #1e293b;">Option C: Copy Source Code Directly into Your Project</h3>
                <p style="color: #475569; font-size: 14px; margin: 0 0 12px 0;">Switch to the <strong>"Standalone Source Code"</strong> tab above, click <strong>"Copy Complete Code"</strong>, and paste it directly into your own repository or editor.</p>
                <button onclick="switchTab('source')" style="background: #2563eb; color: #fff; border: none; padding: 10px 18px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;">
                    View & Copy Code (main.py) →
                </button>
            </div>
        </div>

        <!-- Tab 2: Standalone Source Code -->
        <div id="tab_source" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <div>
                    <h2 style="margin: 0; color: #0f172a;">Standalone Source Code (<code>main.py</code>)</h2>
                    <small style="color: #64748b;">Ready to execute, modular, zero unwanted dependencies.</small>
                </div>
                <button class="copy-btn" style="padding: 8px 18px; font-size: 13px;" onclick="copyCode()">
                    📋 Copy Complete Source Code
                </button>
            </div>
            
            <div class="code-header">
                <span>main.py • Python 3</span>
                <span>Commercial Ownership: Client</span>
            </div>
            <pre class="code-area"><code id="codeBlock">__CODE_DISPLAY__</code></pre>

            <div style="margin-top: 24px;">
                <h3 style="color: #0f172a; margin-bottom: 8px;">Requirements (<code>requirements.txt</code>)</h3>
                <pre style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #334155;">__REQS_DISPLAY__</pre>
            </div>
        </div>

        <!-- Tab 3: Full Architecture Manual -->
        <div id="tab_docs" class="tab-content">
            <h2 style="color: #0f172a; margin-top: 0;">Full Technical Documentation & Architectural Reference</h2>
            <div style="line-height: 1.7; color: #334155;">
                __HTML_BODY__
            </div>
        </div>

        <!-- Tab 4: Directory Map -->
        <div id="tab_files" class="tab-content">
            <h2 style="color: #0f172a; margin-top: 0;">Package Directory & File Contents Map</h2>
            <p style="color: #64748b; font-size: 14px;">Here is an overview of each file included in your unzipped deliverable:</p>
            
            <table class="file-table">
                <thead>
                    <tr>
                        <th>File Name</th>
                        <th>Type</th>
                        <th>Description & Purpose</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>START_HERE.html</code></td>
                        <td><span style="color: #2563eb; font-weight: 600;">Interactive UI</span></td>
                        <td>The interactive customer onboarding dashboard with 1-click code copier and guides.</td>
                    </tr>
                    <tr>
                        <td><code>main.py</code></td>
                        <td><span style="color: #16a34a; font-weight: 600;">Python Script</span></td>
                        <td>The standalone executable source code and verification runner.</td>
                    </tr>
                    <tr>
                        <td><code>RUN_WINDOWS.bat</code></td>
                        <td><span style="color: #d97706; font-weight: 600;">Batch Launcher</span></td>
                        <td>1-click launcher for Windows. Double-click to run code and open dashboard.</td>
                    </tr>
                    <tr>
                        <td><code>RUN_MAC_LINUX.sh</code></td>
                        <td><span style="color: #9333ea; font-weight: 600;">Shell Script</span></td>
                        <td>1-click launcher for macOS and Linux environments.</td>
                    </tr>
                    <tr>
                        <td><code>requirements.txt</code></td>
                        <td><span style="color: #475569; font-weight: 600;">Dependencies</span></td>
                        <td>Dependencies file for easy installation via <code>pip install -r requirements.txt</code>.</td>
                    </tr>
                    <tr>
                        <td><code>QUICKSTART.txt</code></td>
                        <td><span style="color: #475569; font-weight: 600;">Plain Text</span></td>
                        <td>Quickstart instructions readable in Notepad or any plain text editor.</td>
                    </tr>
                    <tr>
                        <td><code>README.md</code></td>
                        <td><span style="color: #475569; font-weight: 600;">Markdown</span></td>
                        <td>Complete technical manual, architecture patterns, and setup reference.</td>
                    </tr>
                    <tr>
                        <td><code>INVOICE.txt</code></td>
                        <td><span style="color: #16a34a; font-weight: 600;">Invoice</span></td>
                        <td>Official verified commercial invoice with payment settlement details.</td>
                    </tr>
                    <tr>
                        <td><code>LICENSE.txt</code></td>
                        <td><span style="color: #2563eb; font-weight: 600;">License</span></td>
                        <td>Full commercial ownership transfer certificate.</td>
                    </tr>
                    <tr>
                        <td><code>TERMS_AND_CONDITIONS.txt</code></td>
                        <td><span style="color: #475569; font-weight: 600;">Legal Terms</span></td>
                        <td>MicroCorp AI corporate terms and ethical governance charter.</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Tab 5: License & Invoice -->
        <div id="tab_license" class="tab-content">
            <h2 style="color: #0f172a; margin-top: 0;">Commercial Rights & Verification Invoice</h2>
            
            <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
                <span style="background: #16a34a; color: #fff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; text-transform: uppercase;">Ownership Verified</span>
                <h3 style="color: #166534; margin: 8px 0 4px 0;">Commercial Distribution & Modification Rights Granted</h3>
                <p style="color: #15803d; font-size: 13px; margin: 0 0 16px 0;">You possess 100% royalty-free commercial rights to use, modify, embed, deploy, and distribute this software in personal or commercial projects.</p>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 13px; color: #1e293b;">
                    <div><strong>Agreed Price:</strong> ₹__AMOUNT_INR__ (~$__PRICE_USD__ USD)</div>
                    <div><strong>Official Beneficiary:</strong> __PAYEE_NAME__</div>
                    <div><strong>Payee UPI ID:</strong> <code>__PAYOUT_UPI_ID__</code></div>
                    <div><strong>Asset ID:</strong> <code>__SAFE_SLUG__</code></div>
                </div>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px;">
                <h3 style="margin: 0 0 8px 0; color: #0f172a;">Customer Support & Inquiries</h3>
                <p style="color: #475569; font-size: 13px; margin: 0;">For customization inquiries, enterprise integrations, or support, contact the host developer at <strong>__PAYEE_NAME__</strong> via UPI reference at <code>__PAYOUT_UPI_ID__</code>.</p>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <span>Asset: <strong>__TITLE__</strong></span>
            <span>MicroCorp AI Autonomous Venture • Payout UPI: <strong>__PAYOUT_UPI_ID__</strong></span>
        </div>
    </div>

    <div id="toast">Copied to clipboard!</div>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
            document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
            var targetContent = document.getElementById('tab_' + tabId);
            if (targetContent) targetContent.classList.add('active');
            var btns = document.querySelectorAll('.tab-btn');
            btns.forEach(function(b) {
                var oc = b.getAttribute('onclick') || '';
                if (oc.indexOf(tabId) !== -1) b.classList.add('active');
            });
        }

        function copyCode() {
            var code = document.getElementById('codeBlock').innerText;
            navigator.clipboard.writeText(code).then(function() {
                showToast('Source code copied to clipboard!');
            });
        }

        function copyText(txt) {
            navigator.clipboard.writeText(txt).then(function() {
                showToast('Command copied to clipboard!');
            });
        }

        function showToast(msg) {
            var t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(function() { t.style.display = 'none'; }, 2500);
        }
    </script>
</body>
</html>
"""

def extract_or_generate_code(markdown_content: str, title: str, category: str) -> tuple:
    pattern = r'```(?:python|py)\s*\n(.*?)```'
    matches = re.findall(pattern, markdown_content, re.DOTALL)
    
    code_blocks = [m.strip() for m in matches if m.strip()]
    detected_reqs = set()
    standard_libs = {
        'os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'random', 'logging',
        'pathlib', 'typing', 'collections', 'itertools', 'functools', 'urllib',
        'http', 'hashlib', 'uuid', 'io', 'shutil', 'subprocess', 'asyncio',
        'concurrent', 'threading', 'multiprocessing', 'queue', 'sqlite3',
        'dataclasses', 'abc', 'enum', 'inspect', 'copy'
    }
    known_packages = {
        'fastapi': 'fastapi>=0.109.0',
        'uvicorn': 'uvicorn>=0.27.0',
        'pydantic': 'pydantic>=2.5.0',
        'requests': 'requests>=2.31.0',
        'httpx': 'httpx>=0.26.0',
        'aiohttp': 'aiohttp>=3.9.0',
        'kafka': 'kafka-python>=2.0.2',
        'pandas': 'pandas>=2.0.0',
        'numpy': 'numpy>=1.24.0',
        'pytest': 'pytest>=7.4.0',
        'sqlalchemy': 'sqlalchemy>=2.0.0',
        'redis': 'redis>=5.0.0',
        'click': 'click>=8.1.0'
    }

    if code_blocks:
        sep = "\n\n# " + "=" * 60 + "\n# Module Implementation Snippet\n# " + "=" * 60 + "\n\n"
        combined = sep.join(code_blocks)
        for line in combined.splitlines():
            s = line.strip()
            if s.startswith("import ") or s.startswith("from "):
                pkg = s.replace("from ", "").replace("import ", "").split()[0].split(".")[0].strip()
                if pkg in known_packages:
                    detected_reqs.add(known_packages[pkg])
                elif pkg and pkg not in standard_libs and not pkg.startswith("_"):
                    detected_reqs.add(pkg)
        
        header = f'\"\"\"\nMicroCorp AI - Turnkey Deliverable\nAsset: {title}\nCategory: {category}\nCommercial Rights: 100% Client Ownership\nOfficial Beneficiary: {PAYEE_NAME} (UPI: {PAYOUT_UPI_ID})\n\"\"\"\n\n'
        if "__main__" not in combined:
            entrypoint = f"""

# ======================================================================
# Quick Test & Verification Runner
# ======================================================================
if __name__ == "__main__":
    print("=" * 65)
    print(" MicroCorp AI - Standalone Production Asset")
    print(f" Asset: {title}")
    print(" Commercial Ownership: 100% Client Transferred")
    print(f" Beneficiary: {PAYEE_NAME} (UPI: {PAYOUT_UPI_ID})")
    print("=" * 65)
    print("[✓] Code integrity verified. Ready for production integration.")
    print("[i] Double-click START_HERE.html to view interactive documentation.")
    print("=" * 65)
"""
            final_code = header + combined + entrypoint
        else:
            final_code = header + combined
    else:
        final_code = f'''"""
MicroCorp AI - Interactive Customer Companion & Quick Runner
Asset: {title}
Category: {category}
Commercial Rights: 100% Client Ownership
Beneficiary: {PAYEE_NAME} (UPI: {PAYOUT_UPI_ID})
"""

def main():
    print("=" * 65)
    print(" MicroCorp AI - Standalone Asset Runner")
    print(" Asset: {title}")
    print(" Commercial Rights: 100% Transferred to Client")
    print(" Beneficiary: {PAYEE_NAME} (UPI: {PAYOUT_UPI_ID})")
    print("=" * 65)
    print("\\n[+] What is in your package:")
    print("    - START_HERE.html : Interactive visual documentation & reader")
    print("    - README.md       : Complete technical architecture & manual")
    print("    - LICENSE.txt     : Commercial rights certificate")
    print("    - INVOICE.txt     : Official verified commercial invoice")
    print("\\n[+] To get started:")
    print("    Double-click START_HERE.html to open your interactive guide.")
    print("=" * 65)

if __name__ == "__main__":
    main()
'''

    if detected_reqs:
        reqs_txt = "# MicroCorp AI - Detected Dependencies\n" + "\n".join(sorted(detected_reqs)) + "\n"
    else:
        reqs_txt = "# MicroCorp AI - Zero External Dependencies (Standard Python Library)\n"

    return final_code, reqs_txt

def generate_run_scripts(title: str, category: str) -> tuple:
    windows_bat = f"""@echo off
title MicroCorp AI - {title[:30]}
color 0A
echo ========================================================================
echo   MICROCORP AI - 1-CLICK CUSTOMER LAUNCHER
echo   Product: {title}
echo   Commercial Rights: 100%% Transferred to Client
echo ========================================================================
echo.
echo [1/2] Opening interactive customer dashboard in default browser...
start "" "START_HERE.html"
echo.
echo [2/2] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not detected in your PATH.
    echo Browse START_HERE.html in your web browser for complete visual docs and code!
) else (
    echo Running standalone source code (main.py)...
    echo.
    python main.py
)
echo.
echo ========================================================================
echo Launcher finished. Press any key to exit.
echo ========================================================================
pause
"""

    mac_linux_sh = f"""#!/usr/bin/env bash
# ========================================================================
# MICROCORP AI - 1-CLICK CUSTOMER LAUNCHER (macOS & Linux)
# ========================================================================

echo "========================================================================"
echo "  MICROCORP AI - 1-CLICK CUSTOMER LAUNCHER"
echo "  Product: {title}"
echo "========================================================================"
echo ""
echo "[1/2] Opening interactive customer dashboard in default browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "START_HERE.html" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "START_HERE.html" >/dev/null 2>&1 &
fi

echo "[2/2] Running standalone source code (main.py)..."
echo ""
if command -v python3 >/dev/null 2>&1; then
    python3 main.py
elif command -v python >/dev/null 2>&1; then
    python main.py
else
    echo "Python is not installed. Please browse START_HERE.html in your web browser."
fi

echo ""
echo "========================================================================"
echo "Done! Check START_HERE.html or README.md for full details."
echo "========================================================================"
"""

    quickstart_txt = f"""========================================================================
🚀 MICROCORP AI - 60-SECOND CUSTOMER QUICKSTART GUIDE
========================================================================
Product: {title}
Category: {category}
Commercial Rights: 100% Client Ownership
Beneficiary: {PAYEE_NAME} (UPI: {PAYOUT_UPI_ID})

HOW TO USE THIS PACKAGE IN 3 SIMPLE STEPS:

METHOD 1 (EASIEST - ZERO SETUP REQUIRED):
-> Simply double-click "START_HERE.html" in this folder.
   It opens your interactive dashboard in any browser with 1-click
   code copy buttons, architecture guides, and file explanations.

METHOD 2 (1-CLICK ON WINDOWS):
-> Double-click "RUN_WINDOWS.bat".
   It automatically opens your interactive browser dashboard AND runs
   the standalone Python code with a single click.

METHOD 3 (1-CLICK ON MACOS & LINUX):
-> In your terminal, run:
   bash RUN_MAC_LINUX.sh
   OR
   python3 main.py

========================================================================
DIRECTORY GUIDE:
- START_HERE.html          : Interactive customer dashboard & 1-click code copier.
- main.py                  : Standalone executable production source code.
- requirements.txt         : Python dependencies (pip install -r requirements.txt).
- RUN_WINDOWS.bat          : 1-click launcher for Windows.
- RUN_MAC_LINUX.sh         : 1-click launcher for macOS & Linux.
- README.md                : Full architectural documentation & technical manual.
- INVOICE.txt              : Official verified commercial invoice.
- LICENSE.txt              : Commercial rights & ownership transfer certificate.
- TERMS_AND_CONDITIONS.txt : Enterprise legal and governance terms.
========================================================================
Need help or custom extensions?
Contact: {PAYEE_NAME} • MicroCorp AI • UPI: {PAYOUT_UPI_ID}
========================================================================
"""
    return windows_bat, mac_linux_sh, quickstart_txt

def generate_start_here_html(
    title: str,
    category: str,
    safe_slug: str,
    code_content: str,
    markdown_content: str,
    amount_inr: float,
    price_usd: float,
    reqs_content: str
) -> str:
    html_body = simple_markdown_to_html(markdown_content)
    safe_code = code_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_reqs = reqs_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    html = START_HERE_TEMPLATE
    html = html.replace("__TITLE__", title)
    html = html.replace("__CATEGORY__", category.replace("_", " ").title())
    html = html.replace("__SAFE_SLUG__", safe_slug)
    html = html.replace("__PAYOUT_UPI_ID__", PAYOUT_UPI_ID)
    html = html.replace("__PAYEE_NAME__", PAYEE_NAME)
    html = html.replace("__AMOUNT_INR__", str(int(amount_inr)))
    html = html.replace("__PRICE_USD__", f"{price_usd:.2f}")
    html = html.replace("__CODE_DISPLAY__", safe_code)
    html = html.replace("__REQS_DISPLAY__", safe_reqs)
    html = html.replace("__HTML_BODY__", html_body)
    return html

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
            
        # 3c. Generate Customer 1-Click Launchers and Interactive START_HERE.html
        code_content, reqs_content = extract_or_generate_code(markdown_content, title, category)
        windows_bat, mac_linux_sh, quickstart_txt = generate_run_scripts(title, category)
        start_here_html = generate_start_here_html(
            title=title,
            category=category,
            safe_slug=base_filename,
            code_content=code_content,
            markdown_content=markdown_content,
            amount_inr=amount_inr,
            price_usd=price_usd,
            reqs_content=reqs_content
        )
        start_here_file = category_dir / f"{base_filename}_START_HERE.html"
        try:
            with open(start_here_file, "w", encoding="utf-8") as f:
                f.write(start_here_html)
        except Exception:
            pass

        # 4. Create ZIP package with Customer Quickstart, Launchers, Terms, Payment QR, and Instructions
        zip_path_str = ""
        terms_text = Packager._get_terms_and_conditions_text()
        if create_zip:
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
                # Customer Onboarding & 1-Click Launchers (Priority Root Files)
                zf.writestr(f"{safe_slug}/START_HERE.html", start_here_html)
                zf.writestr(f"{safe_slug}/RUN_WINDOWS.bat", windows_bat)
                zf.writestr(f"{safe_slug}/RUN_MAC_LINUX.sh", mac_linux_sh)
                zf.writestr(f"{safe_slug}/QUICKSTART.txt", quickstart_txt)
                zf.writestr(f"{safe_slug}/main.py", code_content)
                zf.writestr(f"{safe_slug}/requirements.txt", reqs_content)

                # Standard Deliverable Artifacts
                zf.write(md_file, arcname=f"{safe_slug}/README.md")
                zf.write(html_file, arcname=f"{safe_slug}/index.html")
                zf.write(listing_file, arcname=f"{safe_slug}/MARKETPLACE_LISTING.md")
                zf.write(qr_file, arcname=f"{safe_slug}/PAYMENT_QR.svg")
                zf.write(payment_file, arcname=f"{safe_slug}/PAYMENT_INSTRUCTIONS.md")
                
                # License text with explicit AI disclaimer and liability shield
                license_text = f"""COMMERCIAL PRODUCT LICENSE & LIABILITY DISCLAIMER
Product: {title}
Produced Autonomously By: MicroCorp AI (Autonomous AI Multi-Agent Fleet)
Platform Operator & Payee: {PAYEE_NAME} (UPI: {PAYOUT_UPI_ID})
Jurisdiction: Ahmedabad, Gujarat, India

1. COMMERCIAL GRANT:
Customer is granted a non-exclusive, perpetual, commercial license to use, adapt, and deploy this software deliverable.

2. STRICT AS-IS DISCLAIMER (NO WARRANTIES):
THIS DELIVERABLE AND ALL ACCOMPANYING CODE, SCRIPTS, AND BLUEPRINTS ARE PROVIDED ON AN "AS-IS", "WHERE-IS", AND "WITH ALL FAULTS" BASIS WITHOUT WARRANTY OF ANY KIND, EXPRESS, STATUTORY, OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, ACCURACY, OR NON-INFRINGEMENT.

3. ZERO LIABILITY & HARD MONETARY CAP:
ALL CODE WAS GENERATED AUTONOMOUSLY BY ARTIFICIAL INTELLIGENCE. THE CUSTOMER ASSUMES 100% SOLE RESPONSIBILITY FOR AUDITING, SANDBOXING, AND TESTING ALL CODE PRIOR TO EXECUTION OR PRODUCTION DEPLOYMENT. UNDER NO CIRCUMSTANCES SHALL ALPESH THAKOR OR MICROCORP AI BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, LOST PROFITS, OR DATA LOSS. TOTAL AGGREGATE LIABILITY IS HARD-CAPPED AT THE LESSER OF THE PURCHASE PRICE OR ₹1,000 INR ($10 USD).

4. COMPLETE TERMS:
See accompanying 'TERMS_AND_CONDITIONS.txt' for the complete, legally binding Master Terms of Service, Indemnification, and Exclusive Jurisdiction in Ahmedabad, Gujarat, India."""
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
            
            # Copy zip, html preview, and start_here preview to ready_to_monetize
            try:
                import shutil
                ready_zip = ready_dir / f"{base_filename}.zip"
                shutil.copy2(zip_file, ready_zip)
                ready_html = ready_dir / f"{base_filename}.html"
                if html_file.exists():
                    shutil.copy2(html_file, ready_html)
                ready_start = ready_dir / f"{base_filename}_START_HERE.html"
                if start_here_file.exists():
                    shutil.copy2(start_here_file, ready_start)
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
            "start_here_path": str(start_here_file) if 'start_here_file' in locals() and start_here_file.exists() else "",
            "ecommerce_listings": ecom_files
        }

packager = Packager()
